from typing import List, Dict
from datetime import date, timedelta
from dataclasses import dataclass

from .ois import CurveRef, get_discount_factor

@dataclass
class RatePoint:
    """A forward rate point"""
    start_date: date
    end_date: date
    forward_rate: float
    day_count: float
    discount_factor_start: float
    discount_factor_end: float

def project_forwards(index: str, discount_curve: CurveRef, schedule: List[date]) -> List[RatePoint]:
    """
    Project forward rates from discount curve and payment schedule
    
    Args:
        index: Rate index (e.g., "USD-LIBOR-3M", "SOFR")
        discount_curve: Discount curve reference
        schedule: List of payment dates
        
    Returns:
        List of forward rate points
    """
    rate_points = []
    
    for i in range(len(schedule) - 1):
        start_date = schedule[i]
        end_date = schedule[i + 1]
        
        # Get discount factors
        df_start = get_discount_factor(discount_curve, start_date)
        df_end = get_discount_factor(discount_curve, end_date)
        
        # Calculate day count (simple ACT/360 for now)
        day_count = (end_date - start_date).days / 360.0
        
        # Calculate forward rate using discount factors
        # Forward rate = (DF_start / DF_end - 1) / day_count
        if day_count > 0 and df_end > 0:
            forward_rate = (df_start / df_end - 1.0) / day_count
        else:
            forward_rate = 0.0
        
        rate_point = RatePoint(
            start_date=start_date,
            end_date=end_date,
            forward_rate=forward_rate,
            day_count=day_count,
            discount_factor_start=df_start,
            discount_factor_end=df_end
        )
        rate_points.append(rate_point)
    
    return rate_points

def project_flat_forwards(index: str, discount_curve: CurveRef, schedule: List[date], par_rate: float) -> List[RatePoint]:
    """
    Project flat forward rates (placeholder implementation)
    
    Args:
        index: Rate index
        discount_curve: Discount curve reference
        schedule: List of payment dates
        par_rate: Par rate for the period
        
    Returns:
        List of forward rate points with flat rates
    """
    rate_points = []
    
    for i in range(len(schedule) - 1):
        start_date = schedule[i]
        end_date = schedule[i + 1]
        
        # Get discount factors
        df_start = get_discount_factor(discount_curve, start_date)
        df_end = get_discount_factor(discount_curve, end_date)
        
        # Calculate day count
        day_count = (end_date - start_date).days / 360.0
        
        # Use par rate as forward rate (placeholder)
        forward_rate = par_rate
        
        rate_point = RatePoint(
            start_date=start_date,
            end_date=end_date,
            forward_rate=forward_rate,
            day_count=day_count,
            discount_factor_start=df_start,
            discount_factor_end=df_end
        )
        rate_points.append(rate_point)
    
    return rate_points

def create_simple_schedule(effective_date: date, maturity_date: date, frequency: str = "Q") -> List[date]:
    """
    Create a simple payment schedule
    
    Args:
        effective_date: Effective date
        maturity_date: Maturity date
        frequency: Payment frequency (Q = quarterly)
        
    Returns:
        List of payment dates
    """
    schedule = [effective_date]
    
    if frequency == "Q":
        # Quarterly payments
        current_date = effective_date
        while current_date < maturity_date:
            # Add 3 months (90 days for simplicity)
            current_date = current_date + timedelta(days=90)
            if current_date < maturity_date:
                schedule.append(current_date)
    
    schedule.append(maturity_date)
    return schedule
