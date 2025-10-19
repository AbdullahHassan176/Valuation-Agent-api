"""
Schedule generation for interest rate swaps
"""
from datetime import date, timedelta
from typing import List, Optional
from enum import Enum
from dataclasses import dataclass

from .calendar import Calendar, BusinessDayConvention, get_calendar
from .daycount import DayCountConvention, parse_day_count_convention

class Frequency(Enum):
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"
    QUARTERLY = "Q"
    SEMI_ANNUAL = "S"
    ANNUAL = "A"

class StubConvention(Enum):
    SHORT_FIRST = "SHORT_FIRST"
    SHORT_LAST = "SHORT_LAST"
    LONG_FIRST = "LONG_FIRST"
    LONG_LAST = "LONG_LAST"

@dataclass
class SchedulePeriod:
    """A single period in a payment schedule"""
    start_date: date
    end_date: date
    payment_date: date
    day_count_fraction: float
    period_number: int

@dataclass
class PaymentSchedule:
    """Complete payment schedule for a swap leg"""
    periods: List[SchedulePeriod]
    effective_date: date
    termination_date: date
    frequency: Frequency
    day_count_convention: DayCountConvention
    business_day_convention: BusinessDayConvention
    calendar: Calendar

class ScheduleBuilder:
    """Builder for generating payment schedules"""
    
    def __init__(self):
        self.effective_date: Optional[date] = None
        self.termination_date: Optional[date] = None
        self.frequency: Optional[Frequency] = None
        self.day_count_convention: Optional[DayCountConvention] = None
        self.business_day_convention: Optional[BusinessDayConvention] = None
        self.calendar: Optional[Calendar] = None
        self.stub_convention: StubConvention = StubConvention.SHORT_FIRST
    
    def with_effective_date(self, effective_date: date) -> 'ScheduleBuilder':
        self.effective_date = effective_date
        return self
    
    def with_termination_date(self, termination_date: date) -> 'ScheduleBuilder':
        self.termination_date = termination_date
        return self
    
    def with_frequency(self, frequency: str) -> 'ScheduleBuilder':
        """Set frequency from string (e.g., 'Q' for quarterly)"""
        freq_map = {
            "D": Frequency.DAILY,
            "W": Frequency.WEEKLY,
            "M": Frequency.MONTHLY,
            "Q": Frequency.QUARTERLY,
            "S": Frequency.SEMI_ANNUAL,
            "A": Frequency.ANNUAL,
        }
        self.frequency = freq_map.get(frequency.upper())
        if self.frequency is None:
            raise ValueError(f"Unknown frequency: {frequency}")
        return self
    
    def with_day_count_convention(self, convention: str) -> 'ScheduleBuilder':
        self.day_count_convention = parse_day_count_convention(convention)
        return self
    
    def with_business_day_convention(self, convention: str) -> 'ScheduleBuilder':
        bdc_map = {
            "FOLLOWING": BusinessDayConvention.FOLLOWING,
            "MODIFIED_FOLLOWING": BusinessDayConvention.MODIFIED_FOLLOWING,
            "PRECEDING": BusinessDayConvention.PRECEDING,
            "MODIFIED_PRECEDING": BusinessDayConvention.MODIFIED_PRECEDING,
            "UNADJUSTED": BusinessDayConvention.UNADJUSTED,
        }
        self.business_day_convention = bdc_map.get(convention.upper())
        if self.business_day_convention is None:
            raise ValueError(f"Unknown business day convention: {convention}")
        return self
    
    def with_calendar(self, calendar_name: str) -> 'ScheduleBuilder':
        self.calendar = get_calendar(calendar_name)
        return self
    
    def with_stub_convention(self, convention: StubConvention) -> 'ScheduleBuilder':
        self.stub_convention = convention
        return self
    
    def build(self) -> PaymentSchedule:
        """Build the payment schedule"""
        if not all([self.effective_date, self.termination_date, self.frequency, 
                   self.day_count_convention, self.business_day_convention, self.calendar]):
            raise ValueError("All schedule parameters must be set before building")
        
        # Generate unadjusted dates
        unadjusted_dates = self._generate_unadjusted_dates()
        
        # Adjust for business days
        adjusted_dates = self._adjust_business_days(unadjusted_dates)
        
        # Create periods
        periods = self._create_periods(adjusted_dates)
        
        return PaymentSchedule(
            periods=periods,
            effective_date=self.effective_date,
            termination_date=self.termination_date,
            frequency=self.frequency,
            day_count_convention=self.day_count_convention,
            business_day_convention=self.business_day_convention,
            calendar=self.calendar
        )
    
    def _generate_unadjusted_dates(self) -> List[date]:
        """Generate unadjusted schedule dates"""
        dates = [self.effective_date]
        
        if self.frequency == Frequency.DAILY:
            increment = timedelta(days=1)
        elif self.frequency == Frequency.WEEKLY:
            increment = timedelta(weeks=1)
        elif self.frequency == Frequency.MONTHLY:
            increment = timedelta(days=30)  # Approximate
        elif self.frequency == Frequency.QUARTERLY:
            increment = timedelta(days=90)  # Approximate
        elif self.frequency == Frequency.SEMI_ANNUAL:
            increment = timedelta(days=180)  # Approximate
        elif self.frequency == Frequency.ANNUAL:
            increment = timedelta(days=365)  # Approximate
        
        current_date = self.effective_date
        while current_date < self.termination_date:
            current_date += increment
            if current_date <= self.termination_date:
                dates.append(current_date)
        
        # Ensure termination date is included
        if dates[-1] != self.termination_date:
            dates.append(self.termination_date)
        
        return dates
    
    def _adjust_business_days(self, dates: List[date]) -> List[date]:
        """Adjust dates for business day conventions"""
        adjusted = []
        for d in dates:
            adjusted_date = self.calendar.adjust(d, self.business_day_convention)
            adjusted.append(adjusted_date)
        return adjusted
    
    def _create_periods(self, dates: List[date]) -> List[SchedulePeriod]:
        """Create schedule periods from dates"""
        periods = []
        
        for i in range(len(dates) - 1):
            start_date = dates[i]
            end_date = dates[i + 1]
            payment_date = end_date  # Payment typically on period end
            
            # Calculate day count fraction
            from .daycount import day_count_fraction
            dcf = day_count_fraction(start_date, end_date, self.day_count_convention)
            
            period = SchedulePeriod(
                start_date=start_date,
                end_date=end_date,
                payment_date=payment_date,
                day_count_fraction=dcf,
                period_number=i + 1
            )
            periods.append(period)
        
        return periods

def create_schedule(
    effective_date: date,
    termination_date: date,
    frequency: str,
    day_count_convention: str,
    business_day_convention: str = "FOLLOWING",
    calendar_name: str = "USD"
) -> PaymentSchedule:
    """Convenience function to create a payment schedule"""
    return (ScheduleBuilder()
            .with_effective_date(effective_date)
            .with_termination_date(termination_date)
            .with_frequency(frequency)
            .with_day_count_convention(day_count_convention)
            .with_business_day_convention(business_day_convention)
            .with_calendar(calendar_name)
            .build())

