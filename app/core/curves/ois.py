import math
from typing import List, Dict, Tuple
from datetime import date, timedelta
from dataclasses import dataclass

from ..curves.base import CurveRef, CurvePoint, CurveType
from ...data.catalog import QuoteData, catalog

@dataclass
class CurveNode:
    """A node on the discount curve"""
    tenor: str
    maturity_date: date
    zero_rate: float
    discount_factor: float
    day_count: float

def parse_tenor(tenor: str, as_of_date: date) -> Tuple[date, float]:
    """
    Parse tenor string to maturity date and day count
    
    Args:
        tenor: Tenor string (e.g., "1M", "3M", "1Y")
        as_of_date: As of date for calculation
        
    Returns:
        Tuple of (maturity_date, day_count)
    """
    tenor = tenor.upper()
    
    if tenor == "ON":
        # Overnight - next business day
        maturity_date = as_of_date + timedelta(days=1)
        day_count = 1.0 / 365.0
    elif tenor.endswith("D"):
        days = int(tenor[:-1])
        maturity_date = as_of_date + timedelta(days=days)
        day_count = days / 365.0
    elif tenor.endswith("W"):
        weeks = int(tenor[:-1])
        maturity_date = as_of_date + timedelta(weeks=weeks)
        day_count = (weeks * 7) / 365.0
    elif tenor.endswith("M"):
        months = int(tenor[:-1])
        # Simple month addition (30 days per month)
        maturity_date = as_of_date + timedelta(days=months * 30)
        day_count = (months * 30) / 365.0
    elif tenor.endswith("Y"):
        years = int(tenor[:-1])
        # Simple year addition (365 days per year)
        maturity_date = as_of_date + timedelta(days=years * 365)
        day_count = years
    else:
        raise ValueError(f"Unsupported tenor format: {tenor}")
    
    return maturity_date, day_count

def bootstrap_discount_curve(as_of_date: date, quotes: List[QuoteData]) -> CurveRef:
    """
    Bootstrap discount curve from OIS quotes
    
    Args:
        as_of_date: As of date for the curve
        quotes: List of OIS quotes
        
    Returns:
        CurveRef with bootstrapped curve nodes
    """
    # Sort quotes by tenor (simple string sort for now)
    sorted_quotes = sorted(quotes, key=lambda q: q.tenor)
    
    curve_nodes = []
    
    for quote in sorted_quotes:
        try:
            maturity_date, day_count = parse_tenor(quote.tenor, as_of_date)
            
            # Simple discount factor calculation
            # DF = exp(-rate * time)
            discount_factor = math.exp(-quote.rate * day_count)
            
            node = CurveNode(
                tenor=quote.tenor,
                maturity_date=maturity_date,
                zero_rate=quote.rate,
                discount_factor=discount_factor,
                day_count=day_count
            )
            curve_nodes.append(node)
            
        except ValueError as e:
            print(f"Warning: Skipping invalid tenor {quote.tenor}: {e}")
            continue
    
    # Create curve points
    curve_points = []
    for node in curve_nodes:
        point = CurvePoint(
            date=node.maturity_date,
            rate=node.zero_rate,
            discount_factor=node.discount_factor,
            tenor=node.tenor
        )
        curve_points.append(point)
    
    # Create curve reference
    curve_ref = CurveRef(
        curve_id="USD_OIS_DISCOUNT",
        curve_type=CurveType.DISCOUNT,
        currency="USD",
        index="OIS",
        source="bootstrap",
        as_of_date=as_of_date
    )
    
    # Store curve nodes in metadata (for now)
    curve_ref.curve_nodes = curve_nodes
    curve_ref.curve_points = curve_points
    
    return curve_ref

def get_discount_factor(curve_ref: CurveRef, target_date: date) -> float:
    """
    Get discount factor for a target date using linear interpolation
    
    Args:
        curve_ref: Curve reference with nodes
        target_date: Target date
        
    Returns:
        Discount factor
    """
    if not hasattr(curve_ref, 'curve_points') or not curve_ref.curve_points:
        return 1.0
    
    points = curve_ref.curve_points
    
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
        return points[0].discount_factor
    if after_point is None:
        return points[-1].discount_factor
    
    # Linear interpolation on discount factors
    days_before = (target_date - before_point.date).days
    days_after = (after_point.date - target_date).days
    total_days = (after_point.date - before_point.date).days
    
    if total_days == 0:
        return before_point.discount_factor
    
    weight = days_after / total_days
    return before_point.discount_factor * weight + after_point.discount_factor * (1 - weight)

def bootstrap_usd_ois_curve(as_of_date: date) -> CurveRef:
    """
    Bootstrap USD OIS curve from sample data
    
    Args:
        as_of_date: As of date for the curve
        
    Returns:
        Bootstrapped USD OIS curve
    """
    quotes = catalog.get_usd_ois_quotes()
    return bootstrap_discount_curve(as_of_date, quotes)

