from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import pandas as pd
import os
from ..core.curves.base import CurveBundle

router = APIRouter(prefix="/marketdata", tags=["marketdata"])

# Market data providers
PROVIDERS = {
    "public_ecb": "European Central Bank",
    "public_fred": "Federal Reserve Economic Data", 
    "public_boe": "Bank of England",
    "synthetic": "Synthetic Data"
}

@router.get("/providers")
async def get_providers():
    """Get available market data providers."""
    return {
        "providers": PROVIDERS,
        "default": "synthetic"
    }

@router.get("/curves/{provider}")
async def get_curves(provider: str, as_of: Optional[date] = None):
    """
    Get market curves from specified provider.
    
    Args:
        provider: Market data provider
        as_of: As-of date (defaults to today)
        
    Returns:
        Available curves and their data
    """
    if as_of is None:
        as_of = datetime.now().date()
    
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    try:
        if provider == "synthetic":
            curves = get_synthetic_curves(as_of)
        elif provider == "public_ecb":
            curves = get_ecb_curves(as_of)
        elif provider == "public_fred":
            curves = get_fred_curves(as_of)
        elif provider == "public_boe":
            curves = get_boe_curves(as_of)
        else:
            raise HTTPException(status_code=400, detail=f"Provider {provider} not implemented")
        
        return {
            "provider": provider,
            "as_of": as_of.isoformat(),
            "curves": curves,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching curves: {str(e)}")


def get_synthetic_curves(as_of: date) -> Dict[str, Any]:
    """Get synthetic market curves for testing."""
    # Load synthetic data from CSV files
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "samples")
    
    curves = {}
    
    # USD OIS curve
    usd_ois_file = os.path.join(data_dir, "usd_ois.csv")
    if os.path.exists(usd_ois_file):
        usd_ois = pd.read_csv(usd_ois_file)
        curves["USD_OIS"] = {
            "currency": "USD",
            "type": "OIS",
            "tenors": usd_ois["tenor"].tolist(),
            "rates": usd_ois["rate"].tolist(),
            "source": "synthetic"
        }
    
    # EUR OIS curve
    eur_ois_file = os.path.join(data_dir, "eur_ois.csv")
    if os.path.exists(eur_ois_file):
        eur_ois = pd.read_csv(eur_ois_file)
        curves["EUR_OIS"] = {
            "currency": "EUR", 
            "type": "OIS",
            "tenors": eur_ois["tenor"].tolist(),
            "rates": eur_ois["rate"].tolist(),
            "source": "synthetic"
        }
    
    # FX rates
    fx_file = os.path.join(data_dir, "fx_usd_eur.csv")
    if os.path.exists(fx_file):
        fx_data = pd.read_csv(fx_file)
        curves["USD_EUR_FX"] = {
            "currency_pair": "USD/EUR",
            "spot": fx_data["spot"].iloc[0] if "spot" in fx_data.columns else 0.85,
            "forward_points": fx_data["forward_points"].tolist() if "forward_points" in fx_data.columns else [],
            "source": "synthetic"
        }
    
    return curves


def get_ecb_curves(as_of: date) -> Dict[str, Any]:
    """Get curves from European Central Bank (placeholder)."""
    # In production, this would call ECB API
    return {
        "EUR_OIS": {
            "currency": "EUR",
            "type": "OIS", 
            "tenors": ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"],
            "rates": [0.035, 0.037, 0.040, 0.042, 0.045, 0.048, 0.050],
            "source": "ECB"
        }
    }


def get_fred_curves(as_of: date) -> Dict[str, Any]:
    """Get curves from Federal Reserve Economic Data (placeholder)."""
    # In production, this would call FRED API
    return {
        "USD_OIS": {
            "currency": "USD",
            "type": "OIS",
            "tenors": ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"],
            "rates": [0.045, 0.047, 0.050, 0.052, 0.055, 0.058, 0.060],
            "source": "FRED"
        }
    }


def get_boe_curves(as_of: date) -> Dict[str, Any]:
    """Get curves from Bank of England (placeholder)."""
    # In production, this would call BoE API
    return {
        "GBP_OIS": {
            "currency": "GBP",
            "type": "OIS",
            "tenors": ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"],
            "rates": [0.040, 0.042, 0.045, 0.047, 0.050, 0.053, 0.055],
            "source": "BoE"
        }
    }


@router.post("/curves/bootstrap")
async def bootstrap_curves(
    provider: str = "synthetic",
    as_of: Optional[date] = None,
    currencies: List[str] = ["USD", "EUR"]
):
    """
    Bootstrap curves from market data provider.
    
    Args:
        provider: Market data provider
        as_of: As-of date
        currencies: List of currencies to bootstrap
        
    Returns:
        CurveBundle with bootstrapped curves
    """
    if as_of is None:
        as_of = datetime.now().date()
    
    try:
        # Get market data
        market_data = await get_curves(provider, as_of)
        
        # Create curve bundle
        curve_bundle = CurveBundle(
            as_of_date=as_of,
            market_data_profile=provider,
            curves=market_data["curves"]
        )
        
        return {
            "status": "success",
            "curve_bundle": curve_bundle,
            "curves_count": len(market_data["curves"]),
            "currencies": currencies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error bootstrapping curves: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for market data service."""
    return {
        "status": "healthy",
        "providers": list(PROVIDERS.keys()),
        "timestamp": datetime.now().isoformat()
    }
