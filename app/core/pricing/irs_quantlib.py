from typing import Dict, Any, List
from datetime import datetime, date, timedelta
import QuantLib as ql
import numpy as np
from ...schemas.instrument import IRSSpec
from ...schemas.run import PVBreakdown
from ..curves.base import CurveBundle


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


def create_quantlib_calendar(calendar_name: str) -> ql.Calendar:
    """Create QuantLib calendar from string name."""
    calendar_map = {
        "USD": ql.UnitedStates(ql.UnitedStates.NYSE),
        "EUR": ql.TARGET(),
        "GBP": ql.UnitedKingdom(ql.UnitedKingdom.Exchange),
        "USD_EUR": ql.JointCalendar(ql.UnitedStates(ql.UnitedStates.NYSE), ql.TARGET()),
    }
    return calendar_map.get(calendar_name, ql.UnitedStates(ql.UnitedStates.NYSE))


def create_quantlib_daycount(day_count: str) -> ql.DayCounter:
    """Create QuantLib day counter from string."""
    day_count_map = {
        "ACT/360": ql.Actual360(),
        "ACT/365F": ql.Actual365Fixed(),
        "30E/360": ql.Thirty360(ql.Thirty360.European),
        "ACT/ACT": ql.ActualActual(ql.ActualActual.ISDA),
    }
    return day_count_map.get(day_count, ql.Actual360())


def create_quantlib_business_day_convention(bdc: str) -> ql.BusinessDayConvention:
    """Create QuantLib business day convention from string."""
    bdc_map = {
        "Following": ql.Following,
        "Modified Following": ql.ModifiedFollowing,
        "Preceding": ql.Preceding,
        "Modified Preceding": ql.ModifiedPreceding,
    }
    return bdc_map.get(bdc, ql.Following)


def create_quantlib_frequency(freq: str) -> ql.Frequency:
    """Create QuantLib frequency from string."""
    freq_map = {
        "Annual": ql.Annual,
        "Semi-Annual": ql.Semiannual,
        "Quarterly": ql.Quarterly,
        "Monthly": ql.Monthly,
    }
    return freq_map.get(freq, ql.Semiannual)


def create_quantlib_discount_curve(curves: CurveBundle) -> ql.YieldTermStructure:
    """Create QuantLib discount curve from curve bundle."""
    # For now, create a flat curve at 5%
    # In production, this would bootstrap from market data
    flat_rate = 0.05
    flat_curve = ql.FlatForward(
        ql.Date.from_date(curves.as_of_date),
        flat_rate,
        ql.Actual360()
    )
    return flat_curve


def create_quantlib_forward_curve(curves: CurveBundle) -> ql.YieldTermStructure:
    """Create QuantLib forward curve from curve bundle."""
    # For now, create a flat curve at 5%
    # In production, this would project forwards from market data
    flat_rate = 0.05
    flat_curve = ql.FlatForward(
        ql.Date.from_date(curves.as_of_date),
        flat_rate,
        ql.Actual360()
    )
    return flat_curve


def calculate_pv01(swap: ql.VanillaSwap, curve: ql.YieldTermStructure, shift: float) -> float:
    """Calculate PV01 (parallel shift sensitivity) for a swap."""
    # Store original NPV
    original_npv = swap.NPV()
    
    # Create shifted curve
    shifted_curve = ql.ZeroSpreadedTermStructure(curve, ql.QuoteHandle(ql.SimpleQuote(shift)))
    
    # Create new engine with shifted curve
    shifted_engine = ql.DiscountingSwapEngine(shifted_curve)
    swap.setPricingEngine(shifted_engine)
    
    # Calculate NPV with shift
    shifted_npv = swap.NPV()
    
    # PV01 is the difference in NPV per basis point
    pv01 = (shifted_npv - original_npv) / (shift * 10000)  # Convert to per bp
    
    return pv01
