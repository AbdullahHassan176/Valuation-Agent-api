from typing import Union, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum
from .instrument import IRSSpec, CCSSpec

class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RunRequest(BaseModel):
    """Request to run a valuation"""
    spec: Union[IRSSpec, CCSSpec] = Field(..., description="Instrument specification")
    asOf: date = Field(..., description="Valuation date")
    marketDataProfile: str = Field(..., description="Market data profile identifier")
    approach: List[str] = Field(..., description="List of valuation approaches to use")

class RunStatus(BaseModel):
    """Status of a valuation run"""
    id: str = Field(..., description="Unique run identifier")
    status: RunStatus = Field(..., description="Current status of the run")
    created_at: datetime = Field(..., description="When the run was created")
    updated_at: datetime = Field(..., description="When the run was last updated")
    request: RunRequest = Field(..., description="Original run request")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class PVBreakdown(BaseModel):
    """Present Value breakdown with lineage information"""
    run_id: str = Field(..., description="Run identifier")
    total_pv: float = Field(..., description="Total present value")
    components: Dict[str, float] = Field(..., description="PV components breakdown")
    market_data_hash: str = Field(..., description="Hash of market data used")
    model_hash: str = Field(..., description="Hash of model/parameters used")
    calculated_at: datetime = Field(..., description="When the calculation was performed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
