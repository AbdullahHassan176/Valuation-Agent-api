"""
Calendar and business day conventions for schedule generation
"""
from datetime import date, timedelta
from typing import List, Set
from enum import Enum

class BusinessDayConvention(Enum):
    FOLLOWING = "FOLLOWING"
    MODIFIED_FOLLOWING = "MODIFIED_FOLLOWING"
    PRECEDING = "PRECEDING"
    MODIFIED_PRECEDING = "MODIFIED_PRECEDING"
    UNADJUSTED = "UNADJUSTED"

class Calendar:
    """Business calendar for holiday handling"""
    
    def __init__(self, name: str, holidays: Set[date] = None):
        self.name = name
        self.holidays = holidays or set()
    
    def is_business_day(self, d: date) -> bool:
        """Check if a date is a business day (not weekend or holiday)"""
        # Weekend check (Saturday=5, Sunday=6)
        if d.weekday() >= 5:
            return False
        # Holiday check
        return d not in self.holidays
    
    def adjust(self, d: date, convention: BusinessDayConvention) -> date:
        """Adjust a date according to business day convention"""
        if convention == BusinessDayConvention.UNADJUSTED:
            return d
        
        if self.is_business_day(d):
            return d
        
        if convention == BusinessDayConvention.FOLLOWING:
            return self.next_business_day(d)
        elif convention == BusinessDayConvention.PRECEDING:
            return self.previous_business_day(d)
        elif convention == BusinessDayConvention.MODIFIED_FOLLOWING:
            next_bd = self.next_business_day(d)
            # If next business day is in different month, go to previous
            if next_bd.month != d.month:
                return self.previous_business_day(d)
            return next_bd
        elif convention == BusinessDayConvention.MODIFIED_PRECEDING:
            prev_bd = self.previous_business_day(d)
            # If previous business day is in different month, go to next
            if prev_bd.month != d.month:
                return self.next_business_day(d)
            return prev_bd
        
        return d
    
    def next_business_day(self, d: date) -> date:
        """Find the next business day"""
        current = d + timedelta(days=1)
        while not self.is_business_day(current):
            current += timedelta(days=1)
        return current
    
    def previous_business_day(self, d: date) -> date:
        """Find the previous business day"""
        current = d - timedelta(days=1)
        while not self.is_business_day(current):
            current -= timedelta(days=1)
        return current

# Standard calendars
USD_CALENDAR = Calendar("USD", {
    # Add common US holidays
    date(2024, 1, 1),   # New Year's Day
    date(2024, 7, 4),   # Independence Day
    date(2024, 12, 25), # Christmas Day
    # Add more holidays as needed
})

EUR_CALENDAR = Calendar("EUR", {
    # Add common European holidays
    date(2024, 1, 1),   # New Year's Day
    date(2024, 4, 1),   # Easter Monday (approximate)
    date(2024, 5, 1),   # Labour Day
    date(2024, 12, 25), # Christmas Day
    date(2024, 12, 26), # Boxing Day
    # Add more holidays as needed
})

USD_EUR_CALENDAR = Calendar("USD_EUR", {
    # Combined USD and EUR holidays
    date(2024, 1, 1),   # New Year's Day
    date(2024, 4, 1),   # Easter Monday (approximate)
    date(2024, 5, 1),   # Labour Day
    date(2024, 7, 4),   # Independence Day (US)
    date(2024, 12, 25), # Christmas Day
    date(2024, 12, 26), # Boxing Day
    # Add more holidays as needed
})

def get_calendar(calendar_name: str) -> Calendar:
    """Get calendar by name"""
    calendar_name_upper = calendar_name.upper()
    if calendar_name_upper == "USD":
        return USD_CALENDAR
    elif calendar_name_upper == "EUR":
        return EUR_CALENDAR
    elif calendar_name_upper in ["USD_EUR", "USD/EUR"]:
        return USD_EUR_CALENDAR
    else:
        # Default to USD calendar
        return USD_CALENDAR
