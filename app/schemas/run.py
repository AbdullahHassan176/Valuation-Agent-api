from typing import Union, List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_serializer
from datetime import date, datetime
from enum import Enum
from .instrument import IRSSpec, CCSSpec


class CSAConfig(BaseModel):
    """Credit Support Annex configuration."""
    threshold: float = Field(0.0, description="Threshold amount")
    minimum_transfer_amount: float = Field(0.0, description="Minimum transfer amount")
    rounding: float = Field(0.0, description="Rounding amount")
    collateral_currency: str = Field("USD", description="Collateral currency")
    interest_rate: float = Field(0.0, description="Interest rate on posted collateral")
    posting_frequency: str = Field("daily", description="Posting frequency")


class CreditCurveConfig(BaseModel):
    """Credit curve configuration."""
    name: str = Field(..., description="Curve name")
    currency: str = Field(..., description="Currency")
    tenors: List[str] = Field(..., description="Tenor points")
    spreads: List[float] = Field(..., description="Credit spreads in basis points")
    recovery_rate: float = Field(0.4, description="Recovery rate")


class XVAConfig(BaseModel):
    """XVA calculation configuration."""
    compute_cva: bool = Field(True, description="Compute CVA")
    compute_dva: bool = Field(True, description="Compute DVA")
    compute_fva: bool = Field(True, description="Compute FVA")
    counterparty_credit_curve: Optional[CreditCurveConfig] = Field(None, description="Counterparty credit curve")
    own_credit_curve: Optional[CreditCurveConfig] = Field(None, description="Own credit curve")
    funding_curve: Optional[CreditCurveConfig] = Field(None, description="Funding curve")
    csa_config: Optional[CSAConfig] = Field(None, description="CSA configuration")

class RunStatusEnum(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_REVIEW = "needs_review"

class RunRequest(BaseModel):
    """Request to run a valuation"""
    spec: Union[IRSSpec, CCSSpec] = Field(..., description="Instrument specification")
    asOf: date = Field(..., description="Valuation date")
    marketDataProfile: str = Field(..., description="Market data profile identifier")
    approach: List[str] = Field(..., description="List of valuation approaches to use")
    xva_config: Optional[XVAConfig] = Field(None, description="XVA calculation configuration")
    
    @field_serializer('asOf')
    def serialize_as_of(self, value: date) -> str:
        return value.isoformat()

class RunStatus(BaseModel):
    """Status of a valuation run"""
    id: str = Field(..., description="Unique run identifier")
    status: RunStatusEnum = Field(..., description="Current status of the run")
    created_at: datetime = Field(..., description="When the run was created")
    updated_at: datetime = Field(..., description="When the run was last updated")
    request: RunRequest = Field(..., description="Original run request")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    ifrs13_assessment: Optional[Dict[str, Any]] = Field(None, description="IFRS-13 compliance assessment")

class XVABreakdown(BaseModel):
    """XVA breakdown"""
    cva: float = Field(0.0, description="Credit Value Adjustment")
    dva: float = Field(0.0, description="Debit Value Adjustment")
    fva: float = Field(0.0, description="Funding Value Adjustment")
    total_xva: float = Field(0.0, description="Total XVA")
    currency: str = Field("USD", description="Currency")
    details: Dict[str, Any] = Field(default_factory=dict, description="XVA calculation details")


class PVBreakdown(BaseModel):
    """Present Value breakdown with lineage information"""
    run_id: str = Field(..., description="Run identifier")
    total_pv: float = Field(..., description="Total present value")
    components: Dict[str, float] = Field(..., description="PV components breakdown")
    market_data_hash: str = Field(..., description="Hash of market data used")
    model_hash: str = Field(..., description="Hash of model/parameters used")
    calculated_at: datetime = Field(..., description="When the calculation was performed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    xva: Optional[XVABreakdown] = Field(None, description="XVA breakdown if calculated")
