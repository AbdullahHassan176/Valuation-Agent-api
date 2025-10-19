from typing import Dict, Any, List
from datetime import datetime, date, timedelta
import QuantLib as ql
import numpy as np
from ...schemas.instrument import IRSSpec
from ...schemas.run import PVBreakdown
from ..curves.base import CurveBundle, interpolate_curve
from ..curves.ois import bootstrap_usd_ois_curve, get_discount_factor
from ..curves.forward import project_flat_forwards, create_simple_schedule
from ..schedules import (
    create_schedule, 
    PaymentSchedule, 
    SchedulePeriod,
    day_count_fraction,
    parse_day_count_convention,
    BusinessDayConvention
)

def price_irs(spec: IRSSpec, curves: CurveBundle) -> PVBreakdown:
    """
    Price an Interest Rate Swap using QuantLib
    
    Args:
        spec: IRS specification
        curves: Curve bundle with discount and forward curves
        
    Returns:
        PVBreakdown with present value components
    """
    now = datetime.utcnow()
    
    # Set evaluation date
    ql.Settings.instance().evaluationDate = ql.Date.from_date(curves.as_of_date)
    
    # Create QuantLib objects
    notional = spec.notional
    fixed_rate = spec.fixedRate or 0.05
    effective_date = ql.Date.from_date(spec.effective)
    maturity_date = ql.Date.from_date(spec.maturity)
    
    # Create calendar and day count conventions
    calendar = create_quantlib_calendar(spec.calendar)
    fixed_dc = create_quantlib_daycount(spec.dcFixed)
    floating_dc = create_quantlib_daycount(spec.dcFloat)
    bdc = create_quantlib_business_day_convention(spec.bdc)
    
    # Create frequency objects
    fixed_freq = create_quantlib_frequency(spec.freqFixed)
    floating_freq = create_quantlib_frequency(spec.freqFloat)
    
    # Create discount curve from market data
    discount_curve = create_quantlib_discount_curve(curves)
    
    # Create forward curve (for now, use flat forwards)
    forward_curve = create_quantlib_forward_curve(curves)
    
    # Create index for floating leg
    index = ql.USDLibor(ql.Period(3, ql.Months), forward_curve)
    
    # Create fixed leg
    fixed_leg = ql.VanillaSwap(
        ql.VanillaSwap.Payer,  # Pay fixed
        notional,
        ql.Schedule(
            effective_date,
            maturity_date,
            ql.Period(fixed_freq),
            calendar,
            bdc,
            bdc,
            ql.DateGeneration.Forward,
            False
        ),
        fixed_rate,
        fixed_dc,
        ql.Schedule(
            effective_date,
            maturity_date,
            ql.Period(floating_freq),
            calendar,
            bdc,
            bdc,
            ql.DateGeneration.Forward,
            False
        ),
        index,
        0.0,  # spread
        floating_dc
    )
    
    # Set pricing engine
    swap_engine = ql.DiscountingSwapEngine(discount_curve)
    fixed_leg.setPricingEngine(swap_engine)
    
    # Calculate present values
    fixed_leg_pv = fixed_leg.legNPV(0)  # Fixed leg NPV
    floating_leg_pv = fixed_leg.legNPV(1)  # Floating leg NPV
    net_pv = fixed_leg.NPV()  # Net NPV
    
    # Calculate PV01 (parallel shift sensitivity)
    pv01 = calculate_pv01(fixed_leg, discount_curve, 0.0001)  # 1bp shift
    
    # Get curve hashes for lineage
    market_data_hash = f"usd_ois_quotes_{curves.market_data_profile}_{curves.as_of_date}"
    model_hash = f"quantlib_irs_model_{now.strftime('%Y%m%d_%H%M%S')}"
    
    components = {
        "fixed_leg_pv": fixed_leg_pv,
        "floating_leg_pv": floating_leg_pv,
        "net_pv": net_pv,
        "notional": notional,
        "fixed_rate": fixed_rate,
        "pv01": pv01
    }
    
    # Add curve information to metadata
    metadata = {
        "instrument_type": "IRS",
        "pricing_model": "quantlib_vanilla_swap",
        "curves_used": ["USD_OIS_DISCOUNT", "USD_LIBOR_FORWARD"],
        "as_of_date": curves.as_of_date.isoformat(),
        "market_data_profile": curves.market_data_profile,
        "spec_hash": f"irs_{notional}_{spec.ccy}_{spec.effective}_{spec.maturity}",
        "calculation_timestamp": now.isoformat(),
        "quantlib_version": ql.__version__,
        "pv01": pv01
    }
    
    return PVBreakdown(
        run_id="",  # Will be set by caller
        total_pv=net_pv,
        components=components,
        market_data_hash=market_data_hash,
        model_hash=model_hash,
        calculated_at=now,
        metadata=metadata
    )

def calculate_fixed_leg_pv(spec: IRSSpec, discount_curve) -> float:
    """
    Calculate fixed leg present value using proper schedule generation and day count conventions
    
    Args:
        spec: IRS specification
        discount_curve: Discount curve reference
        
    Returns:
        Fixed leg present value
    """
    # Create proper payment schedule
    payment_schedule = create_schedule(
        effective_date=spec.effective,
        termination_date=spec.maturity,
        frequency=spec.freqFixed,
        day_count_convention=spec.dcFixed,
        business_day_convention=spec.bdc,
        calendar_name=spec.calendar
    )
    
    fixed_rate = spec.fixedRate or 0.05  # Default to 5% if not provided
    notional = spec.notional
    
    total_pv = 0.0
    
    for period in payment_schedule.periods:
        # Calculate payment amount using proper day count fraction
        payment_amount = notional * fixed_rate * period.day_count_fraction
        
        # Get discount factor
        discount_factor = get_discount_factor(discount_curve, period.payment_date)
        
        # Calculate present value
        pv = payment_amount * discount_factor
        total_pv += pv
    
    return total_pv

def calculate_floating_leg_pv(spec: IRSSpec, discount_curve) -> float:
    """
    Calculate floating leg present value using projected forwards
    
    Args:
        spec: IRS specification
        discount_curve: Discount curve reference
        
    Returns:
        Floating leg present value
    """
    # Create proper payment schedule for floating leg
    payment_schedule = create_schedule(
        effective_date=spec.effective,
        termination_date=spec.maturity,
        frequency=spec.freqFloat,
        day_count_convention=spec.dcFloat,
        business_day_convention=spec.bdc,
        calendar_name=spec.calendar
    )
    
    notional = spec.notional
    total_pv = 0.0
    
    for period in payment_schedule.periods:
        # For now, use flat forwards (will be enhanced with proper forward curve)
        # In a real implementation, this would use projected forward rates
        forward_rate = 0.05  # Placeholder - should come from forward curve
        
        # Calculate payment amount using projected forward rate
        payment_amount = notional * forward_rate * period.day_count_fraction
        
        # Get discount factor
        discount_factor = get_discount_factor(discount_curve, period.payment_date)
        
        # Calculate present value
        pv = payment_amount * discount_factor
        total_pv += pv
    
    return total_pv
