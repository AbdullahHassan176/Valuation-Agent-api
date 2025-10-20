"""Day count convention calculations."""

from typing import Union
from datetime import date
from enum import Enum

from .models import DayCountConvention


def accrual_factor(
    start_date: date,
    end_date: date,
    day_count_convention: DayCountConvention
) -> float:
    """Calculate accrual factor between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        day_count_convention: Day count convention
        
    Returns:
        Accrual factor as a decimal
    """
    try:
        if day_count_convention == DayCountConvention.ACT_360:
            return _act_360(start_date, end_date)
        elif day_count_convention == DayCountConvention.ACT_365:
            return _act_365(start_date, end_date)
        elif day_count_convention == DayCountConvention.ACT_365F:
            return _act_365f(start_date, end_date)
        elif day_count_convention == DayCountConvention.THIRTY_360:
            return _thirty_360(start_date, end_date)
        elif day_count_convention == DayCountConvention.ACT_ACT:
            return _act_act(start_date, end_date)
        else:
            raise ValueError(f"Unsupported day count convention: {day_count_convention}")
            
    except Exception as e:
        raise ValueError(f"Error calculating accrual factor: {str(e)}")


def _act_360(start_date: date, end_date: date) -> float:
    """Actual/360 day count convention.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Accrual factor
    """
    days = (end_date - start_date).days
    return days / 360.0


def _act_365(start_date: date, end_date: date) -> float:
    """Actual/365 day count convention.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Accrual factor
    """
    days = (end_date - start_date).days
    return days / 365.0


def _act_365f(start_date: date, end_date: date) -> float:
    """Actual/365 Fixed day count convention.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Accrual factor
    """
    days = (end_date - start_date).days
    return days / 365.0


def _thirty_360(start_date: date, end_date: date) -> float:
    """30/360 day count convention.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Accrual factor
    """
    # 30/360 US convention
    d1, m1, y1 = start_date.day, start_date.month, start_date.year
    d2, m2, y2 = end_date.day, end_date.month, end_date.year
    
    # Adjust for end-of-month
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 == 30:
        d2 = 30
    
    # Calculate days
    days = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)
    return days / 360.0


def _act_act(start_date: date, end_date: date) -> float:
    """Actual/Actual day count convention.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Accrual factor
    """
    # Simple Actual/Actual implementation
    # In real implementation, would handle leap years properly
    days = (end_date - start_date).days
    
    # Check if period spans a leap year
    start_year = start_date.year
    end_year = end_date.year
    
    if start_year == end_year:
        # Same year
        if _is_leap_year(start_year):
            return days / 366.0
        else:
            return days / 365.0
    else:
        # Different years - use average
        return days / 365.25


def _is_leap_year(year: int) -> bool:
    """Check if a year is a leap year.
    
    Args:
        year: Year to check
        
    Returns:
        True if leap year, False otherwise
    """
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def year_fraction(
    start_date: date,
    end_date: date,
    day_count_convention: DayCountConvention
) -> float:
    """Calculate year fraction between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        day_count_convention: Day count convention
        
    Returns:
        Year fraction as a decimal
    """
    return accrual_factor(start_date, end_date, day_count_convention)


def days_between(start_date: date, end_date: date) -> int:
    """Calculate actual days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Number of days
    """
    return (end_date - start_date).days


def is_end_of_month(dt: date) -> bool:
    """Check if a date is the end of the month.
    
    Args:
        dt: Date to check
        
    Returns:
        True if end of month, False otherwise
    """
    # Get next day
    from datetime import timedelta
    next_day = dt + timedelta(days=1)
    
    # If next day is in a different month, current day is end of month
    return next_day.month != dt.month


def get_month_end(dt: date) -> date:
    """Get the end of the month for a given date.
    
    Args:
        dt: Input date
        
    Returns:
        End of month date
    """
    # Get first day of next month
    if dt.month == 12:
        next_month = date(dt.year + 1, 1, 1)
    else:
        next_month = date(dt.year, dt.month + 1, 1)
    
    # Subtract one day to get end of current month
    from datetime import timedelta
    return next_month - timedelta(days=1)



