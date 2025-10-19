"""Schedule generation with QuantLib integration."""

from typing import List, Optional, Union
from datetime import date, datetime
from enum import Enum

# QuantLib imports (commented out for now since it's optional)
# import QuantLib as ql

from app.core.models import BusinessDayConvention, Calendar, Frequency
from .schedules.schedule_builder import ScheduleBuilder, create_schedule


class StubType(str, Enum):
    """Stub type for schedule generation."""
    NONE = "None"
    SHORT_FIRST = "ShortFirst"
    SHORT_LAST = "ShortLast"
    LONG_FIRST = "LongFirst"
    LONG_LAST = "LongLast"


def make_schedule(
    effective_date: date,
    maturity_date: date,
    frequency: Frequency,
    calendar: Calendar,
    business_day_convention: BusinessDayConvention,
    stub: Optional[StubType] = None
) -> List[date]:
    """Generate a schedule of dates.
    
    Args:
        effective_date: Effective date of the schedule
        maturity_date: Maturity date of the schedule
        frequency: Payment frequency
        calendar: Calendar for business day adjustments
        business_day_convention: Business day convention
        stub: Optional stub type
        
    Returns:
        List of schedule dates
    """
    try:
        # Use existing schedule builder
        builder = ScheduleBuilder()
        builder.effective_date = effective_date
        builder.termination_date = maturity_date
        builder.frequency = _convert_frequency(frequency)
        builder.calendar = _convert_calendar(calendar)
        builder.business_day_convention = _convert_business_day_convention(business_day_convention)
        builder.day_count_convention = _convert_day_count_convention()
        
        # Build schedule
        schedule = builder.build()
        
        # Extract dates
        dates = [effective_date]
        for period in schedule.periods:
            dates.append(period.end_date)
        
        return dates
        
    except Exception as e:
        raise ValueError(f"Error generating schedule: {str(e)}")


def _convert_frequency(frequency: Frequency):
    """Convert Frequency enum to schedule builder frequency."""
    from .schedules.schedule_builder import Frequency as ScheduleFrequency
    
    freq_map = {
        Frequency.DAILY: ScheduleFrequency.DAILY,
        Frequency.WEEKLY: ScheduleFrequency.WEEKLY,
        Frequency.MONTHLY: ScheduleFrequency.MONTHLY,
        Frequency.QUARTERLY: ScheduleFrequency.QUARTERLY,
        Frequency.SEMI_ANNUAL: ScheduleFrequency.SEMI_ANNUAL,
        Frequency.ANNUAL: ScheduleFrequency.ANNUAL,
        Frequency.SEMI_ANNUAL_30_360: ScheduleFrequency.SEMI_ANNUAL,
        Frequency.ANNUAL_30_360: ScheduleFrequency.ANNUAL
    }
    
    return freq_map.get(frequency, ScheduleFrequency.QUARTERLY)


def _convert_calendar(calendar: Calendar):
    """Convert Calendar enum to schedule builder calendar."""
    from .schedules.calendar import Calendar as ScheduleCalendar, get_calendar
    
    # Use the get_calendar function to get the appropriate calendar
    return get_calendar(calendar.value)


def _convert_business_day_convention(bdc: BusinessDayConvention):
    """Convert BusinessDayConvention enum to schedule builder convention."""
    from .schedules.calendar import BusinessDayConvention as ScheduleBDC
    
    bdc_map = {
        BusinessDayConvention.FOLLOWING: ScheduleBDC.FOLLOWING,
        BusinessDayConvention.MODIFIED_FOLLOWING: ScheduleBDC.MODIFIED_FOLLOWING,
        BusinessDayConvention.PRECEDING: ScheduleBDC.PRECEDING,
        BusinessDayConvention.MODIFIED_PRECEDING: ScheduleBDC.MODIFIED_PRECEDING,
        BusinessDayConvention.UNADJUSTED: ScheduleBDC.UNADJUSTED
    }
    
    return bdc_map.get(bdc, ScheduleBDC.MODIFIED_FOLLOWING)


def _convert_day_count_convention():
    """Convert to schedule builder day count convention."""
    from .schedules.daycount import DayCountConvention as ScheduleDCC
    
    # Default to ACT/360
    return ScheduleDCC.ACT_360


def _frequency_to_months(frequency: Frequency) -> int:
    """Convert frequency enum to months.
    
    Args:
        frequency: Frequency enum
        
    Returns:
        Number of months
    """
    freq_map = {
        Frequency.DAILY: 0,  # Special case
        Frequency.WEEKLY: 0,  # Special case
        Frequency.MONTHLY: 1,
        Frequency.QUARTERLY: 3,
        Frequency.SEMI_ANNUAL: 6,
        Frequency.ANNUAL: 12,
        Frequency.SEMI_ANNUAL_30_360: 6,
        Frequency.ANNUAL_30_360: 12
    }
    
    return freq_map.get(frequency, 3)  # Default to quarterly


def _add_months(dt: date, months: int) -> date:
    """Add months to a date.
    
    Args:
        dt: Input date
        months: Number of months to add
        
    Returns:
        New date
    """
    if months == 0:
        return dt
        
    year = dt.year
    month = dt.month + months
    
    # Handle year overflow
    while month > 12:
        year += 1
        month -= 12
    
    # Handle year underflow
    while month < 1:
        year -= 1
        month += 12
    
    # Handle day overflow (e.g., Jan 31 + 1 month)
    try:
        return date(year, month, dt.day)
    except ValueError:
        # If day doesn't exist in target month, use last day of month
        if month == 2:
            # February - check for leap year
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return date(year, month, 29)
            else:
                return date(year, month, 28)
        else:
            # Use last day of month
            if month in [4, 6, 9, 11]:  # 30-day months
                return date(year, month, 30)
            else:  # 31-day months
                return date(year, month, 31)


def _apply_business_day_convention(
    schedule_date: date,
    calendar: Calendar,
    business_day_convention: BusinessDayConvention
) -> date:
    """Apply business day convention to a date.
    
    Args:
        schedule_date: Original schedule date
        calendar: Calendar for holiday adjustments
        business_day_convention: Business day convention
        
    Returns:
        Adjusted date
    """
    # For now, implement simple business day logic
    # In real implementation, would use QuantLib's calendar and business day conventions
    
    if business_day_convention == BusinessDayConvention.UNADJUSTED:
        return schedule_date
    
    # Simple weekend adjustment
    if schedule_date.weekday() >= 5:  # Saturday or Sunday
        if business_day_convention == BusinessDayConvention.FOLLOWING:
            # Move to next business day
            while schedule_date.weekday() >= 5:
                schedule_date = _add_days(schedule_date, 1)
        elif business_day_convention == BusinessDayConvention.PRECEDING:
            # Move to previous business day
            while schedule_date.weekday() >= 5:
                schedule_date = _add_days(schedule_date, -1)
        elif business_day_convention == BusinessDayConvention.MODIFIED_FOLLOWING:
            # Move to next business day, but if it crosses month boundary, use preceding
            next_business = schedule_date
            while next_business.weekday() >= 5:
                next_business = _add_days(next_business, 1)
            
            if next_business.month != schedule_date.month:
                # Crossed month boundary, use preceding
                prev_business = schedule_date
                while prev_business.weekday() >= 5:
                    prev_business = _add_days(prev_business, -1)
                schedule_date = prev_business
            else:
                schedule_date = next_business
    
    return schedule_date


def _add_days(dt: date, days: int) -> date:
    """Add days to a date.
    
    Args:
        dt: Input date
        days: Number of days to add
        
    Returns:
        New date
    """
    from datetime import timedelta
    return dt + timedelta(days=days)


def roll_date(
    input_date: date,
    calendar: Calendar,
    business_day_convention: BusinessDayConvention
) -> date:
    """Roll a date according to business day convention.
    
    Args:
        input_date: Input date
        calendar: Calendar for adjustments
        business_day_convention: Business day convention
        
    Returns:
        Rolled date
    """
    return _apply_business_day_convention(input_date, calendar, business_day_convention)


def adjust_date(
    input_date: date,
    calendar: Calendar,
    business_day_convention: BusinessDayConvention
) -> date:
    """Adjust a date according to business day convention.
    
    Args:
        input_date: Input date
        calendar: Calendar for adjustments
        business_day_convention: Business day convention
        
    Returns:
        Adjusted date
    """
    return _apply_business_day_convention(input_date, calendar, business_day_convention)


def is_business_day(input_date: date, calendar: Calendar) -> bool:
    """Check if a date is a business day.
    
    Args:
        input_date: Date to check
        calendar: Calendar to use
        
    Returns:
        True if business day, False otherwise
    """
    # Simple implementation - just check if it's a weekday
    # In real implementation, would use QuantLib's calendar
    return input_date.weekday() < 5  # Monday = 0, Sunday = 6


def business_days_between(start_date: date, end_date: date, calendar: Calendar) -> int:
    """Calculate business days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        calendar: Calendar to use
        
    Returns:
        Number of business days
    """
    # Simple implementation
    # In real implementation, would use QuantLib's calendar
    business_days = 0
    current_date = start_date
    
    while current_date < end_date:
        if is_business_day(current_date, calendar):
            business_days += 1
        current_date = _add_days(current_date, 1)
    
    return business_days
