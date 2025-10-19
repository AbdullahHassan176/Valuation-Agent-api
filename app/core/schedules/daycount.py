"""
Day count conventions for interest calculations
"""
from datetime import date
from typing import Tuple
from enum import Enum

class DayCountConvention(Enum):
    ACT_360 = "ACT/360"
    ACT_365F = "ACT/365F"
    ACT_365L = "ACT/365L"
    THIRTY_360 = "30/360"
    THIRTY_E_360 = "30E/360"

def day_count_fraction(start_date: date, end_date: date, convention: DayCountConvention) -> float:
    """
    Calculate day count fraction between two dates
    
    Args:
        start_date: Start date (excluded)
        end_date: End date (included)
        convention: Day count convention
    
    Returns:
        Day count fraction as a float
    """
    if convention == DayCountConvention.ACT_360:
        return actual_360(start_date, end_date)
    elif convention == DayCountConvention.ACT_365F:
        return actual_365_fixed(start_date, end_date)
    elif convention == DayCountConvention.ACT_365L:
        return actual_365_leap(start_date, end_date)
    elif convention == DayCountConvention.THIRTY_360:
        return thirty_360(start_date, end_date)
    elif convention == DayCountConvention.THIRTY_E_360:
        return thirty_e_360(start_date, end_date)
    else:
        raise ValueError(f"Unsupported day count convention: {convention}")

def actual_360(start_date: date, end_date: date) -> float:
    """ACT/360: Actual days / 360"""
    actual_days = (end_date - start_date).days
    return actual_days / 360.0

def actual_365_fixed(start_date: date, end_date: date) -> float:
    """ACT/365F: Actual days / 365"""
    actual_days = (end_date - start_date).days
    return actual_days / 365.0

def actual_365_leap(start_date: date, end_date: date) -> float:
    """ACT/365L: Actual days / 365 (leap year aware)"""
    actual_days = (end_date - start_date).days
    
    # Count leap years in the period
    leap_days = 0
    current_year = start_date.year
    while current_year <= end_date.year:
        if is_leap_year(current_year):
            # Count days in this leap year that are in our period
            year_start = max(start_date, date(current_year, 1, 1))
            year_end = min(end_date, date(current_year, 12, 31))
            if year_start <= year_end:
                leap_days += 1
        current_year += 1
    
    return actual_days / (365.0 + leap_days)

def thirty_360(start_date: date, end_date: date) -> float:
    """30/360: 30 days per month, 360 days per year"""
    d1, m1, y1 = start_date.day, start_date.month, start_date.year
    d2, m2, y2 = end_date.day, end_date.month, end_date.year
    
    # 30/360 rules
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 == 30:
        d2 = 30
    
    days = (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)
    return days / 360.0

def thirty_e_360(start_date: date, end_date: date) -> float:
    """30E/360: European 30/360"""
    d1, m1, y1 = start_date.day, start_date.month, start_date.year
    d2, m2, y2 = end_date.day, end_date.month, end_date.year
    
    # 30E/360 rules
    if d1 == 31:
        d1 = 30
    if d2 == 31:
        d2 = 30
    
    days = (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)
    return days / 360.0

def is_leap_year(year: int) -> bool:
    """Check if a year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def parse_tenor(tenor: str) -> int:
    """
    Parse tenor string to get number of days (simplified)
    
    Args:
        tenor: Tenor string (e.g., "1M", "3M", "1Y")
        
    Returns:
        Approximate number of days
    """
    if tenor.endswith("M"):
        months = int(tenor[:-1])
        return months * 30  # Approximate
    elif tenor.endswith("Y"):
        years = int(tenor[:-1])
        return years * 365  # Approximate
    else:
        raise ValueError(f"Unsupported tenor format: {tenor}")

def parse_day_count_convention(convention_str: str) -> DayCountConvention:
    """Parse day count convention from string"""
    convention_map = {
        "ACT/360": DayCountConvention.ACT_360,
        "ACT/365F": DayCountConvention.ACT_365F,
        "ACT/365L": DayCountConvention.ACT_365L,
        "30/360": DayCountConvention.THIRTY_360,
        "30E/360": DayCountConvention.THIRTY_E_360,
    }
    
    if convention_str in convention_map:
        return convention_map[convention_str]
    else:
        raise ValueError(f"Unknown day count convention: {convention_str}")
