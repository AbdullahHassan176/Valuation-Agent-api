from typing import Dict, Union
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, date
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..schemas.run import RunRequest, RunStatus, PVBreakdown, RunStatus as RunStatusEnum
from ..schemas.instrument import IRSSpec, CCSSpec
from ..validators.math import validate_irs_spec, validate_ccs_spec, validate_market_data_profile, validate_approach_list
from ..core.curves.base import bootstrap_curves
from ..core.pricing.irs import price_irs
from ..core.pricing.ccs import price_ccs

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
        
        # Update status to completed
        run_status.status = RunStatusEnum.COMPLETED
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
    
    return result

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
    
    # Check if run is completed
    if run_status.status != RunStatusEnum.COMPLETED:
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
