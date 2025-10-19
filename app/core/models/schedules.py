from dataclasses import dataclass
from typing import List, Optional
from datetime import date
from enum import Enum

class ScheduleType(str, Enum):
    REGULAR = "regular"
    STUB = "stub"
    SHORT_FIRST = "short_first"
    SHORT_LAST = "short_last"

@dataclass
class SchedulePeriod:
    """Individual period in a schedule"""
    start_date: date
    end_date: date
    payment_date: date
    accrual_factor: float
    period_type: ScheduleType = ScheduleType.REGULAR

@dataclass
class Schedule:
    """Payment schedule for financial instruments"""
    effective_date: date
    maturity_date: date
    periods: List[SchedulePeriod]
    frequency: str = "Q"
    day_count_convention: str = "ACT/360"
    business_day_convention: str = "FOLLOWING"
    calendar: str = "USD"
    
    def get_payment_dates(self) -> List[date]:
        """Get all payment dates"""
        return [period.payment_date for period in self.periods]
    
    def get_accrual_factors(self) -> List[float]:
        """Get all accrual factors"""
        return [period.accrual_factor for period in self.periods]
    
    def get_total_accrual_factor(self) -> float:
        """Get total accrual factor"""
        return sum(self.get_accrual_factors())

@dataclass
class ScheduleBuilder:
    """Builder for creating schedules"""
    effective_date: date
    maturity_date: date
    frequency: str = "Q"
    day_count_convention: str = "ACT/360"
    business_day_convention: str = "FOLLOWING"
    calendar: str = "USD"
    
    def build(self) -> Schedule:
        """Build the schedule (placeholder implementation)"""
        # This would normally use QuantLib or similar to generate proper schedules
        # For now, return a simple placeholder
        periods = [
            SchedulePeriod(
                start_date=self.effective_date,
                end_date=self.maturity_date,
                payment_date=self.maturity_date,
                accrual_factor=1.0,
                period_type=ScheduleType.REGULAR
            )
        ]
        
        return Schedule(
            effective_date=self.effective_date,
            maturity_date=self.maturity_date,
            periods=periods,
            frequency=self.frequency,
            day_count_convention=self.day_count_convention,
            business_day_convention=self.business_day_convention,
            calendar=self.calendar
        )

