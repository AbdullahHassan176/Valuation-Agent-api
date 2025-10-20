from typing import Dict, Union, List
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, date
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..schemas.run import RunRequest, RunStatus, PVBreakdown, RunStatusEnum
from ..schemas.instrument import IRSSpec, CCSSpec
from ..validators.math import validate_irs_spec, validate_ccs_spec, validate_market_data_profile, validate_approach_list
from ..core.curves.base import bootstrap_curves
from ..core.pricing.irs import price_irs
from ..core.pricing.ccs import price_ccs
from ..core.governance.ifrs13 import IFRS13Governance

router = APIRouter(prefix="/runs", tags=["runs"])

# In-memory storage for demo purposes
runs_db: Dict[str, RunStatus] = {}
results_db: Dict[str, PVBreakdown] = {}

# Thread pool for running pricing calculations
executor = ThreadPoolExecutor(max_workers=4)

@router.post("/", response_model=RunStatus, status_code=status.HTTP_201_CREATED)
async def create_run(request: RunRequest) -> RunStatus:
    """Create a new valuation run with validation and queuing"""
    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Validate the request
    validation_errors = []
    
    # Validate market data profile
    if not validate_market_data_profile(request.marketDataProfile):
        validation_errors.append(f"Invalid market data profile: {request.marketDataProfile}")
    
    # Validate approaches
    approach_errors = validate_approach_list(request.approach)
    validation_errors.extend(approach_errors)
    
    # Validate instrument specification
    if isinstance(request.spec, IRSSpec):
        spec_errors = validate_irs_spec(request.spec)
        validation_errors.extend(spec_errors)
    elif isinstance(request.spec, CCSSpec):
        spec_errors = validate_ccs_spec(request.spec)
        validation_errors.extend(spec_errors)
    
    # Validate XVA configuration if provided
    if request.xva_config:
        xva_errors = _validate_xva_config(request.xva_config)
        validation_errors.extend(xva_errors)
    
    # If validation fails, return error
    if validation_errors:
        error_message = "; ".join(validation_errors)
        run_status = RunStatus(
            id=run_id,
            status=RunStatusEnum.FAILED,
            created_at=now,
            updated_at=now,
            request=request,
            error_message=error_message
        )
        runs_db[run_id] = run_status
        return run_status
    
    # Create queued run
    run_status = RunStatus(
        id=run_id,
        status=RunStatusEnum.QUEUED,
        created_at=now,
        updated_at=now,
        request=request,
        error_message=None
    )
    
    runs_db[run_id] = run_status
    
    # Queue the pricing calculation
    asyncio.create_task(process_run(run_id))
    
    return run_status

async def process_run(run_id: str) -> None:
    """Process a queued run by running the pricing calculation"""
    if run_id not in runs_db:
        return
    
    run_status = runs_db[run_id]
    
    try:
        # Update status to running
        run_status.status = RunStatusEnum.RUNNING
        run_status.updated_at = datetime.utcnow()
        runs_db[run_id] = run_status
        
        # Run pricing calculation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, _run_pricing_calculation, run_status.request)
        
        # Set run_id in result
        result.run_id = run_id
        
        # Store result
        results_db[run_id] = result
        
        # Perform IFRS-13 assessment
        governance = IFRS13Governance()
        ifrs13_assessment = governance.assess_compliance(result, run_status.request.spec)
        
        # Update status based on IFRS-13 assessment
        if ifrs13_assessment.needs_review:
            run_status.status = RunStatusEnum.NEEDS_REVIEW
        else:
            run_status.status = RunStatusEnum.COMPLETED
        
        # Store IFRS-13 assessment
        run_status.ifrs13_assessment = {
            "fair_value_level": ifrs13_assessment.fair_value_level.value,
            "data_sources": [
                {
                    "name": source.name,
                    "observability": source.observability.value,
                    "level": source.level.value,
                    "description": source.description,
                    "rationale": source.rationale
                }
                for source in ifrs13_assessment.data_sources
            ],
            "day1_pnl": ifrs13_assessment.day1_pnl,
            "day1_pnl_tolerance": ifrs13_assessment.day1_pnl_tolerance,
            "day1_pnl_within_tolerance": ifrs13_assessment.day1_pnl_within_tolerance,
            "principal_market": ifrs13_assessment.principal_market,
            "valuation_technique": ifrs13_assessment.valuation_technique,
            "key_inputs": ifrs13_assessment.key_inputs,
            "unobservable_inputs": ifrs13_assessment.unobservable_inputs,
            "needs_review": ifrs13_assessment.needs_review,
            "review_reason": ifrs13_assessment.review_reason,
            "reviewer_rationale": ifrs13_assessment.reviewer_rationale,
            "ready_for_export": ifrs13_assessment.ready_for_export,
            "assessed_at": ifrs13_assessment.assessed_at.isoformat()
        }
        
        run_status.updated_at = datetime.utcnow()
        runs_db[run_id] = run_status
        
    except Exception as e:
        # Update status to failed
        run_status.status = RunStatusEnum.FAILED
        run_status.error_message = str(e)
        run_status.updated_at = datetime.utcnow()
        runs_db[run_id] = run_status

def _run_pricing_calculation(request: RunRequest) -> PVBreakdown:
    """Run the actual pricing calculation (synchronous)"""
    # Bootstrap curves
    curves = bootstrap_curves(request.marketDataProfile, request.asOf)
    
    # Run appropriate pricing function based on spec type
    if isinstance(request.spec, IRSSpec):
        result = price_irs(request.spec, curves)
    elif isinstance(request.spec, CCSSpec):
        result = price_ccs(request.spec, curves)
    else:
        raise ValueError(f"Unsupported spec type: {type(request.spec)}")
    
    # Compute XVA if requested
    if request.xva_config:
        from ..xva.simple import compute_xva, create_synthetic_ee_grid, create_proxy_credit_curve
        from ..schemas.run import XVABreakdown
        
        # Create synthetic EE grid for testing
        ee_grid = create_synthetic_ee_grid(
            start_date=request.asOf,
            end_date=request.spec.maturity,
            frequency="monthly",
            peak_exposure=abs(result.total_pv) * 0.1,  # 10% of PV as peak exposure
            currency=request.spec.ccy if hasattr(request.spec, 'ccy') else 'USD'
        )
        
        # Convert Pydantic configs to XVA module objects
        from ..xva.simple import XVAConfig as XVAConfigImpl, CreditCurve, CSAConfig as CSAConfigImpl
        
        xva_config_impl = XVAConfigImpl(
            compute_cva=request.xva_config.compute_cva,
            compute_dva=request.xva_config.compute_dva,
            compute_fva=request.xva_config.compute_fva,
            counterparty_credit_curve=CreditCurve(
                name=request.xva_config.counterparty_credit_curve.name,
                currency=request.xva_config.counterparty_credit_curve.currency,
                tenors=request.xva_config.counterparty_credit_curve.tenors,
                spreads=request.xva_config.counterparty_credit_curve.spreads,
                recovery_rate=request.xva_config.counterparty_credit_curve.recovery_rate
            ) if request.xva_config.counterparty_credit_curve else None,
            own_credit_curve=CreditCurve(
                name=request.xva_config.own_credit_curve.name,
                currency=request.xva_config.own_credit_curve.currency,
                tenors=request.xva_config.own_credit_curve.tenors,
                spreads=request.xva_config.own_credit_curve.spreads,
                recovery_rate=request.xva_config.own_credit_curve.recovery_rate
            ) if request.xva_config.own_credit_curve else None,
            funding_curve=CreditCurve(
                name=request.xva_config.funding_curve.name,
                currency=request.xva_config.funding_curve.currency,
                tenors=request.xva_config.funding_curve.tenors,
                spreads=request.xva_config.funding_curve.spreads,
                recovery_rate=request.xva_config.funding_curve.recovery_rate
            ) if request.xva_config.funding_curve else None,
            csa_config=CSAConfigImpl(
                threshold=request.xva_config.csa_config.threshold,
                minimum_transfer_amount=request.xva_config.csa_config.minimum_transfer_amount,
                rounding=request.xva_config.csa_config.rounding,
                collateral_currency=request.xva_config.csa_config.collateral_currency,
                interest_rate=request.xva_config.csa_config.interest_rate,
                posting_frequency=request.xva_config.csa_config.posting_frequency
            ) if request.xva_config.csa_config else None
        )
        
        # Compute XVA
        xva_results = compute_xva(ee_grid, xva_config_impl)
        
        # Add XVA to result
        result.xva = XVABreakdown(
            cva=xva_results.cva,
            dva=xva_results.dva,
            fva=xva_results.fva,
            total_xva=xva_results.total_xva,
            currency=xva_results.currency,
            details=xva_results.details
        )
        
        # Update total PV to include XVA
        result.total_pv += xva_results.total_xva
        result.components["xva"] = xva_results.total_xva
    
    # Handle Hull-White 1-Factor model calibration if requested
    if "HW1F-variance-matching" in request.approach:
        from ..models.hw1f import calibrate_hw1f_variance_matching, create_demo_volatility_surface, create_demo_curves
        
        # Create demo volatility surface and curves for calibration
        volatility_surface = create_demo_volatility_surface()
        demo_curves = create_demo_curves()
        
        # Calibrate HW1F model (stub implementation)
        hw1f_params = calibrate_hw1f_variance_matching(volatility_surface, demo_curves)
        
        # Store model version in lineage
        result.model_hash = f"{result.model_hash}_HW1F:{hw1f_params.model_version}"
        
        # Add HW1F parameters to metadata
        result.metadata["hw1f_params"] = hw1f_params.to_dict()
        result.metadata["hw1f_calibration"] = {
            "method": "variance_matching",
            "calibrated_at": hw1f_params.calibrated_at.isoformat() if hw1f_params.calibrated_at else None,
            "model_version": hw1f_params.model_version
        }
    
    return result

def _validate_xva_config(xva_config) -> List[str]:
    """Validate XVA configuration and CSA requirements"""
    errors = []
    
    # Check if XVA is requested but required inputs are missing
    if xva_config.compute_cva and not xva_config.counterparty_credit_curve:
        errors.append("CVA requested but counterparty credit curve not provided")
    
    if xva_config.compute_dva and not xva_config.own_credit_curve:
        errors.append("DVA requested but own credit curve not provided")
    
    if xva_config.compute_fva and not xva_config.funding_curve:
        errors.append("FVA requested but funding curve not provided")
    
    # Check CSA requirements for FVA
    if xva_config.compute_fva and not xva_config.csa_config:
        errors.append("FVA requested but CSA configuration not provided - XVA calculation requires CSA terms")
    
    # Validate credit curves if provided
    if xva_config.counterparty_credit_curve:
        curve_errors = _validate_credit_curve(xva_config.counterparty_credit_curve, "counterparty")
        errors.extend(curve_errors)
    
    if xva_config.own_credit_curve:
        curve_errors = _validate_credit_curve(xva_config.own_credit_curve, "own")
        errors.extend(curve_errors)
    
    if xva_config.funding_curve:
        curve_errors = _validate_credit_curve(xva_config.funding_curve, "funding")
        errors.extend(curve_errors)
    
    return errors

def _validate_credit_curve(curve, curve_type: str) -> List[str]:
    """Validate credit curve configuration"""
    errors = []
    
    if not curve.name:
        errors.append(f"{curve_type} credit curve name is required")
    
    if not curve.currency:
        errors.append(f"{curve_type} credit curve currency is required")
    
    if not curve.tenors or len(curve.tenors) == 0:
        errors.append(f"{curve_type} credit curve tenors are required")
    
    if not curve.spreads or len(curve.spreads) == 0:
        errors.append(f"{curve_type} credit curve spreads are required")
    
    if len(curve.tenors) != len(curve.spreads):
        errors.append(f"{curve_type} credit curve tenors and spreads must have same length")
    
    if curve.recovery_rate < 0 or curve.recovery_rate > 1:
        errors.append(f"{curve_type} credit curve recovery rate must be between 0 and 1")
    
    return errors

@router.get("/", response_model=List[RunStatus])
async def list_runs() -> List[RunStatus]:
    """Get all valuation runs"""
    return list(runs_db.values())

@router.get("/{run_id}", response_model=RunStatus)
async def get_run(run_id: str) -> RunStatus:
    """Get the status of a valuation run"""
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    return runs_db[run_id]

@router.get("/{run_id}/result", response_model=PVBreakdown)
async def get_run_result(run_id: str) -> PVBreakdown:
    """Get the result of a valuation run"""
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    run_status = runs_db[run_id]
    
    # Check if run is completed or needs review
    if run_status.status not in [RunStatusEnum.COMPLETED, RunStatusEnum.NEEDS_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run {run_id} is not completed yet. Status: {run_status.status}"
        )
    
    # Return the calculated result
    if run_id not in results_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result for run {run_id} not found"
        )
    
    return results_db[run_id]

@router.post("/{run_id}/review")
async def submit_review(run_id: str, rationale: str) -> RunStatus:
    """Submit reviewer rationale for a run that needs review"""
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    run_status = runs_db[run_id]
    
    if run_status.status != RunStatusEnum.NEEDS_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run {run_id} does not need review"
        )
    
    if not run_status.ifrs13_assessment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No IFRS-13 assessment found for run {run_id}"
        )
    
    # Update assessment with rationale
    governance = IFRS13Governance()
    assessment_data = run_status.ifrs13_assessment
    
    # Create assessment object from stored data
    from ..core.governance.ifrs13 import IFRS13Assessment, FairValueLevel, DataObservability, DataSource
    assessment = IFRS13Assessment(
        fair_value_level=FairValueLevel(assessment_data["fair_value_level"]),
        data_sources=[
            DataSource(
                name=source["name"],
                observability=DataObservability(source["observability"]),
                level=FairValueLevel(source["level"]),
                description=source["description"],
                rationale=source.get("rationale")
            )
            for source in assessment_data["data_sources"]
        ],
        day1_pnl=assessment_data["day1_pnl"],
        day1_pnl_tolerance=assessment_data["day1_pnl_tolerance"],
        day1_pnl_within_tolerance=assessment_data["day1_pnl_within_tolerance"],
        principal_market=assessment_data["principal_market"],
        valuation_technique=assessment_data["valuation_technique"],
        key_inputs=assessment_data["key_inputs"],
        unobservable_inputs=assessment_data["unobservable_inputs"],
        needs_review=assessment_data["needs_review"],
        review_reason=assessment_data.get("review_reason")
    )
    
    # Update with rationale
    updated_assessment = governance.update_assessment_with_rationale(assessment, rationale)
    
    # Update run status
    run_status.status = RunStatusEnum.COMPLETED
    run_status.updated_at = datetime.utcnow()
    
    # Update assessment in run status
    run_status.ifrs13_assessment.update({
        "reviewer_rationale": updated_assessment.reviewer_rationale,
        "ready_for_export": updated_assessment.ready_for_export,
        "needs_review": updated_assessment.needs_review
    })
    
    runs_db[run_id] = run_status
    
    return run_status
