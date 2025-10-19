"""Pydantic schemas for the valuation API."""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"


class DayCountConvention(str, Enum):
    """Day count conventions."""
    ACT_360 = "ACT/360"
    ACT_365 = "ACT/365"
    ACT_365F = "ACT/365F"
    ACT_ACT = "ACT/ACT"
    THIRTY_360 = "30/360"
    THIRTY_E_360 = "30E/360"
    THIRTY_E_PLUS_360 = "30E+/360"


class BusinessDayConvention(str, Enum):
    """Business day conventions."""
    FOLLOWING = "Following"
    MODIFIED_FOLLOWING = "ModifiedFollowing"
    PRECEDING = "Preceding"
    MODIFIED_PRECEDING = "ModifiedPreceding"
    UNADJUSTED = "Unadjusted"


class Calendar(str, Enum):
    """Market calendars."""
    WEEKENDS_ONLY = "WeekendsOnly"
    UNITED_STATES = "UnitedStates"
    UNITED_KINGDOM = "UnitedKingdom"
    GERMANY = "Germany"
    JAPAN = "Japan"
    SWITZERLAND = "Switzerland"
    CANADA = "Canada"
    AUSTRALIA = "Australia"
    NEW_ZEALAND = "NewZealand"
    SWEDEN = "Sweden"
    NORWAY = "Norway"
    DENMARK = "Denmark"


class InstrumentType(str, Enum):
    """Financial instrument types."""
    INTEREST_RATE_SWAP = "InterestRateSwap"
    CROSS_CURRENCY_SWAP = "CrossCurrencySwap"
    FORWARD_RATE_AGREEMENT = "ForwardRateAgreement"
    CAP = "Cap"
    FLOOR = "Floor"
    SWAPTION = "Swaption"
    BOND = "Bond"
    FUTURE = "Future"
    OPTION = "Option"


class ValuationRequest(BaseModel):
    """Request model for valuation."""
    
    instrument_type: InstrumentType
    notional: float = Field(gt=0, description="Notional amount")
    currency: Currency
    start_date: date
    end_date: date
    day_count: DayCountConvention = DayCountConvention.ACT_360
    business_day_convention: BusinessDayConvention = BusinessDayConvention.MODIFIED_FOLLOWING
    calendar: Calendar = Calendar.WEEKENDS_ONLY
    
    # Instrument-specific fields
    fixed_rate: Optional[float] = Field(None, description="Fixed rate for swaps")
    floating_index: Optional[str] = Field(None, description="Floating rate index")
    payment_frequency: Optional[str] = Field(None, description="Payment frequency")
    
    # Market data
    market_curves: Optional[List[dict]] = Field(None, description="Market curves data")
    volatility_surface: Optional[dict] = Field(None, description="Volatility surface data")


class ValuationResponse(BaseModel):
    """Response model for valuation."""
    
    present_value: float
    currency: Currency
    valuation_date: date
    instrument_type: InstrumentType
    risk_metrics: Optional[dict] = None
    sensitivities: Optional[dict] = None
    calculation_details: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response."""
    
    ok: bool
    service: str
    timestamp: str
    status: str


class Frequency(str, Enum):
    """Payment frequencies."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUAL = "SemiAnnual"
    ANNUAL = "Annual"
    SEMI_ANNUAL_30_360 = "SemiAnnual30/360"
    ANNUAL_30_360 = "Annual30/360"


class IndexName(str, Enum):
    """Floating rate indices."""
    SOFR = "SOFR"
    SOFR_3M = "SOFR-3M"
    SOFR_6M = "SOFR-6M"
    LIBOR_1M = "LIBOR-1M"
    LIBOR_3M = "LIBOR-3M"
    LIBOR_6M = "LIBOR-6M"
    LIBOR_12M = "LIBOR-12M"
    EURIBOR_1M = "EURIBOR-1M"
    EURIBOR_3M = "EURIBOR-3M"
    EURIBOR_6M = "EURIBOR-6M"
    EURIBOR_12M = "EURIBOR-12M"
    SONIA = "SONIA"
    TONAR = "TONAR"
    BBSW_1M = "BBSW-1M"
    BBSW_3M = "BBSW-3M"
    BBSW_6M = "BBSW-6M"
    CDOR_1M = "CDOR-1M"
    CDOR_3M = "CDOR-3M"
    CDOR_6M = "CDOR-6M"


class IRSSpec(BaseModel):
    """Interest Rate Swap specification."""
    
    notional: float = Field(gt=0, description="Notional amount")
    currency: Currency = Field(..., description="Currency")
    pay_fixed: bool = Field(..., description="True if paying fixed rate")
    fixed_rate: Optional[float] = Field(None, description="Fixed rate (if applicable)")
    float_index: IndexName = Field(..., description="Floating rate index")
    effective_date: date = Field(..., description="Effective date")
    maturity_date: date = Field(..., description="Maturity date")
    day_count_fixed: DayCountConvention = Field(DayCountConvention.ACT_360, description="Day count for fixed leg")
    day_count_float: DayCountConvention = Field(DayCountConvention.ACT_360, description="Day count for floating leg")
    frequency_fixed: Frequency = Field(Frequency.QUARTERLY, description="Payment frequency for fixed leg")
    frequency_float: Frequency = Field(Frequency.QUARTERLY, description="Payment frequency for floating leg")
    calendar: Calendar = Field(Calendar.WEEKENDS_ONLY, description="Calendar")
    business_day_convention: BusinessDayConvention = Field(BusinessDayConvention.MODIFIED_FOLLOWING, description="Business day convention")


class CCSSpec(BaseModel):
    """Cross Currency Swap specification."""
    
    notional_leg1: float = Field(gt=0, description="Notional for leg 1")
    notional_leg2: float = Field(gt=0, description="Notional for leg 2")
    currency_leg1: Currency = Field(..., description="Currency for leg 1")
    currency_leg2: Currency = Field(..., description="Currency for leg 2")
    index_leg1: IndexName = Field(..., description="Floating rate index for leg 1")
    index_leg2: IndexName = Field(..., description="Floating rate index for leg 2")
    effective_date: date = Field(..., description="Effective date")
    maturity_date: date = Field(..., description="Maturity date")
    frequency: Frequency = Field(Frequency.QUARTERLY, description="Payment frequency")
    day_count: DayCountConvention = Field(DayCountConvention.ACT_360, description="Day count convention")
    calendar: Calendar = Field(Calendar.WEEKENDS_ONLY, description="Calendar")
    business_day_convention: BusinessDayConvention = Field(BusinessDayConvention.MODIFIED_FOLLOWING, description="Business day convention")
    constant_notional: bool = Field(True, description="Whether notional is constant")
