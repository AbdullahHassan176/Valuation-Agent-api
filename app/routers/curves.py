from typing import Dict, List
from fastapi import APIRouter, HTTPException, status
from datetime import date
from pydantic import BaseModel

from ..core.curves.ois import bootstrap_usd_ois_curve
from ..data.catalog import catalog
from ..data.validation import DataValidator

router = APIRouter(prefix="/curves", tags=["curves"])

# In-memory storage for curves
curves_db: Dict[str, Dict] = {}

class BootstrapRequest(BaseModel):
    """Request to bootstrap a curve"""
    curve_type: str = "USD_OIS"
    as_of_date: date
    market_data_profile: str = "default"

class CurveNodeResponse(BaseModel):
    """Response for a curve node"""
    tenor: str
    maturity_date: date
    zero_rate: float
    discount_factor: float
    day_count: float

class CurveResponse(BaseModel):
    """Response for a bootstrapped curve"""
    curve_id: str
    curve_type: str
    currency: str
    index: str
    as_of_date: date
    nodes: List[CurveNodeResponse]
    version: int

@router.post("/bootstrap", response_model=CurveResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_curve(request: BootstrapRequest):
    """Bootstrap a curve from market data"""
    
    try:
        # Load and validate quotes
        if request.curve_type == "USD_OIS":
            quotes = catalog.get_usd_ois_quotes()
            expected_type = "OIS"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported curve type: {request.curve_type}"
            )
        
        # Validate quotes
        validator = DataValidator()
        validation_results = validator.validate_all(quotes, expected_type)
        
        if validator.has_errors(validation_results):
            error_messages = validator.get_error_messages(validation_results)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data validation failed: {'; '.join(error_messages)}"
            )
        
        # Bootstrap curve
        curve_ref = bootstrap_usd_ois_curve(request.as_of_date)
        
        # Convert to response format
        nodes = []
        if hasattr(curve_ref, 'curve_nodes'):
            for node in curve_ref.curve_nodes:
                node_response = CurveNodeResponse(
                    tenor=node.tenor,
                    maturity_date=node.maturity_date,
                    zero_rate=node.zero_rate,
                    discount_factor=node.discount_factor,
                    day_count=node.day_count
                )
                nodes.append(node_response)
        
        # Generate version number
        version = len(curves_db) + 1
        
        # Store curve
        curve_data = {
            "curve_id": curve_ref.curve_id,
            "curve_type": curve_ref.curve_type.value,
            "currency": curve_ref.currency,
            "index": curve_ref.index,
            "as_of_date": curve_ref.as_of_date,
            "nodes": nodes,
            "version": version,
            "raw_curve_ref": curve_ref
        }
        curves_db[curve_ref.curve_id] = curve_data
        
        return CurveResponse(
            curve_id=curve_ref.curve_id,
            curve_type=curve_ref.curve_type.value,
            currency=curve_ref.currency,
            index=curve_ref.index,
            as_of_date=curve_ref.as_of_date,
            nodes=nodes,
            version=version
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bootstrap curve: {str(e)}"
        )

@router.get("/{curve_id}", response_model=CurveResponse)
async def get_curve(curve_id: str):
    """Get a bootstrapped curve"""
    if curve_id not in curves_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Curve {curve_id} not found"
        )
    
    curve_data = curves_db[curve_id]
    return CurveResponse(
        curve_id=curve_data["curve_id"],
        curve_type=curve_data["curve_type"],
        currency=curve_data["currency"],
        index=curve_data["index"],
        as_of_date=curve_data["as_of_date"],
        nodes=curve_data["nodes"],
        version=curve_data["version"]
    )

@router.get("/", response_model=List[str])
async def list_curves():
    """List all available curves"""
    return list(curves_db.keys())
