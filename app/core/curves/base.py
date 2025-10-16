from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import date
from enum import Enum

class CurveType(str, Enum):
    DISCOUNT = "discount"
    FORWARD = "forward"
    BASIS = "basis"
    FX = "fx"

@dataclass
class CurvePoint:
    """Single point on a curve"""
    date: date
    rate: float
    discount_factor: float
    tenor: Optional[str] = None

@dataclass
class CurveRef:
    """Reference to a curve with metadata"""
    curve_id: str
    curve_type: CurveType
    currency: str
    index: Optional[str] = None
    tenor: Optional[str] = None
    source: str = "market"
    as_of_date: Optional[date] = None
    
    def __str__(self) -> str:
        return f"{self.curve_type.value}_{self.currency}_{self.index or 'base'}_{self.tenor or 'spot'}"

@dataclass
class CurveBundle:
    """Bundle of curves for pricing"""
    curves: Dict[str, List[CurvePoint]]
    curve_refs: Dict[str, CurveRef]
    as_of_date: date
    market_data_profile: str
    
    def get_curve(self, curve_id: str) -> Optional[List[CurvePoint]]:
        """Get curve by ID"""
        return self.curves.get(curve_id)
    
    def get_curve_ref(self, curve_id: str) -> Optional[CurveRef]:
        """Get curve reference by ID"""
        return self.curve_refs.get(curve_id)
    
    def add_curve(self, curve_ref: CurveRef, points: List[CurvePoint]) -> None:
        """Add a curve to the bundle"""
        self.curves[curve_ref.curve_id] = points
        self.curve_refs[curve_ref.curve_id] = curve_ref

def bootstrap_curves(market_data_profile: str, as_of_date: date) -> CurveBundle:
    """
    Bootstrap curves from market data (placeholder implementation)
    
    In a real implementation, this would:
    1. Load market data from database/external source
    2. Bootstrap discount curves from deposit, futures, swap rates
    3. Build forward curves from discount curves
    4. Handle basis curves for different indices
    5. Build FX curves for cross-currency swaps
    
    Args:
        market_data_profile: Profile identifier for market data
        as_of_date: Valuation date
        
    Returns:
        CurveBundle with bootstrapped curves
    """
    # Placeholder implementation - return dummy curves
    bundle = CurveBundle(
        curves={},
        curve_refs={},
        as_of_date=as_of_date,
        market_data_profile=market_data_profile
    )
    
    # Add dummy discount curve
    discount_ref = CurveRef(
        curve_id="USD_DISCOUNT",
        curve_type=CurveType.DISCOUNT,
        currency="USD",
        source="bootstrap",
        as_of_date=as_of_date
    )
    
    dummy_points = [
        CurvePoint(date=as_of_date, rate=0.0, discount_factor=1.0, tenor="ON"),
        CurvePoint(date=as_of_date, rate=0.05, discount_factor=0.95, tenor="1Y"),
        CurvePoint(date=as_of_date, rate=0.06, discount_factor=0.90, tenor="2Y"),
        CurvePoint(date=as_of_date, rate=0.07, discount_factor=0.85, tenor="5Y"),
    ]
    
    bundle.add_curve(discount_ref, dummy_points)
    
    # Add dummy forward curve
    forward_ref = CurveRef(
        curve_id="USD_LIBOR_3M",
        curve_type=CurveType.FORWARD,
        currency="USD",
        index="USD-LIBOR-3M",
        source="bootstrap",
        as_of_date=as_of_date
    )
    
    forward_points = [
        CurvePoint(date=as_of_date, rate=0.05, discount_factor=1.0, tenor="3M"),
        CurvePoint(date=as_of_date, rate=0.055, discount_factor=0.95, tenor="6M"),
        CurvePoint(date=as_of_date, rate=0.06, discount_factor=0.90, tenor="1Y"),
    ]
    
    bundle.add_curve(forward_ref, forward_points)
    
    return bundle

def interpolate_curve(points: List[CurvePoint], target_date: date) -> float:
    """
    Interpolate curve at target date (placeholder implementation)
    
    In a real implementation, this would use proper interpolation methods
    like linear, cubic spline, or log-linear interpolation.
    
    Args:
        points: Curve points
        target_date: Date to interpolate at
        
    Returns:
        Interpolated rate
    """
    # Simple linear interpolation placeholder
    if not points:
        return 0.0
    
    # Find surrounding points
    before_point = None
    after_point = None
    
    for point in points:
        if point.date <= target_date:
            before_point = point
        elif point.date > target_date and after_point is None:
            after_point = point
            break
    
    if before_point is None:
        return points[0].rate
    if after_point is None:
        return points[-1].rate
    
    # Linear interpolation
    days_before = (target_date - before_point.date).days
    days_after = (after_point.date - target_date).days
    total_days = (after_point.date - before_point.date).days
    
    if total_days == 0:
        return before_point.rate
    
    weight = days_after / total_days
    return before_point.rate * weight + after_point.rate * (1 - weight)
