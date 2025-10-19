"""Market data types and schemas."""

from typing import List, Dict, Any, Optional
from datetime import date as Date
from pydantic import BaseModel, Field
from ..models import Currency


class RateData(BaseModel):
    """Market rate data."""
    
    tenor: str = Field(..., description="Tenor (e.g., '1M', '3M', '1Y')")
    rate: float = Field(..., description="Interest rate")
    date: Optional[Date] = None


class FXPointsData(BaseModel):
    """FX forward points data."""
    
    tenor: str = Field(..., description="Tenor (e.g., '1M', '3M', '1Y')")
    points: float = Field(..., description="Forward points")
    date: Optional[Date] = None


class FXSpotData(BaseModel):
    """FX spot rate data."""
    
    pair: str = Field(..., description="Currency pair (e.g., 'USD/EUR')")
    spot_rate: float = Field(..., description="Spot rate")
    date: Date = Field(..., description="Spot date")


class MarketDataRequest(BaseModel):
    """Request for market data."""
    
    as_of: Date = Field(..., description="As-of date")
    currency: Optional[Currency] = Field(None, description="Currency for rates")
    pair: Optional[str] = Field(None, description="Currency pair for FX")
    provider: str = Field("synthetic", description="Data provider")
    data_type: str = Field(..., description="Type of data (rates, fx_spot, fx_points)")


class MarketDataResponse(BaseModel):
    """Response from market data provider."""
    
    provider: str
    as_of: Date
    data_type: str
    data: List[Dict[str, Any]]
    count: int
    status: str = "success"
