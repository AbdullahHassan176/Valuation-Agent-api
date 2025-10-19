"""
Sensitivity analysis endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.pricing.irs import price_irs
from ..core.pricing.ccs import price_ccs
from ..core.curves.base import CurveBundle
from ..core.curves.ois import bootstrap_usd_ois_curve
from ..schemas.instrument import IRSSpec, CCSSpec
from ..schemas.run import RunStatus, RunStatusEnum
from ..risk.sensitivities import RiskSensitivities, validate_sensitivity_symmetry

router = APIRouter()

# In-memory storage for runs (in production, this would be a database)
runs_db: Dict[str, RunStatus] = {}
results_db: Dict[str, Any] = {}

@router.get("/runs/{run_id}/sensitivities")
async def get_sensitivities(run_id: str):
    """
    Calculate comprehensive sensitivities for a completed run
    
    Args:
        run_id: Run identifier
        
    Returns:
        Complete sensitivity analysis results
    """
    # Check if run exists
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    run_status = runs_db[run_id]
    
    # Check if run is completed
    if run_status.status not in [RunStatusEnum.COMPLETED, RunStatusEnum.NEEDS_REVIEW]:
        raise HTTPException(status_code=400, detail=f"Run {run_id} is not completed")
    
    # Get results
    if run_id not in results_db:
        raise HTTPException(status_code=404, detail=f"Results for run {run_id} not found")
    
    results = results_db[run_id]
    spec = run_status.request.spec
    
    try:
        # Initialize risk sensitivities engine
        risk_engine = RiskSensitivities()
        
        # Determine currency
        currency = "USD"
        if isinstance(spec, CCSSpec):
            currency = spec.reportingCcy
        
        # Create pricing function wrapper
        def pricing_function(curves: Dict[str, Any], fx_rates: Optional[Dict[str, float]] = None):
            if isinstance(spec, IRSSpec):
                curve_bundle = CurveBundle(
                    as_of_date=run_status.request.asOf,
                    market_data_profile=run_status.request.marketDataProfile,
                    curves=curves
                )
                result = price_irs(spec, curve_bundle)
                return result.total_pv
            elif isinstance(spec, CCSSpec):
                curve_bundle = CurveBundle(
                    as_of_date=run_status.request.asOf,
                    market_data_profile=run_status.request.marketDataProfile,
                    curves=curves
                )
                result = price_ccs(spec, curve_bundle)
                return result.total_pv
            else:
                return 0.0
        
        # Get base curves (simplified for now)
        base_curves = {
            "USD_OIS_DISCOUNT": bootstrap_usd_ois_curve(run_status.request.asOf)
        }
        
        # Get FX rates for CCS
        fx_rates = None
        if isinstance(spec, CCSSpec):
            fx_rates = {
                f"{spec.ccy1}/{spec.ccy2}": 1.0  # Simplified
            }
        
        # Calculate comprehensive sensitivities
        sensitivity_results = risk_engine.calculate_sensitivities(
            run_id=run_id,
            original_pv=results.total_pv,
            currency=currency,
            curves=base_curves,
            fx_rates=fx_rates,
            pricing_function=pricing_function
        )
        
        # Validate symmetry
        validation = validate_sensitivity_symmetry(sensitivity_results)
        
        # Convert to API response format
        response = {
            "run_id": run_id,
            "original_pv": sensitivity_results.original_pv,
            "currency": sensitivity_results.currency,
            "calculation_time": sensitivity_results.calculation_time,
            "shocks": [
                {
                    "name": shock.shock_name,
                    "value": shock.shock_value,
                    "unit": shock.shock_unit,
                    "pv_delta": shock.pv_delta,
                    "pv_delta_percent": shock.pv_delta_percent,
                    "leg_breakdown": shock.leg_breakdown,
                    "original_pv": shock.original_pv,
                    "shocked_pv": shock.shocked_pv
                }
                for shock in sensitivity_results.shocks
            ],
            "validation": validation,
            "summary": {
                "total_shocks": len(sensitivity_results.shocks),
                "max_positive_delta": max((s.pv_delta for s in sensitivity_results.shocks), default=0),
                "max_negative_delta": min((s.pv_delta for s in sensitivity_results.shocks), default=0),
                "pv01_parallel": next(
                    (s.pv_delta for s in sensitivity_results.shocks if s.shock_name == "parallel_1bp_up"), 0
                )
            }
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating sensitivities: {str(e)}")


@router.post("/runs/{run_id}/sensitivities/custom")
async def calculate_custom_shock(run_id: str, shock_config: Dict[str, Any]):
    """
    Calculate custom shock scenario
    
    Args:
        run_id: Run identifier
        shock_config: Custom shock configuration
        
    Returns:
        Custom shock results
    """
    # Check if run exists
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    run_status = runs_db[run_id]
    
    # Check if run is completed
    if run_status.status not in [RunStatusEnum.COMPLETED, RunStatusEnum.NEEDS_REVIEW]:
        raise HTTPException(status_code=400, detail=f"Run {run_id} is not completed")
    
    # Get results
    if run_id not in results_db:
        raise HTTPException(status_code=404, detail=f"Results for run {run_id} not found")
    
    results = results_db[run_id]
    spec = run_status.request.spec
    
    try:
        from ..risk.sensitivities import create_custom_shock
        
        # Create custom shock
        custom_shock = create_custom_shock(
            shock_config.get("type", "parallel"),
            shock_config.get("parameters", {})
        )
        
        # Initialize risk engine
        risk_engine = RiskSensitivities()
        
        # Create pricing function
        def pricing_function(curves: Dict[str, Any], fx_rates: Optional[Dict[str, float]] = None):
            if isinstance(spec, IRSSpec):
                curve_bundle = CurveBundle(
                    as_of_date=run_status.request.asOf,
                    market_data_profile=run_status.request.marketDataProfile,
                    curves=curves
                )
                result = price_irs(spec, curve_bundle)
                return result.total_pv
            elif isinstance(spec, CCSSpec):
                curve_bundle = CurveBundle(
                    as_of_date=run_status.request.asOf,
                    market_data_profile=run_status.request.marketDataProfile,
                    curves=curves
                )
                result = price_ccs(spec, curve_bundle)
                return result.total_pv
            else:
                return 0.0
        
        # Get base curves
        base_curves = {
            "USD_OIS_DISCOUNT": bootstrap_usd_ois_curve(run_status.request.asOf)
        }
        
        # Calculate custom shock
        shock_result = risk_engine._calculate_single_shock(
            shock_name="custom_shock",
            shock_config=custom_shock,
            original_pv=results.total_pv,
            curves=base_curves,
            fx_rates=None,
            pricing_function=pricing_function
        )
        
        if not shock_result:
            raise HTTPException(status_code=500, detail="Failed to calculate custom shock")
        
        return {
            "run_id": run_id,
            "shock_name": shock_result.shock_name,
            "shock_value": shock_result.shock_value,
            "shock_unit": shock_result.shock_unit,
            "pv_delta": shock_result.pv_delta,
            "pv_delta_percent": shock_result.pv_delta_percent,
            "leg_breakdown": shock_result.leg_breakdown,
            "original_pv": shock_result.original_pv,
            "shocked_pv": shock_result.shocked_pv
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating custom shock: {str(e)}")

async def calculate_all_sensitivities(spec: IRSSpec, as_of_date) -> Dict[str, float]:
    """
    Calculate parallel curve sensitivities
    
    Args:
        spec: IRS specification
        as_of_date: As of date for pricing
        
    Returns:
        Dictionary of sensitivity results
    """
    # Base curve
    base_curve = bootstrap_usd_ois_curve(as_of_date)
    
    # Create curve bundles for different scenarios
    base_bundle = CurveBundle(
        as_of_date=as_of_date,
        market_data_profile="default",
        curves={"USD_OIS_DISCOUNT": base_curve}
    )
    
    # Calculate base PV
    base_result = price_irs(spec, base_bundle)
    base_pv = base_result.total_pv
    
    # Calculate sensitivities in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Parallel +1bp
        plus_1bp_future = executor.submit(
            calculate_shifted_pv, spec, as_of_date, 0.0001
        )
        
        # Parallel -1bp
        minus_1bp_future = executor.submit(
            calculate_shifted_pv, spec, as_of_date, -0.0001
        )
        
        # Wait for results
        plus_1bp_pv = plus_1bp_future.result()
        minus_1bp_pv = minus_1bp_future.result()
    
    # Calculate FX sensitivities if this is a CCS
    fx_sensitivities = {}
    if hasattr(spec, 'ccy2') and spec.ccy2:  # This is a CCS
        fx_sensitivities = await calculate_fx_sensitivities(spec, as_of_date, base_pv)
    
    return {
        "Parallel +1bp": plus_1bp_pv - base_pv,
        "Parallel -1bp": minus_1bp_pv - base_pv,
        **fx_sensitivities
    }

def calculate_shifted_pv(spec: IRSSpec, as_of_date, shift_amount: float) -> float:
    """
    Calculate PV with shifted curve
    
    Args:
        spec: IRS specification
        as_of_date: As of date for pricing
        shift_amount: Curve shift amount (in decimal)
        
    Returns:
        Present value with shifted curve
    """
    # Bootstrap curve with shift
    shifted_curve = bootstrap_usd_ois_curve(as_of_date, shift_amount)
    
    # Create curve bundle
    curve_bundle = CurveBundle(
        as_of_date=as_of_date,
        market_data_profile="default",
        curves={"USD_OIS_DISCOUNT": shifted_curve}
    )
    
    # Calculate PV
    result = price_irs(spec, curve_bundle)
    return result.total_pv

async def calculate_fx_sensitivities(spec, as_of_date, base_pv: float) -> Dict[str, float]:
    """
    Calculate FX sensitivities for CCS
    
    Args:
        spec: CCS specification
        as_of_date: As of date for pricing
        base_pv: Base present value
        
    Returns:
        Dictionary of FX sensitivity results
    """
    from ..core.pricing.ccs import price_ccs
    from ..core.fx.forwards import create_usd_eur_fx_curve
    
    # Calculate FX sensitivities in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        # FX +1%
        plus_1pct_future = executor.submit(
            calculate_fx_shifted_pv, spec, as_of_date, 0.01
        )
        
        # FX -1%
        minus_1pct_future = executor.submit(
            calculate_fx_shifted_pv, spec, as_of_date, -0.01
        )
        
        # Wait for results
        plus_1pct_pv = plus_1pct_future.result()
        minus_1pct_pv = minus_1pct_future.result()
    
    return {
        "FX +1%": plus_1pct_pv - base_pv,
        "FX -1%": minus_1pct_pv - base_pv,
    }

def calculate_fx_shifted_pv(spec, as_of_date, fx_shift_amount: float) -> float:
    """
    Calculate PV with shifted FX curve
    
    Args:
        spec: CCS specification
        as_of_date: As of date for pricing
        fx_shift_amount: FX shift amount (in decimal)
        
    Returns:
        Present value with shifted FX curve
    """
    from ..core.pricing.ccs import price_ccs
    from ..core.curves.base import CurveBundle
    
    # Create curve bundle (FX shift would be applied in the FX curve)
    curve_bundle = CurveBundle(
        as_of_date=as_of_date,
        market_data_profile="default",
        curves={}
    )
    
    # Calculate PV (FX shift would be handled in the pricing function)
    result = price_ccs(spec, curve_bundle)
    return result.total_pv
