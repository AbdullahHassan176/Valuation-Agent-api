"""Simple runs router for IRS and CCS pricing."""

from typing import Dict, Optional, Union
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, date
import uuid

from app.core.models import IRSSpec, CCSSpec
from app.core.pricing.irs import price_irs, create_synthetic_curves, PVBreakdown
from app.core.pricing.ccs import price_ccs, create_synthetic_ccs_curves, CCSBreakdown

router = APIRouter(prefix="/runs", tags=["runs"])

# In-memory storage for demo purposes
runs_db: Dict[str, Dict] = {}


class RunRequest:
    """Request model for creating a run."""
    def __init__(self, as_of: date, spec: Union[IRSSpec, CCSSpec], market_data_profile: str = "synthetic"):
        self.as_of = as_of
        self.spec = spec
        self.market_data_profile = market_data_profile


class RunResponse:
    """Response model for run creation."""
    def __init__(self, run_id: str, state: str):
        self.run_id = run_id
        self.state = state


@router.post("/", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(request: RunRequest) -> RunResponse:
    """Create a new valuation run."""
    run_id = str(uuid.uuid4())
    
    # Validate inputs
    _validate_run_request(request)
    
    # Store run
    runs_db[run_id] = {
        "id": run_id,
        "as_of": request.as_of,
        "spec": request.spec,
        "market_data_profile": request.market_data_profile,
        "state": "completed",  # For simplicity, complete immediately
        "created_at": datetime.utcnow(),
        "result": None
    }
    
    # Process the run
    try:
        # Determine pricing method based on spec type
        if isinstance(request.spec, IRSSpec):
            # Create synthetic curves for IRS
            curves = create_synthetic_curves(request.as_of, request.spec.currency.value)
            result = price_irs(request.spec, curves)
        elif isinstance(request.spec, CCSSpec):
            # Create synthetic curves for CCS
            curves = create_synthetic_ccs_curves(request.as_of)
            result = price_ccs(request.spec, curves)
        else:
            raise ValueError(f"Unsupported spec type: {type(request.spec)}")
        
        # Store result
        runs_db[run_id]["result"] = result
        
        return RunResponse(run_id=run_id, state="completed")
        
    except Exception as e:
        runs_db[run_id]["state"] = "failed"
        runs_db[run_id]["error"] = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process run: {str(e)}"
        )


@router.get("/{run_id}/result")
async def get_run_result(run_id: str) -> Union[PVBreakdown, CCSBreakdown]:
    """Get the result of a valuation run."""
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    run = runs_db[run_id]
    
    if run["state"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run {run_id} is not completed. State: {run['state']}"
        )
    
    if not run["result"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result for run {run_id} not found"
        )
    
    return run["result"]


def _validate_run_request(request: RunRequest) -> None:
    """Validate run request."""
    # Validate dates
    if request.spec.effective_date >= request.spec.maturity_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Effective date must be before maturity date"
        )
    
    # Validate based on spec type
    if isinstance(request.spec, IRSSpec):
        # Validate IRS-specific fields
        if request.spec.notional <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Notional must be positive"
            )
        
        if request.spec.fixed_rate is None or request.spec.fixed_rate < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fixed rate must be provided and non-negative"
            )
    
    elif isinstance(request.spec, CCSSpec):
        # Validate CCS-specific fields
        if request.spec.notional_leg1 <= 0 or request.spec.notional_leg2 <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both notionals must be positive"
            )
        
        if request.spec.currency_leg1 == request.spec.currency_leg2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leg currencies must be different for CCS"
            )
    
    # Validate market data profile
    if request.market_data_profile not in ["synthetic", "ecb", "fred"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid market data profile"
        )
