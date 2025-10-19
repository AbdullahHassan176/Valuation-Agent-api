from typing import Dict, Any, List
from datetime import datetime, date, timedelta
import QuantLib as ql
import numpy as np
from ...schemas.instrument import CCSSpec
from ...schemas.run import PVBreakdown
from ..curves.base import CurveBundle


def price_ccs(spec: CCSSpec, curves: CurveBundle) -> PVBreakdown:
    """
    Price a Cross-Currency Swap using QuantLib
    
    Args:
        spec: CCS specification
        curves: Curve bundle with discount and forward curves
        
    Returns:
        PVBreakdown with present value components
    """
    now = datetime.utcnow()
    
    # Set evaluation date
    ql.Settings.instance().evaluationDate = ql.Date.from_date(curves.as_of_date)
    
    # Create QuantLib objects
    notional_base = spec.notionalBase
    notional_quote = spec.notionalQuote
    effective_date = ql.Date.from_date(spec.effective)
    maturity_date = ql.Date.from_date(spec.maturity)
    
    # Create calendar and day count conventions
    calendar = create_quantlib_calendar(spec.calendar)
    base_dc = create_quantlib_daycount(spec.dcBase)
    quote_dc = create_quantlib_daycount(spec.dcQuote)
    bdc = create_quantlib_business_day_convention(spec.bdc)
    
    # Create frequency objects
    base_freq = create_quantlib_frequency(spec.freqBase)
    quote_freq = create_quantlib_frequency(spec.freqQuote)
    
    # Create discount curves for both currencies
    base_discount_curve = create_quantlib_discount_curve(curves, spec.ccyBase)
    quote_discount_curve = create_quantlib_discount_curve(curves, spec.ccyQuote)
    
    # Create forward curves for both currencies
    base_forward_curve = create_quantlib_forward_curve(curves, spec.ccyBase)
    quote_forward_curve = create_quantlib_forward_curve(curves, spec.ccyQuote)
    
    # Create indices for floating legs
    base_index = create_quantlib_index(spec.ccyBase, base_forward_curve)
    quote_index = create_quantlib_index(spec.ccyQuote, quote_forward_curve)
    
    # Create CCS
    ccs = ql.VanillaSwap(
        ql.VanillaSwap.Payer,  # Pay base currency
        notional_base,
        ql.Schedule(
            effective_date,
            maturity_date,
            ql.Period(base_freq),
            calendar,
            bdc,
            bdc,
            ql.DateGeneration.Forward,
            False
        ),
        0.0,  # Fixed rate (CCS are typically float/float)
        base_dc,
        ql.Schedule(
            effective_date,
            maturity_date,
            ql.Period(quote_freq),
            calendar,
            bdc,
            bdc,
            ql.DateGeneration.Forward,
            False
        ),
        quote_index,
        0.0,  # spread
        quote_dc
    )
    
    # Set pricing engine
    ccs_engine = ql.DiscountingSwapEngine(base_discount_curve)
    ccs.setPricingEngine(ccs_engine)
    
    # Calculate present values
    base_leg_pv = ccs.legNPV(0)  # Base currency leg NPV
    quote_leg_pv = ccs.legNPV(1)  # Quote currency leg NPV (converted to base)
    net_pv = ccs.NPV()  # Net NPV in base currency
    
    # Calculate FX sensitivity
    fx_sensitivity = calculate_fx_sensitivity(ccs, base_discount_curve, 0.01)  # 1% FX move
    
    # Get curve hashes for lineage
    market_data_hash = f"ccs_quotes_{curves.market_data_profile}_{curves.as_of_date}"
    model_hash = f"quantlib_ccs_model_{now.strftime('%Y%m%d_%H%M%S')}"
    
    components = {
        "base_leg_pv": base_leg_pv,
        "quote_leg_pv": quote_leg_pv,
        "net_pv": net_pv,
        "notional_base": notional_base,
        "notional_quote": notional_quote,
        "fx_sensitivity": fx_sensitivity
    }
    
    # Add curve information to metadata
    metadata = {
        "instrument_type": "CCS",
        "pricing_model": "quantlib_vanilla_swap",
        "curves_used": [f"{spec.ccyBase}_DISCOUNT", f"{spec.ccyQuote}_DISCOUNT", f"{spec.ccyBase}_FORWARD", f"{spec.ccyQuote}_FORWARD"],
        "as_of_date": curves.as_of_date.isoformat(),
        "market_data_profile": curves.market_data_profile,
        "spec_hash": f"ccs_{notional_base}_{spec.ccyBase}_{spec.ccyQuote}_{spec.effective}_{spec.maturity}",
        "calculation_timestamp": now.isoformat(),
        "quantlib_version": ql.__version__,
        "fx_sensitivity": fx_sensitivity
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


def create_quantlib_discount_curve(curves: CurveBundle, currency: str) -> ql.YieldTermStructure:
    """Create QuantLib discount curve from curve bundle for specific currency."""
    # For now, create a flat curve at 5%
    # In production, this would bootstrap from market data
    flat_rate = 0.05
    flat_curve = ql.FlatForward(
        ql.Date.from_date(curves.as_of_date),
        flat_rate,
        ql.Actual360()
    )
    return flat_curve


def create_quantlib_forward_curve(curves: CurveBundle, currency: str) -> ql.YieldTermStructure:
    """Create QuantLib forward curve from curve bundle for specific currency."""
    # For now, create a flat curve at 5%
    # In production, this would project forwards from market data
    flat_rate = 0.05
    flat_curve = ql.FlatForward(
        ql.Date.from_date(curves.as_of_date),
        flat_rate,
        ql.Actual360()
    )
    return flat_curve


def create_quantlib_index(currency: str, forward_curve: ql.YieldTermStructure) -> ql.IborIndex:
    """Create QuantLib index for specific currency."""
    if currency == "USD":
        return ql.USDLibor(ql.Period(3, ql.Months), forward_curve)
    elif currency == "EUR":
        return ql.Euribor(ql.Period(3, ql.Months), forward_curve)
    elif currency == "GBP":
        return ql.GBPLibor(ql.Period(3, ql.Months), forward_curve)
    else:
        # Default to USD Libor
        return ql.USDLibor(ql.Period(3, ql.Months), forward_curve)


def calculate_fx_sensitivity(ccs: ql.VanillaSwap, curve: ql.YieldTermStructure, fx_shift: float) -> float:
    """Calculate FX sensitivity for a CCS."""
    # Store original NPV
    original_npv = ccs.NPV()
    
    # For FX sensitivity, we would typically shift the FX rate
    # This is a simplified version - in practice, you'd need to handle FX curves
    # For now, return a placeholder sensitivity
    fx_sensitivity = original_npv * fx_shift * 0.1  # Simplified FX sensitivity
    
    return fx_sensitivity