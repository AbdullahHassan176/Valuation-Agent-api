from typing import Dict
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
import uuid

from ..schemas.run import RunRequest, RunStatus, PVBreakdown, RunStatus as RunStatusEnum
from ..schemas.instrument import IRSSpec, CCSSpec

router = APIRouter(prefix="/runs", tags=["runs"])

# In-memory storage for demo purposes
runs_db: Dict[str, RunStatus] = {}
results_db: Dict[str, PVBreakdown] = {}

@router.post("/", response_model=RunStatus, status_code=status.HTTP_201_CREATED)
async def create_run(request: RunRequest) -> RunStatus:
    """Create a new valuation run"""
    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    run_status = RunStatus(
        id=run_id,
        status=RunStatusEnum.QUEUED,
        created_at=now,
        updated_at=now,
        request=request,
        error_message=None
    )
    
    runs_db[run_id] = run_status
    
    return run_status

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
    
    # Return dummy result with zeros for now
    if run_id not in results_db:
        # Create a dummy result
        dummy_result = PVBreakdown(
            run_id=run_id,
            total_pv=0.0,
            components={
                "fixed_leg": 0.0,
                "floating_leg": 0.0,
                "net_pv": 0.0
            },
            market_data_hash="dummy_market_data_hash",
            model_hash="dummy_model_hash",
            calculated_at=datetime.utcnow(),
            metadata={
                "approach": "dummy_approach",
                "version": "1.0.0"
            }
        )
        results_db[run_id] = dummy_result
    
    return results_db[run_id]
