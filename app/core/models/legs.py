from dataclasses import dataclass
from typing import List, Optional
from datetime import date
from enum import Enum

class LegType(str, Enum):
    FIXED = "fixed"
    FLOATING = "floating"
    OIS = "ois"

class PaymentDirection(str, Enum):
    PAY = "pay"
    RECEIVE = "receive"

@dataclass
class PaymentSchedule:
    """Payment schedule for a leg"""
    payment_dates: List[date]
    accrual_start_dates: List[date]
    accrual_end_dates: List[date]
    accrual_factors: List[float]
    
@dataclass
class FixedLeg:
    """Fixed rate leg specification"""
    leg_type: LegType = LegType.FIXED
    notional: float = 0.0
    currency: str = "USD"
    fixed_rate: float = 0.0
    payment_direction: PaymentDirection = PaymentDirection.PAY
    day_count_convention: str = "ACT/360"
    payment_frequency: str = "Q"
    business_day_convention: str = "FOLLOWING"
    calendar: str = "USD"
    schedule: Optional[PaymentSchedule] = None

@dataclass
class FloatingLeg:
    """Floating rate leg specification"""
    leg_type: LegType = LegType.FLOATING
    notional: float = 0.0
    currency: str = "USD"
    floating_index: str = "USD-LIBOR-3M"
    payment_direction: PaymentDirection = PaymentDirection.RECEIVE
    day_count_convention: str = "ACT/360"
    payment_frequency: str = "Q"
    business_day_convention: str = "FOLLOWING"
    calendar: str = "USD"
    schedule: Optional[PaymentSchedule] = None

@dataclass
class SwapLegs:
    """Container for swap legs"""
    fixed_leg: Optional[FixedLeg] = None
    floating_leg: Optional[FloatingLeg] = None
    # For CCS, we might have multiple currencies
    legs: List[FixedLeg | FloatingLeg] = None
    
    def __post_init__(self):
        if self.legs is None:
            self.legs = []
            if self.fixed_leg:
                self.legs.append(self.fixed_leg)
            if self.floating_leg:
                self.legs.append(self.floating_leg)
