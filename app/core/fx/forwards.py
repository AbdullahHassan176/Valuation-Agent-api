"""
FX forward curve construction from spot rates and forward points
"""
from typing import Dict, List, Optional
from datetime import date, timedelta
from dataclasses import dataclass
import pandas as pd

from ..curves.base import CurvePoint, CurveRef, CurveType
from ..schedules.daycount import parse_tenor

@dataclass
class FXQuote:
    """FX quote data"""
    currency_pair: str
    tenor: str
    spot_rate: float
    forward_points: float
    forward_rate: float

@dataclass
class FXForwardCurve:
    """FX forward curve"""
    currency_pair: str
    spot_rate: float
    forward_points: List[CurvePoint]
    as_of_date: date

def load_fx_quotes(file_path: str) -> List[FXQuote]:
    """
    Load FX quotes from CSV file
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of FX quotes
    """
    df = pd.read_csv(file_path)
    quotes = []
    
    for _, row in df.iterrows():
        quote = FXQuote(
            currency_pair=row['currency_pair'],
            tenor=row['tenor'],
            spot_rate=float(row['spot_rate']),
            forward_points=float(row['forward_points']),
            forward_rate=float(row['forward_rate'])
        )
        quotes.append(quote)
    
    return quotes

def build_fx_forward_curve(quotes: List[FXQuote], as_of_date: date) -> FXForwardCurve:
    """
    Build FX forward curve from quotes
    
    Args:
        quotes: List of FX quotes
        as_of_date: As of date for the curve
        
    Returns:
        FX forward curve
    """
    if not quotes:
        raise ValueError("No quotes provided")
    
    # Get spot rate (assume all quotes are for the same pair)
    spot_rate = quotes[0].spot_rate
    currency_pair = quotes[0].currency_pair
    
    # Build forward points
    forward_points = []
    
    for quote in quotes:
        if quote.tenor == "SPOT":
            continue  # Skip spot, we already have it
        
        # Parse tenor to get maturity date
        try:
            maturity_date = parse_tenor_to_date(quote.tenor, as_of_date)
        except ValueError:
            continue  # Skip invalid tenors
        
        # Create curve point
        point = CurvePoint(
            date=maturity_date,
            rate=quote.forward_rate,
            discount_factor=1.0,  # Placeholder - should be calculated from rate
            tenor=quote.tenor
        )
        forward_points.append(point)
    
    # Sort by date
    forward_points.sort(key=lambda x: x.date)
    
    return FXForwardCurve(
        currency_pair=currency_pair,
        spot_rate=spot_rate,
        forward_points=forward_points,
        as_of_date=as_of_date
    )

def parse_tenor_to_date(tenor: str, as_of_date: date) -> date:
    """
    Parse tenor string to maturity date
    
    Args:
        tenor: Tenor string (e.g., "1M", "3M", "1Y")
        as_of_date: As of date
        
    Returns:
        Maturity date
    """
    if tenor == "SPOT":
        return as_of_date
    
    # Parse tenor
    if tenor.endswith("M"):
        months = int(tenor[:-1])
        # Simple month addition (doesn't handle month-end properly)
        year = as_of_date.year
        month = as_of_date.month + months
        while month > 12:
            month -= 12
            year += 1
        return date(year, month, as_of_date.day)
    elif tenor.endswith("Y"):
        years = int(tenor[:-1])
        return date(as_of_date.year + years, as_of_date.month, as_of_date.day)
    else:
        raise ValueError(f"Unsupported tenor format: {tenor}")

def get_fx_forward_rate(curve: FXForwardCurve, target_date: date) -> float:
    """
    Get FX forward rate for a specific date using linear interpolation
    
    Args:
        curve: FX forward curve
        target_date: Target date
        
    Returns:
        FX forward rate
    """
    if not curve.forward_points:
        return curve.spot_rate
    
    # If target date is before first point, return spot
    if target_date <= curve.as_of_date:
        return curve.spot_rate
    
    # If target date is after last point, return last forward rate
    if target_date >= curve.forward_points[-1].date:
        return curve.forward_points[-1].rate
    
    # Find surrounding points for interpolation
    for i in range(len(curve.forward_points) - 1):
        point1 = curve.forward_points[i]
        point2 = curve.forward_points[i + 1]
        
        if point1.date <= target_date <= point2.date:
            # Linear interpolation
            days_between = (point2.date - point1.date).days
            days_to_target = (target_date - point1.date).days
            
            if days_between == 0:
                return point1.rate
            
            weight = days_to_target / days_between
            interpolated_rate = point1.rate + weight * (point2.rate - point1.rate)
            return interpolated_rate
    
    # Fallback to spot rate
    return curve.spot_rate

def get_fx_spot_rate(curve: FXForwardCurve) -> float:
    """
    Get FX spot rate
    
    Args:
        curve: FX forward curve
        
    Returns:
        FX spot rate
    """
    return curve.spot_rate

def create_usd_eur_fx_curve(as_of_date: date) -> FXForwardCurve:
    """
    Create USD/EUR FX forward curve from sample data
    
    Args:
        as_of_date: As of date
        
    Returns:
        USD/EUR FX forward curve
    """
    # Load quotes from sample data
    quotes = load_fx_quotes("app/data/samples/fx_quotes.csv")
    
    # Filter for USD/EUR
    usd_eur_quotes = [q for q in quotes if q.currency_pair == "USD/EUR"]
    
    if not usd_eur_quotes:
        raise ValueError("No USD/EUR quotes found")
    
    return build_fx_forward_curve(usd_eur_quotes, as_of_date)

