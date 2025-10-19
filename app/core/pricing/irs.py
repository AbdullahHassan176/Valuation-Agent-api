"""Interest Rate Swap pricing with OIS discounting and PV01 calculations."""

from typing import Dict, List, Optional, Tuple
from datetime import date
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.core.models import IRSSpec, Currency, DayCountConvention, Frequency
from app.core.schedule_utils import make_schedule
from app.core.daycount import accrual_factor


@dataclass
class PVBreakdown:
    """Present Value breakdown for an IRS."""
    pv_base_ccy: float
    currency: str
    legs: List[Dict[str, any]]
    sensitivities: List[Dict[str, any]]
    as_of: date
    curve_ids: Dict[str, str]
    lineage: Dict[str, any]


@dataclass
class CurveData:
    """Market curve data for pricing."""
    discount_curve: Dict[str, float]  # {tenor: discount_factor}
    forward_curve: Dict[str, float]   # {tenor: forward_rate}
    curve_id: str
    as_of: date


def price_irs(spec: IRSSpec, curves: Dict[str, CurveData]) -> PVBreakdown:
    """
    Price an Interest Rate Swap using OIS discounting and projected floating rates.
    
    Args:
        spec: IRS specification
        curves: Dictionary containing discount and forward curves
        
    Returns:
        PVBreakdown with present value, legs, and sensitivities
    """
    try:
        # Validate inputs
        _validate_irs_inputs(spec, curves)
        
        # Extract curves
        discount_curve = curves.get("discount")
        forward_curve = curves.get("forward")
        
        if not discount_curve or not forward_curve:
            raise ValueError("Both discount and forward curves are required")
        
        # Build schedules
        fixed_schedule = _build_fixed_schedule(spec)
        float_schedule = _build_float_schedule(spec)
        
        # Compute fixed leg cashflows and PV
        fixed_pv, fixed_cashflows = _compute_fixed_leg_pv(
            spec, fixed_schedule, discount_curve
        )
        
        # Compute floating leg cashflows and PV
        float_pv, float_cashflows = _compute_float_leg_pv(
            spec, float_schedule, discount_curve, forward_curve
        )
        
        # Calculate net PV
        if spec.pay_fixed:
            net_pv = float_pv - fixed_pv
        else:
            net_pv = fixed_pv - float_pv
        
        # Calculate PV01
        pv01 = _calculate_pv01(spec, curves, net_pv)
        
        # Build result
        legs = [
            {
                "name": "Fixed Leg",
                "pv": fixed_pv,
                "currency": spec.currency.value,
                "cashflows": fixed_cashflows
            },
            {
                "name": "Floating Leg", 
                "pv": float_pv,
                "currency": spec.currency.value,
                "cashflows": float_cashflows
            }
        ]
        
        sensitivities = [
            {
                "shock": "PV01",
                "value": pv01,
                "description": "Present value of 1 basis point parallel shift in discount curve"
            }
        ]
        
        return PVBreakdown(
            pv_base_ccy=net_pv,
            currency=spec.currency.value,
            legs=legs,
            sensitivities=sensitivities,
            as_of=spec.effective_date,
            curve_ids={
                "discount": discount_curve.curve_id,
                "forward": forward_curve.curve_id
            },
            lineage={
                "pricing_method": "OIS_discounting",
                "fixed_rate": spec.fixed_rate,
                "notional": spec.notional,
                "pay_fixed": spec.pay_fixed
            }
        )
        
    except Exception as e:
        raise ValueError(f"Error pricing IRS: {str(e)}")


def _validate_irs_inputs(spec: IRSSpec, curves: Dict[str, CurveData]) -> None:
    """Validate IRS inputs."""
    if spec.notional <= 0:
        raise ValueError("Notional must be positive")
    
    if spec.effective_date >= spec.maturity_date:
        raise ValueError("Effective date must be before maturity date")
    
    if spec.fixed_rate is None or spec.fixed_rate < 0:
        raise ValueError("Fixed rate must be provided and non-negative")
    
    if not curves:
        raise ValueError("Market curves are required")


def _build_fixed_schedule(spec: IRSSpec) -> List[date]:
    """Build fixed leg payment schedule."""
    return make_schedule(
        effective_date=spec.effective_date,
        maturity_date=spec.maturity_date,
        frequency=spec.frequency_fixed,
        calendar=spec.calendar,
        business_day_convention=spec.business_day_convention
    )


def _build_float_schedule(spec: IRSSpec) -> List[date]:
    """Build floating leg payment schedule."""
    return make_schedule(
        effective_date=spec.effective_date,
        maturity_date=spec.maturity_date,
        frequency=spec.frequency_float,
        calendar=spec.calendar,
        business_day_convention=spec.business_day_convention
    )


def _compute_fixed_leg_pv(
    spec: IRSSpec, 
    schedule: List[date], 
    discount_curve: CurveData
) -> Tuple[float, List[Dict]]:
    """Compute fixed leg present value and cashflows."""
    if not spec.fixed_rate:
        return 0.0, []
    
    pv = 0.0
    cashflows = []
    
    for i in range(1, len(schedule)):
        start_date = schedule[i-1]
        end_date = schedule[i]
        
        # Calculate accrual factor
        accrual = accrual_factor(
            start_date, end_date, spec.day_count_fixed
        )
        
        # Calculate cashflow
        cashflow = spec.fixed_rate * accrual * spec.notional
        
        # Get discount factor (interpolate if needed)
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
            "rate": spec.fixed_rate,
            "cashflow": cashflow,
            "discount_factor": discount_factor,
            "present_value": pv_cashflow
        })
    
    return pv, cashflows


def _compute_float_leg_pv(
    spec: IRSSpec,
    schedule: List[date],
    discount_curve: CurveData,
    forward_curve: CurveData
) -> Tuple[float, List[Dict]]:
    """Compute floating leg present value and cashflows."""
    pv = 0.0
    cashflows = []
    
    for i in range(1, len(schedule)):
        start_date = schedule[i-1]
        end_date = schedule[i]
        
        # Calculate accrual factor
        accrual = accrual_factor(
            start_date, end_date, spec.day_count_float
        )
        
        # Forecast floating rate (simple approach using forward curve)
        forward_rate = _interpolate_forward_rate(
            end_date, forward_curve
        )
        
        # Calculate cashflow
        cashflow = forward_rate * accrual * spec.notional
        
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
            "present_value": pv_cashflow
        })
    
    return pv, cashflows


def _interpolate_discount_factor(maturity_date: date, curve: CurveData) -> float:
    """Interpolate discount factor from curve."""
    # Simple linear interpolation for now
    # In production, would use more sophisticated interpolation
    
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
                
                # Simple linear interpolation
                weight = (years_to_maturity - prev_tenor) / (tenor - prev_tenor)
                return prev_df + weight * (curr_df - prev_df)
    
    # Extrapolate beyond last tenor
    last_tenor = tenors[-1]
    return curve.discount_curve[last_tenor]


def _interpolate_forward_rate(maturity_date: date, curve: CurveData) -> float:
    """Interpolate forward rate from curve."""
    # Similar to discount factor interpolation
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


def _calculate_pv01(
    spec: IRSSpec, 
    curves: Dict[str, CurveData], 
    base_pv: float
) -> float:
    """Calculate PV01 using parallel shift method."""
    try:
        # Create shocked curves (+1bp)
        shocked_curves = _create_shocked_curves(curves, 0.0001)
        
        # Re-price with shocked curves
        shocked_result = price_irs(spec, shocked_curves)
        
        # PV01 is the difference in PV
        pv01 = shocked_result.pv_base_ccy - base_pv
        
        return pv01
        
    except Exception as e:
        # Fallback to analytical approximation
        return _analytical_pv01_approximation(spec, curves)


def _create_shocked_curves(curves: Dict[str, CurveData], shock_bp: float) -> Dict[str, CurveData]:
    """Create curves with parallel shift shock."""
    shocked_curves = {}
    
    for curve_name, curve in curves.items():
        shocked_discount_curve = {}
        shocked_forward_curve = {}
        
        # Apply shock to discount factors
        for tenor, df in curve.discount_curve.items():
            # Convert shock to discount factor shock
            # For small shocks: new_df ≈ old_df * (1 - shock * tenor)
            shocked_df = df * (1 - shock_bp * tenor)
            shocked_discount_curve[tenor] = max(shocked_df, 0.001)  # Avoid negative DFs
        
        # Apply shock to forward rates
        for tenor, rate in curve.forward_curve.items():
            shocked_forward_curve[tenor] = rate + shock_bp
        
        shocked_curves[curve_name] = CurveData(
            discount_curve=shocked_discount_curve,
            forward_curve=shocked_forward_curve,
            curve_id=f"{curve.curve_id}_shocked_{shock_bp}bp",
            as_of=curve.as_of
        )
    
    return shocked_curves


def _analytical_pv01_approximation(spec: IRSSpec, curves: Dict[str, CurveData]) -> float:
    """Analytical PV01 approximation for fallback."""
    # Simple approximation: PV01 ≈ -PV * average_tenor * 0.0001
    # This is a rough approximation for demonstration
    
    discount_curve = curves.get("discount")
    if not discount_curve:
        return 0.0
    
    # Calculate average tenor of the swap
    total_tenor = 0.0
    tenor_count = 0
    
    for tenor in discount_curve.discount_curve.keys():
        total_tenor += tenor
        tenor_count += 1
    
    if tenor_count == 0:
        return 0.0
    
    average_tenor = total_tenor / tenor_count
    
    # Rough PV01 approximation
    pv01 = -spec.notional * average_tenor * 0.0001
    
    return pv01


def create_synthetic_curves(as_of: date, currency: str) -> Dict[str, CurveData]:
    """Create synthetic market curves for testing."""
    # Simple synthetic curves for testing
    discount_curve = {
        0.25: 0.999,   # 3M
        0.5: 0.998,    # 6M
        1.0: 0.995,    # 1Y
        2.0: 0.985,    # 2Y
        3.0: 0.970,    # 3Y
        5.0: 0.940,    # 5Y
        7.0: 0.905,    # 7Y
        10.0: 0.850    # 10Y
    }
    
    forward_curve = {
        0.25: 0.05,    # 3M
        0.5: 0.05,     # 6M
        1.0: 0.05,     # 1Y
        2.0: 0.05,     # 2Y
        3.0: 0.05,     # 3Y
        5.0: 0.05,     # 5Y
        7.0: 0.05,     # 7Y
        10.0: 0.05     # 10Y
    }
    
    return {
        "discount": CurveData(
            discount_curve=discount_curve,
            forward_curve=forward_curve,
            curve_id=f"{currency}_synthetic_{as_of.isoformat()}",
            as_of=as_of
        ),
        "forward": CurveData(
            discount_curve=discount_curve,
            forward_curve=forward_curve,
            curve_id=f"{currency}_forward_{as_of.isoformat()}",
            as_of=as_of
        )
    }