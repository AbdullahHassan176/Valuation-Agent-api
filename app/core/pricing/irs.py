from typing import Dict, Any
from datetime import datetime, date, timedelta
from ..schemas.instrument import IRSSpec
from ..schemas.run import PVBreakdown
from ..curves.base import CurveBundle, interpolate_curve
from ..curves.ois import bootstrap_usd_ois_curve, get_discount_factor
from ..curves.forward import project_flat_forwards, create_simple_schedule

def price_irs(spec: IRSSpec, curves: CurveBundle) -> PVBreakdown:
    """
    Price an Interest Rate Swap with DCF calculations
    
    Args:
        spec: IRS specification
        curves: Curve bundle with discount and forward curves
        
    Returns:
        PVBreakdown with present value components
    """
    now = datetime.utcnow()
    
    # Bootstrap USD OIS curve for discounting
    discount_curve = bootstrap_usd_ois_curve(curves.as_of_date)
    
    # Calculate fixed leg PV using DCF
    fixed_leg_pv = calculate_fixed_leg_pv(spec, discount_curve)
    
    # Calculate floating leg PV (par by construction for now)
    floating_leg_pv = calculate_floating_leg_pv(spec, discount_curve)
    
    # Net PV (assuming pay fixed)
    net_pv = floating_leg_pv - fixed_leg_pv
    
    # Get curve hashes for lineage
    market_data_hash = f"usd_ois_quotes_{curves.market_data_profile}_{curves.as_of_date}"
    model_hash = f"dcf_irs_model_{now.strftime('%Y%m%d_%H%M%S')}"
    
    components = {
        "fixed_leg_pv": fixed_leg_pv,
        "floating_leg_pv": floating_leg_pv,
        "net_pv": net_pv,
        "notional": spec.notional,
        "currency": spec.ccy,
        "fixed_rate": spec.fixedRate or 0.0
    }
    
    # Add curve information to metadata
    metadata = {
        "instrument_type": "IRS",
        "pricing_model": "dcf_irs_pricer",
        "curves_used": ["USD_OIS_DISCOUNT"],
        "as_of_date": curves.as_of_date.isoformat(),
        "market_data_profile": curves.market_data_profile,
        "spec_hash": f"irs_{spec.notional}_{spec.ccy}_{spec.effective}_{spec.maturity}",
        "calculation_timestamp": now.isoformat(),
        "discount_curve_nodes": len(discount_curve.curve_points) if hasattr(discount_curve, 'curve_points') else 0
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
    Calculate fixed leg present value using DCF
    
    Args:
        spec: IRS specification
        discount_curve: Discount curve reference
        
    Returns:
        Fixed leg present value
    """
    # Create simple payment schedule
    schedule = create_simple_schedule(spec.effective, spec.maturity, spec.freqFixed)
    
    fixed_rate = spec.fixedRate or 0.05  # Default to 5% if not provided
    notional = spec.notional
    
    total_pv = 0.0
    
    for i in range(len(schedule) - 1):
        start_date = schedule[i]
        end_date = schedule[i + 1]
        
        # Calculate day count (simple ACT/360)
        day_count = (end_date - start_date).days / 360.0
        
        # Calculate payment amount
        payment_amount = notional * fixed_rate * day_count
        
        # Get discount factor
        discount_factor = get_discount_factor(discount_curve, end_date)
        
        # Calculate present value
        pv = payment_amount * discount_factor
        total_pv += pv
    
    return total_pv

def calculate_floating_leg_pv(spec: IRSSpec, discount_curve) -> float:
    """
    Calculate floating leg present value (par by construction)
    
    Args:
        spec: IRS specification
        discount_curve: Discount curve reference
        
    Returns:
        Floating leg present value (par value)
    """
    # For a par swap, floating leg PV = notional
    # This is a simplified assumption
    return spec.notional
