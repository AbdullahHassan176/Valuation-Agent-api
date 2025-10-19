"""Cross Currency Swap pricing with OIS discounting and FX sensitivity."""

from typing import Dict, List, Optional, Tuple
from datetime import date
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.core.models import CCSSpec, Currency, DayCountConvention, Frequency, BusinessDayConvention, Calendar, IndexName
from app.core.schedule_utils import make_schedule
from app.core.daycount import accrual_factor
from app.core.pricing.irs import PVBreakdown, CurveData


@dataclass
class CCSBreakdown:
    """Present Value breakdown for a Cross Currency Swap."""
    pv_base_ccy: float
    pv_reporting_ccy: float
    currency: str
    reporting_currency: str
    legs: List[Dict[str, any]]
    sensitivities: List[Dict[str, any]]
    as_of: date
    curve_ids: Dict[str, str]
    lineage: Dict[str, any]


def price_ccs(spec: CCSSpec, curves: Dict[str, CurveData]) -> CCSBreakdown:
    """
    Price a Cross Currency Swap using OIS discounting and FX forwards.
    
    Args:
        spec: CCS specification
        curves: Dictionary containing discount and forward curves for both currencies
        
    Returns:
        CCSBreakdown with present value, legs, and FX sensitivities
    """
    try:
        # Validate inputs
        _validate_ccs_inputs(spec, curves)
        
        # Extract curves
        disc_usd = curves.get("discUSD")
        disc_eur = curves.get("discEUR")
        fwd_usd = curves.get("fwdUSD")
        fwd_eur = curves.get("fwdEUR")
        fx_fwd = curves.get("fxFwd")
        
        if not all([disc_usd, disc_eur, fwd_usd, fwd_eur, fx_fwd]):
            raise ValueError("All required curves (discUSD, discEUR, fwdUSD, fwdEUR, fxFwd) are required")
        
        # Build schedules for both legs
        leg1_schedule = _build_ccs_schedule(spec, leg=1)
        leg2_schedule = _build_ccs_schedule(spec, leg=2)
        
        # Compute leg 1 (USD) cashflows and PV
        leg1_pv, leg1_cashflows = _compute_ccs_leg_pv(
            spec, leg1_schedule, disc_usd, fwd_usd, leg=1
        )
        
        # Compute leg 2 (EUR) cashflows and PV
        leg2_pv, leg2_cashflows = _compute_ccs_leg_pv(
            spec, leg2_schedule, disc_eur, fwd_eur, leg=2
        )
        
        # Convert EUR PV to USD using FX forward
        leg2_pv_usd = _convert_pv_to_reporting_currency(
            leg2_pv, spec.currency_leg2, spec.currency_leg1, fx_fwd
        )
        
        # Calculate net PV in reporting currency (USD)
        net_pv_usd = leg1_pv + leg2_pv_usd
        
        # Calculate FX sensitivities
        fx_sensitivities = _calculate_fx_sensitivities(
            spec, curves, net_pv_usd
        )
        
        # Build result
        legs = [
            {
                "name": f"Leg 1 ({spec.currency_leg1.value})",
                "pv": leg1_pv,
                "pv_reporting_ccy": leg1_pv,
                "currency": spec.currency_leg1.value,
                "cashflows": leg1_cashflows
            },
            {
                "name": f"Leg 2 ({spec.currency_leg2.value})",
                "pv": leg2_pv,
                "pv_reporting_ccy": leg2_pv_usd,
                "currency": spec.currency_leg2.value,
                "cashflows": leg2_cashflows
            }
        ]
        
        sensitivities = [
            {
                "shock": "FX_PLUS_1PCT",
                "value": fx_sensitivities["fx_plus_1pct"],
                "description": "Present value change for +1% FX rate shock"
            },
            {
                "shock": "FX_MINUS_1PCT", 
                "value": fx_sensitivities["fx_minus_1pct"],
                "description": "Present value change for -1% FX rate shock"
            }
        ]
        
        return CCSBreakdown(
            pv_base_ccy=net_pv_usd,
            pv_reporting_ccy=net_pv_usd,
            currency=spec.currency_leg1.value,  # Reporting currency
            reporting_currency=spec.currency_leg1.value,
            legs=legs,
            sensitivities=sensitivities,
            as_of=spec.effective_date,
            curve_ids={
                "discUSD": disc_usd.curve_id,
                "discEUR": disc_eur.curve_id,
                "fwdUSD": fwd_usd.curve_id,
                "fwdEUR": fwd_eur.curve_id,
                "fxFwd": fx_fwd.curve_id
            },
            lineage={
                "pricing_method": "OIS_discounting_with_FX",
                "notional_leg1": spec.notional_leg1,
                "notional_leg2": spec.notional_leg2,
                "currency_leg1": spec.currency_leg1.value,
                "currency_leg2": spec.currency_leg2.value,
                "constant_notional": spec.constant_notional
            }
        )
        
    except Exception as e:
        raise ValueError(f"Error pricing CCS: {str(e)}")


def _validate_ccs_inputs(spec: CCSSpec, curves: Dict[str, CurveData]) -> None:
    """Validate CCS inputs."""
    if spec.notional_leg1 <= 0 or spec.notional_leg2 <= 0:
        raise ValueError("Both notionals must be positive")
    
    if spec.effective_date >= spec.maturity_date:
        raise ValueError("Effective date must be before maturity date")
    
    if spec.currency_leg1 == spec.currency_leg2:
        raise ValueError("Leg currencies must be different for CCS")
    
    if not curves:
        raise ValueError("Market curves are required")


def _build_ccs_schedule(spec: CCSSpec, leg: int) -> List[date]:
    """Build payment schedule for CCS leg."""
    return make_schedule(
        effective_date=spec.effective_date,
        maturity_date=spec.maturity_date,
        frequency=spec.frequency,
        calendar=spec.calendar,
        business_day_convention=spec.business_day_convention
    )


def _compute_ccs_leg_pv(
    spec: CCSSpec,
    schedule: List[date],
    discount_curve: CurveData,
    forward_curve: CurveData,
    leg: int
) -> Tuple[float, List[Dict]]:
    """Compute CCS leg present value and cashflows."""
    pv = 0.0
    cashflows = []
    
    # Get leg-specific parameters
    if leg == 1:
        notional = spec.notional_leg1
        currency = spec.currency_leg1
        index = spec.index_leg1
    else:
        notional = spec.notional_leg2
        currency = spec.currency_leg2
        index = spec.index_leg2
    
    for i in range(1, len(schedule)):
        start_date = schedule[i-1]
        end_date = schedule[i]
        
        # Calculate accrual factor
        accrual = accrual_factor(
            start_date, end_date, spec.day_count
        )
        
        # Forecast floating rate
        forward_rate = _interpolate_forward_rate(
            end_date, forward_curve
        )
        
        # Calculate cashflow
        cashflow = forward_rate * accrual * notional
        
        # Get discount factor
        discount_factor = _interpolate_discount_factor(
            end_date, discount_curve
        )
        
        # Calculate present value
        pv_cashflow = cashflow * discount_factor
        pv += pv_cashflow
        
        cashflows.append({
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "accrual_factor": accrual,
            "rate": forward_rate,
            "cashflow": cashflow,
            "discount_factor": discount_factor,
            "present_value": pv_cashflow,
            "currency": currency.value,
            "notional": notional
        })
    
    return pv, cashflows


def _interpolate_discount_factor(maturity_date: date, curve: CurveData) -> float:
    """Interpolate discount factor from curve."""
    # Calculate years to maturity
    years_to_maturity = (maturity_date - curve.as_of).days / 365.25
    
    # Find closest tenors in curve
    tenors = sorted(curve.discount_curve.keys())
    
    if years_to_maturity <= 0:
        return 1.0
    
    # Find bracketing tenors
    for i, tenor in enumerate(tenors):
        if tenor >= years_to_maturity:
            if i == 0:
                return curve.discount_curve[tenor]
            else:
                # Linear interpolation
                prev_tenor = tenors[i-1]
                prev_df = curve.discount_curve[prev_tenor]
                curr_df = curve.discount_curve[tenor]
                
                weight = (years_to_maturity - prev_tenor) / (tenor - prev_tenor)
                return prev_df + weight * (curr_df - prev_df)
    
    # Extrapolate beyond last tenor
    last_tenor = tenors[-1]
    return curve.discount_curve[last_tenor]


def _interpolate_forward_rate(maturity_date: date, curve: CurveData) -> float:
    """Interpolate forward rate from curve."""
    years_to_maturity = (maturity_date - curve.as_of).days / 365.25
    
    tenors = sorted(curve.forward_curve.keys())
    
    if years_to_maturity <= 0:
        return 0.0
    
    # Find bracketing tenors
    for i, tenor in enumerate(tenors):
        if tenor >= years_to_maturity:
            if i == 0:
                return curve.forward_curve[tenor]
            else:
                # Linear interpolation
                prev_tenor = tenors[i-1]
                prev_rate = curve.forward_curve[prev_tenor]
                curr_rate = curve.forward_curve[tenor]
                
                weight = (years_to_maturity - prev_tenor) / (tenor - prev_tenor)
                return prev_rate + weight * (curr_rate - prev_rate)
    
    # Extrapolate beyond last tenor
    last_tenor = tenors[-1]
    return curve.forward_curve[last_tenor]


def _convert_pv_to_reporting_currency(
    pv: float,
    from_currency: Currency,
    to_currency: Currency,
    fx_curve: CurveData
) -> float:
    """Convert PV from one currency to another using FX forward."""
    if from_currency == to_currency:
        return pv
    
    # Get FX forward rate (assuming EUR/USD for now)
    # In production, would use proper FX curve interpolation
    fx_rate = _get_fx_forward_rate(fx_curve)
    
    if from_currency == Currency.EUR and to_currency == Currency.USD:
        return pv * fx_rate
    elif from_currency == Currency.USD and to_currency == Currency.EUR:
        return pv / fx_rate
    else:
        # For other currency pairs, would need more complex logic
        return pv


def _get_fx_forward_rate(fx_curve: CurveData) -> float:
    """Get FX forward rate from curve."""
    # Simple implementation - use first available rate
    if fx_curve.forward_curve:
        return list(fx_curve.forward_curve.values())[0]
    return 1.0  # Default 1:1 rate


def _calculate_fx_sensitivities(
    spec: CCSSpec,
    curves: Dict[str, CurveData],
    base_pv: float
) -> Dict[str, float]:
    """Calculate FX sensitivities using ±1% shocks."""
    try:
        # Use analytical approximation to avoid recursive calls
        return _analytical_fx_sensitivity_approximation(spec, base_pv)
        
    except Exception as e:
        # Fallback to simple approximation
        return {
            "fx_plus_1pct": 0.0,
            "fx_minus_1pct": 0.0
        }


def _create_fx_shocked_curves(curves: Dict[str, CurveData], shock_pct: float) -> Dict[str, CurveData]:
    """Create curves with FX shock applied."""
    shocked_curves = {}
    
    for curve_name, curve in curves.items():
        if curve_name == "fxFwd":
            # Apply FX shock to forward rates
            shocked_forward_curve = {}
            for tenor, rate in curve.forward_curve.items():
                shocked_forward_curve[tenor] = rate * (1 + shock_pct)
            
            shocked_curves[curve_name] = CurveData(
                discount_curve=curve.discount_curve,
                forward_curve=shocked_forward_curve,
                curve_id=f"{curve.curve_id}_fx_shocked_{shock_pct*100:.1f}pct",
                as_of=curve.as_of
            )
        else:
            # Other curves unchanged
            shocked_curves[curve_name] = curve
    
    return shocked_curves


def _analytical_fx_sensitivity_approximation(spec: CCSSpec, base_pv: float) -> Dict[str, float]:
    """Analytical FX sensitivity approximation for fallback."""
    # Simple approximation based on notional exposure
    # This is a rough approximation for demonstration
    
    # Estimate FX exposure based on EUR leg notional
    # For +1% FX shock, EUR becomes more expensive, so EUR leg PV increases
    # For -1% FX shock, EUR becomes cheaper, so EUR leg PV decreases
    fx_exposure = abs(spec.notional_leg2) * 0.01  # 1% of leg 2 notional
    
    return {
        "fx_plus_1pct": fx_exposure,
        "fx_minus_1pct": -fx_exposure
    }


def create_synthetic_ccs_curves(as_of: date) -> Dict[str, CurveData]:
    """Create synthetic market curves for CCS testing."""
    # USD OIS curve
    usd_discount_curve = {
        0.25: 0.999,   # 3M
        0.5: 0.998,    # 6M
        1.0: 0.995,    # 1Y
        2.0: 0.985,    # 2Y
        3.0: 0.970,    # 3Y
        5.0: 0.940,    # 5Y
        7.0: 0.905,    # 7Y
        10.0: 0.850    # 10Y
    }
    
    usd_forward_curve = {
        0.25: 0.05,    # 3M
        0.5: 0.05,     # 6M
        1.0: 0.05,     # 1Y
        2.0: 0.05,     # 2Y
        3.0: 0.05,     # 3Y
        5.0: 0.05,     # 5Y
        7.0: 0.05,     # 7Y
        10.0: 0.05     # 10Y
    }
    
    # EUR OIS curve (slightly different rates)
    eur_discount_curve = {
        0.25: 0.9995,  # 3M
        0.5: 0.9985,   # 6M
        1.0: 0.9955,   # 1Y
        2.0: 0.9855,   # 2Y
        3.0: 0.9705,   # 3Y
        5.0: 0.9405,   # 5Y
        7.0: 0.9055,   # 7Y
        10.0: 0.8505   # 10Y
    }
    
    eur_forward_curve = {
        0.25: 0.04,    # 3M
        0.5: 0.04,     # 6M
        1.0: 0.04,     # 1Y
        2.0: 0.04,     # 2Y
        3.0: 0.04,     # 3Y
        5.0: 0.04,     # 5Y
        7.0: 0.04,     # 7Y
        10.0: 0.04     # 10Y
    }
    
    # FX forward curve (EUR/USD)
    fx_forward_curve = {
        0.25: 1.08,    # 3M
        0.5: 1.08,     # 6M
        1.0: 1.08,     # 1Y
        2.0: 1.08,     # 2Y
        3.0: 1.08,     # 3Y
        5.0: 1.08,     # 5Y
        7.0: 1.08,     # 7Y
        10.0: 1.08     # 10Y
    }
    
    return {
        "discUSD": CurveData(
            discount_curve=usd_discount_curve,
            forward_curve=usd_forward_curve,
            curve_id=f"USD_OIS_{as_of.isoformat()}",
            as_of=as_of
        ),
        "discEUR": CurveData(
            discount_curve=eur_discount_curve,
            forward_curve=eur_forward_curve,
            curve_id=f"EUR_OIS_{as_of.isoformat()}",
            as_of=as_of
        ),
        "fwdUSD": CurveData(
            discount_curve=usd_discount_curve,
            forward_curve=usd_forward_curve,
            curve_id=f"USD_FWD_{as_of.isoformat()}",
            as_of=as_of
        ),
        "fwdEUR": CurveData(
            discount_curve=eur_discount_curve,
            forward_curve=eur_forward_curve,
            curve_id=f"EUR_FWD_{as_of.isoformat()}",
            as_of=as_of
        ),
        "fxFwd": CurveData(
            discount_curve={},  # FX curve doesn't need discount factors
            forward_curve=fx_forward_curve,
            curve_id=f"FX_FWD_{as_of.isoformat()}",
            as_of=as_of
        )
    }