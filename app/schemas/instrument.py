from typing import Optional, Union
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum

class DayCountConvention(str, Enum):
    ACT_360 = "ACT/360"
    ACT_365 = "ACT/365"
    THIRTY_360 = "30/360"
    ACT_ACT = "ACT/ACT"

class Frequency(str, Enum):
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "M"
    QUARTERLY = "Q"
    SEMI_ANNUAL = "S"
    ANNUAL = "A"

class BusinessDayConvention(str, Enum):
    FOLLOWING = "FOLLOWING"
    MODIFIED_FOLLOWING = "MODIFIED_FOLLOWING"
    PRECEDING = "PRECEDING"
    MODIFIED_PRECEDING = "MODIFIED_PRECEDING"

class IRSSpec(BaseModel):
    """Interest Rate Swap specification"""
    notional: float = Field(..., description="Notional amount", gt=0)
    ccy: str = Field(..., description="Currency code (e.g., USD, EUR)", min_length=3, max_length=3)
    payFixed: bool = Field(..., description="True if paying fixed rate, False if receiving fixed rate")
    fixedRate: Optional[float] = Field(None, description="Fixed rate (if not provided, will be calculated)", ge=0)
    floatIndex: str = Field(..., description="Floating rate index (e.g., USD-LIBOR-3M, SOFR)")
    effective: date = Field(..., description="Effective date of the swap")
    maturity: date = Field(..., description="Maturity date of the swap")
    dcFixed: DayCountConvention = Field(..., description="Day count convention for fixed leg")
    dcFloat: DayCountConvention = Field(..., description="Day count convention for floating leg")
    freqFixed: Frequency = Field(..., description="Payment frequency for fixed leg")
    freqFloat: Frequency = Field(..., description="Payment frequency for floating leg")
    calendar: str = Field(..., description="Business day calendar (e.g., USD, EUR)")
    bdc: BusinessDayConvention = Field(..., description="Business day convention")
    csa: Optional[str] = Field(None, description="Credit Support Annex identifier")

class CCSSpec(BaseModel):
    """Cross Currency Swap specification"""
    notional: float = Field(..., description="Notional amount", gt=0)
    ccy: str = Field(..., description="Currency code (e.g., USD, EUR)", min_length=3, max_length=3)
    payFixed: bool = Field(..., description="True if paying fixed rate, False if receiving fixed rate")
    fixedRate: Optional[float] = Field(None, description="Fixed rate (if not provided, will be calculated)", ge=0)
    floatIndex: str = Field(..., description="Floating rate index (e.g., USD-LIBOR-3M, SOFR)")
    effective: date = Field(..., description="Effective date of the swap")
    maturity: date = Field(..., description="Maturity date of the swap")
    dcFixed: DayCountConvention = Field(..., description="Day count convention for fixed leg")
    dcFloat: DayCountConvention = Field(..., description="Day count convention for floating leg")
    freqFixed: Frequency = Field(..., description="Payment frequency for fixed leg")
    freqFloat: Frequency = Field(..., description="Payment frequency for floating leg")
    calendar: str = Field(..., description="Business day calendar (e.g., USD, EUR)")
    bdc: BusinessDayConvention = Field(..., description="Business day convention")
    csa: Optional[str] = Field(None, description="Credit Support Annex identifier")
    # CCS-specific fields
    notionalCcy2: float = Field(..., description="Notional amount in second currency", gt=0)
    ccy2: str = Field(..., description="Second currency code", min_length=3, max_length=3)
    fxRate: Optional[float] = Field(None, description="FX rate (if not provided, will be calculated)", gt=0)
