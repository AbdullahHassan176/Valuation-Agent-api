"""Curve bootstrapping endpoints."""

from typing import Dict, Any, List
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.models import Currency
from app.core.curves.ois import bootstrap_ois_curve
from app.core.curves.fx import bootstrap_fx_forward_curve
from app.core.marketdata.adapters import get_data_provider

router = APIRouter()

# In-memory storage for curves (PoC)
curves_storage: Dict[str, Dict[str, Any]] = {}
fx_storage: Dict[str, Dict[str, Any]] = {}


class CurveBootstrapRequest(BaseModel):
    """Request model for curve bootstrapping."""
    
    as_of: date = Field(..., description="As-of date for the curve")
    currency: Currency = Field(..., description="Currency for the curve")
    provider: str = Field("synthetic", description="Data provider")


class FXBootstrapRequest(BaseModel):
    """Request model for FX forward bootstrapping."""
    
    as_of: date = Field(..., description="As-of date for the curve")
    pair: str = Field(..., description="Currency pair (e.g., 'USD/EUR')")
    provider: str = Field("synthetic", description="Data provider")


class CurveRef(BaseModel):
    """Curve reference response."""
    
    id: str
    as_of: date
    currency: str
    method: str
    nodes: List[Dict[str, Any]]
    node_count: int


class FxFwdRef(BaseModel):
    """FX forward reference response."""
    
    id: str
    as_of: date
    pair: str
    spot_rate: float
    method: str
    nodes: List[Dict[str, Any]]
    node_count: int


@router.post("/curves/bootstrap", response_model=CurveRef)
async def bootstrap_curve(request: CurveBootstrapRequest) -> CurveRef:
    """Bootstrap OIS discount curve.
    
    Args:
        request: Curve bootstrap request
        
    Returns:
        Bootstrapped curve reference
        
    Raises:
        HTTPException: If bootstrapping fails
    """
    try:
        # Get data provider
        provider = get_data_provider(request.provider)
        
        # Get market data
        rates_data = provider.get_ois_rates(request.currency, request.as_of)
        
        if not rates_data:
            raise HTTPException(
                status_code=404,
                detail=f"No market data available for {request.currency.value} from {request.provider}"
            )
        
        # Bootstrap curve
        curve_data = bootstrap_ois_curve(request.currency, request.as_of, rates_data)
        
        # Generate curve ID
        curve_id = f"{request.currency.value}_{request.as_of.isoformat()}_{request.provider}"
        
        # Store curve
        curves_storage[curve_id] = curve_data
        
        # Return curve reference
        return CurveRef(
            id=curve_id,
            as_of=request.as_of,
            currency=request.currency.value,
            method=curve_data['method'],
            nodes=curve_data['nodes'],
            node_count=curve_data['node_count']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error bootstrapping curve: {str(e)}"
        )


@router.post("/fx/bootstrap", response_model=FxFwdRef)
async def bootstrap_fx_forward(request: FXBootstrapRequest) -> FxFwdRef:
    """Bootstrap FX forward curve.
    
    Args:
        request: FX bootstrap request
        
    Returns:
        Bootstrapped FX forward reference
        
    Raises:
        HTTPException: If bootstrapping fails
    """
    try:
        # Parse currency pair
        if '/' not in request.pair:
            raise HTTPException(
                status_code=400,
                detail="Invalid currency pair format. Use 'USD/EUR' format."
            )
        
        base_currency, quote_currency = request.pair.split('/')
        
        # Get data provider
        provider = get_data_provider(request.provider)
        
        # Get FX spot rate
        spot_data = provider.get_fx_spot(request.pair, request.as_of)
        spot_rate = spot_data['spot_rate']
        
        # Get FX forward points
        points_data = provider.get_fx_points(request.pair, request.as_of)
        
        if not points_data:
            raise HTTPException(
                status_code=404,
                detail=f"No FX data available for {request.pair} from {request.provider}"
            )
        
        # Bootstrap FX forward curve
        fx_data = bootstrap_fx_forward_curve(
            Currency(base_currency),
            Currency(quote_currency),
            request.as_of,
            spot_rate,
            points_data
        )
        
        # Generate FX ID
        fx_id = f"{request.pair}_{request.as_of.isoformat()}_{request.provider}"
        
        # Store FX curve
        fx_storage[fx_id] = fx_data
        
        # Return FX forward reference
        return FxFwdRef(
            id=fx_id,
            as_of=request.as_of,
            pair=request.pair,
            spot_rate=spot_rate,
            method=fx_data['method'],
            nodes=fx_data['nodes'],
            node_count=fx_data['node_count']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error bootstrapping FX forward curve: {str(e)}"
        )


@router.get("/curves/{curve_id}")
async def get_curve(curve_id: str) -> Dict[str, Any]:
    """Get stored curve by ID.
    
    Args:
        curve_id: Curve identifier
        
    Returns:
        Curve data
        
    Raises:
        HTTPException: If curve not found
    """
    if curve_id not in curves_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Curve {curve_id} not found"
        )
    
    return curves_storage[curve_id]


@router.get("/fx/{fx_id}")
async def get_fx_curve(fx_id: str) -> Dict[str, Any]:
    """Get stored FX curve by ID.
    
    Args:
        fx_id: FX curve identifier
        
    Returns:
        FX curve data
        
    Raises:
        HTTPException: If FX curve not found
    """
    if fx_id not in fx_storage:
        raise HTTPException(
            status_code=404,
            detail=f"FX curve {fx_id} not found"
        )
    
    return fx_storage[fx_id]


@router.get("/curves")
async def list_curves() -> Dict[str, Any]:
    """List all stored curves.
    
    Returns:
        List of stored curves
    """
    return {
        "curves": list(curves_storage.keys()),
        "fx_curves": list(fx_storage.keys()),
        "total_curves": len(curves_storage),
        "total_fx_curves": len(fx_storage)
    }