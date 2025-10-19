"""
Hull-White 1-Factor Model Implementation

This module provides the Hull-White 1-factor model for interest rate modeling
with calibration capabilities for variance matching.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import date, datetime


@dataclass
class HW1FParams:
    """Hull-White 1-Factor model parameters"""
    a: float  # Mean reversion speed
    sigma: float  # Volatility parameter
    model_version: str = "HW1F:variance-matching:v0"
    calibrated_at: Optional[datetime] = None
    calibration_method: str = "variance_matching"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameters to dictionary for serialization"""
        return {
            "a": self.a,
            "sigma": self.sigma,
            "model_version": self.model_version,
            "calibrated_at": self.calibrated_at.isoformat() if self.calibrated_at else None,
            "calibration_method": self.calibration_method
        }


@dataclass
class VolatilitySurface:
    """Volatility surface data for calibration"""
    tenors: List[str]  # e.g., ["1Y", "2Y", "5Y", "10Y"]
    strikes: List[float]  # Strike rates
    volatilities: List[List[float]]  # Volatility matrix [tenor][strike]
    surface_type: str = "swaption"  # or "cap_floor"
    
    def get_volatility(self, tenor: str, strike: float) -> float:
        """Get volatility for specific tenor and strike"""
        try:
            tenor_idx = self.tenors.index(tenor)
            # Find closest strike
            strike_idx = min(range(len(self.strikes)), 
                              key=lambda i: abs(self.strikes[i] - strike))
            return self.volatilities[tenor_idx][strike_idx]
        except (ValueError, IndexError):
            return 0.0  # Default to 0 if not found


@dataclass
class CurveData:
    """Interest rate curve data for calibration"""
    tenors: List[str]
    rates: List[float]
    curve_type: str = "discount"  # or "forward"


def calibrate_hw1f_variance_matching(
    surface: VolatilitySurface,
    curves: List[CurveData],
    target_tenors: Optional[List[str]] = None
) -> HW1FParams:
    """
    Calibrate Hull-White 1-Factor model using variance matching approach.
    
    This is a stub implementation that returns fixed demo values.
    In a full implementation, this would:
    1. Extract market volatilities from the surface
    2. Calculate theoretical HW1F volatilities
    3. Minimize the difference between market and model volatilities
    4. Return calibrated parameters (a, sigma)
    
    Args:
        surface: Volatility surface data (swaption/cap-floor)
        curves: List of interest rate curves
        target_tenors: Specific tenors to calibrate against (optional)
        
    Returns:
        HW1FParams: Calibrated model parameters
    """
    # Stub implementation - return fixed demo values
    # In production, this would perform actual calibration
    
    # Demo parameters (typical values for USD market)
    a = 0.05  # Mean reversion speed (5% per year)
    sigma = 0.01  # Volatility (1% per year)
    
    # Create parameters object
    params = HW1FParams(
        a=a,
        sigma=sigma,
        model_version="HW1F:variance-matching:v0",
        calibrated_at=datetime.utcnow(),
        calibration_method="variance_matching"
    )
    
    return params


def validate_hw1f_params(params: HW1FParams) -> List[str]:
    """
    Validate Hull-White 1-Factor model parameters
    
    Args:
        params: HW1F parameters to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check mean reversion speed
    if params.a <= 0:
        errors.append("Mean reversion speed 'a' must be positive")
    elif params.a > 1.0:
        errors.append("Mean reversion speed 'a' seems unusually high (>100%)")
    
    # Check volatility
    if params.sigma <= 0:
        errors.append("Volatility 'sigma' must be positive")
    elif params.sigma > 0.5:
        errors.append("Volatility 'sigma' seems unusually high (>50%)")
    
    # Check model version format
    if not params.model_version.startswith("HW1F:"):
        errors.append("Model version must start with 'HW1F:'")
    
    return errors


def get_hw1f_model_info() -> Dict[str, Any]:
    """
    Get information about the Hull-White 1-Factor model
    
    Returns:
        Dictionary with model information
    """
    return {
        "model_name": "Hull-White 1-Factor",
        "model_type": "short_rate_model",
        "parameters": ["a (mean reversion)", "sigma (volatility)"],
        "calibration_methods": ["variance_matching", "maximum_likelihood", "least_squares"],
        "supported_instruments": ["swaptions", "caps", "floors", "bonds"],
        "version": "v0",
        "description": "Single-factor short rate model with mean reversion"
    }


def create_demo_volatility_surface() -> VolatilitySurface:
    """
    Create a demo volatility surface for testing
    
    Returns:
        VolatilitySurface: Demo surface with typical market data
    """
    tenors = ["1Y", "2Y", "5Y", "10Y", "20Y"]
    strikes = [0.02, 0.03, 0.04, 0.05, 0.06]  # 2% to 6%
    
    # Demo volatility matrix (ATM volatilities)
    volatilities = [
        [0.15, 0.14, 0.13, 0.12, 0.11],  # 1Y
        [0.14, 0.13, 0.12, 0.11, 0.10],  # 2Y
        [0.13, 0.12, 0.11, 0.10, 0.09],  # 5Y
        [0.12, 0.11, 0.10, 0.09, 0.08],  # 10Y
        [0.11, 0.10, 0.09, 0.08, 0.07],  # 20Y
    ]
    
    return VolatilitySurface(
        tenors=tenors,
        strikes=strikes,
        volatilities=volatilities,
        surface_type="swaption"
    )


def create_demo_curves() -> List[CurveData]:
    """
    Create demo interest rate curves for testing
    
    Returns:
        List[CurveData]: Demo curves
    """
    tenors = ["1Y", "2Y", "5Y", "10Y", "20Y", "30Y"]
    rates = [0.05, 0.052, 0.055, 0.058, 0.060, 0.062]  # Upward sloping curve
    
    return [
        CurveData(
            tenors=tenors,
            rates=rates,
            curve_type="discount"
        )
    ]

