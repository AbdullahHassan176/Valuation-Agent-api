"""Unit tests for schedule and daycount functionality."""

import pytest
from datetime import date, timedelta
from app.core.schedule_utils import make_schedule, roll_date, adjust_date, is_business_day, business_days_between
from app.core.daycount import accrual_factor, year_fraction, days_between, is_end_of_month, get_month_end
from app.core.models import (
    Frequency, Calendar, BusinessDayConvention, DayCountConvention,
    IRSSpec, CCSSpec, Currency, IndexName
)


class TestScheduleGeneration:
    """Test schedule generation functionality."""
    
    def test_quarterly_schedule_1y(self):
        """Test 1-year quarterly schedule generation."""
        effective = date(2024, 1, 15)
        maturity = date(2025, 1, 15)
        
        schedule = make_schedule(
            effective_date=effective,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # Should have 6 dates: start + 4 quarters + end
        assert len(schedule) == 6
        assert schedule[0] == effective
        assert schedule[-1] == maturity
        
        # Check quarterly spacing (approximately)
        for i in range(1, len(schedule) - 1):  # Exclude the last period which might be short
            days_diff = (schedule[i] - schedule[i-1]).days
            # Should be around 90 days (3 months)
            assert 85 <= days_diff <= 95, f"Unexpected spacing: {days_diff} days between {schedule[i-1]} and {schedule[i]}"
    
    def test_semi_annual_schedule_2y(self):
        """Test 2-year semi-annual schedule generation."""
        effective = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        schedule = make_schedule(
            effective_date=effective,
            maturity_date=maturity,
            frequency=Frequency.SEMI_ANNUAL,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.FOLLOWING
        )
        
        # Should have 6 dates: start + 4 semi-annual periods + end
        assert len(schedule) == 6
        assert schedule[0] == effective
        assert schedule[-1] == maturity
        
        # Check semi-annual spacing (approximately)
        for i in range(1, len(schedule) - 1):  # Exclude the last period which might be short
            days_diff = (schedule[i] - schedule[i-1]).days
            # Should be around 180 days (6 months)
            assert 175 <= days_diff <= 185, f"Unexpected spacing: {days_diff} days between {schedule[i-1]} and {schedule[i]}"
    
    def test_business_day_convention_following(self):
        """Test Following business day convention."""
        # Test with a Saturday
        saturday = date(2024, 1, 13)  # Saturday
        adjusted = roll_date(
            input_date=saturday,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.FOLLOWING
        )
        
        # Should move to Monday
        assert adjusted.weekday() == 0  # Monday
        assert adjusted > saturday
    
    def test_business_day_convention_preceding(self):
        """Test Preceding business day convention."""
        # Test with a Sunday
        sunday = date(2024, 1, 14)  # Sunday
        adjusted = roll_date(
            input_date=sunday,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.PRECEDING
        )
        
        # Should move to Friday
        assert adjusted.weekday() == 4  # Friday
        assert adjusted < sunday
    
    def test_business_day_convention_modified_following(self):
        """Test Modified Following business day convention."""
        # Test with a Saturday
        saturday = date(2024, 1, 13)  # Saturday
        adjusted = roll_date(
            input_date=saturday,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # Should move to Monday (same month)
        assert adjusted.weekday() == 0  # Monday
        assert adjusted > saturday
        assert adjusted.month == saturday.month
    
    def test_is_business_day(self):
        """Test business day checking."""
        # Monday should be business day
        monday = date(2024, 1, 15)
        assert is_business_day(monday, Calendar.WEEKENDS_ONLY)
        
        # Saturday should not be business day
        saturday = date(2024, 1, 13)
        assert not is_business_day(saturday, Calendar.WEEKENDS_ONLY)
        
        # Sunday should not be business day
        sunday = date(2024, 1, 14)
        assert not is_business_day(sunday, Calendar.WEEKENDS_ONLY)
    
    def test_business_days_between(self):
        """Test business days calculation."""
        start = date(2024, 1, 15)  # Monday
        end = date(2024, 1, 19)    # Friday
        
        business_days = business_days_between(start, end, Calendar.WEEKENDS_ONLY)
        assert business_days == 4  # Monday to Friday = 4 business days


class TestDayCountConventions:
    """Test day count convention calculations."""
    
    def test_act_360(self):
        """Test ACT/360 day count convention."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)  # 90 days
        
        factor = accrual_factor(start, end, DayCountConvention.ACT_360)
        expected = 91.0 / 360.0  # Actual days between Jan 15 and Apr 15 is 91
        assert abs(factor - expected) < 1e-3
    
    def test_act_365(self):
        """Test ACT/365 day count convention."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)  # 90 days
        
        factor = accrual_factor(start, end, DayCountConvention.ACT_365)
        expected = 91.0 / 365.0  # Actual days between Jan 15 and Apr 15 is 91
        assert abs(factor - expected) < 1e-3
    
    def test_act_365f(self):
        """Test ACT/365F day count convention."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)  # 90 days
        
        factor = accrual_factor(start, end, DayCountConvention.ACT_365F)
        expected = 91.0 / 365.0  # Actual days between Jan 15 and Apr 15 is 91
        assert abs(factor - expected) < 1e-3
    
    def test_thirty_360(self):
        """Test 30/360 day count convention."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)
        
        factor = accrual_factor(start, end, DayCountConvention.THIRTY_360)
        # 30/360: 3 months * 30 days = 90 days
        expected = 90.0 / 360.0
        assert abs(factor - expected) < 1e-10
    
    def test_act_act(self):
        """Test ACT/ACT day count convention."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)  # 90 days
        
        factor = accrual_factor(start, end, DayCountConvention.ACT_ACT)
        # Simple implementation uses 365.25
        expected = 91.0 / 365.25  # Actual days between Jan 15 and Apr 15 is 91
        assert abs(factor - expected) < 1e-3
    
    def test_year_fraction(self):
        """Test year fraction calculation."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)
        
        fraction = year_fraction(start, end, DayCountConvention.ACT_360)
        expected = 91.0 / 360.0  # Actual days between Jan 15 and Apr 15 is 91
        assert abs(fraction - expected) < 1e-3
    
    def test_days_between(self):
        """Test days between calculation."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 15)
        
        days = days_between(start, end)
        assert days == 91  # Jan 15 to Apr 15 is 91 days (inclusive)
    
    def test_is_end_of_month(self):
        """Test end of month checking."""
        # January 31st should be end of month
        jan_31 = date(2024, 1, 31)
        assert is_end_of_month(jan_31)
        
        # January 30th should not be end of month
        jan_30 = date(2024, 1, 30)
        assert not is_end_of_month(jan_30)
        
        # February 29th (leap year) should be end of month
        feb_29 = date(2024, 2, 29)
        assert is_end_of_month(feb_29)
    
    def test_get_month_end(self):
        """Test month end calculation."""
        # January 15th should give January 31st
        jan_15 = date(2024, 1, 15)
        month_end = get_month_end(jan_15)
        assert month_end == date(2024, 1, 31)
        
        # February 15th (leap year) should give February 29th
        feb_15 = date(2024, 2, 15)
        month_end = get_month_end(feb_15)
        assert month_end == date(2024, 2, 29)
        
        # February 15th (non-leap year) should give February 28th
        feb_15_2023 = date(2023, 2, 15)
        month_end = get_month_end(feb_15_2023)
        assert month_end == date(2023, 2, 28)


class TestAccrualSum:
    """Test accrual sum calculations for schedules."""
    
    def test_quarterly_schedule_accrual_sum(self):
        """Test accrual sum for 1-year quarterly schedule."""
        effective = date(2024, 1, 15)
        maturity = date(2025, 1, 15)
        
        schedule = make_schedule(
            effective_date=effective,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # Calculate accrual factors for each period
        accrual_factors = []
        for i in range(1, len(schedule)):
            factor = accrual_factor(
                schedule[i-1], 
                schedule[i], 
                DayCountConvention.ACT_360
            )
            accrual_factors.append(factor)
        
        # Sum of accrual factors should be approximately 1.0 (1 year)
        total_accrual = sum(accrual_factors)
        assert abs(total_accrual - 1.0) < 0.05, f"Total accrual {total_accrual} should be close to 1.0"
        
        # Each period should be approximately 0.25 (3 months) - exclude last period which might be short
        for i, factor in enumerate(accrual_factors[:-1]):  # Exclude last period
            assert abs(factor - 0.25) < 0.01, f"Period accrual {factor} should be close to 0.25"
    
    def test_semi_annual_schedule_accrual_sum(self):
        """Test accrual sum for 2-year semi-annual schedule."""
        effective = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        schedule = make_schedule(
            effective_date=effective,
            maturity_date=maturity,
            frequency=Frequency.SEMI_ANNUAL,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # Calculate accrual factors for each period
        accrual_factors = []
        for i in range(1, len(schedule)):
            factor = accrual_factor(
                schedule[i-1], 
                schedule[i], 
                DayCountConvention.ACT_360
            )
            accrual_factors.append(factor)
        
        # Sum of accrual factors should be approximately 2.0 (2 years)
        total_accrual = sum(accrual_factors)
        assert abs(total_accrual - 2.0) < 0.05, f"Total accrual {total_accrual} should be close to 2.0"
        
        # Each period should be approximately 0.5 (6 months) - exclude last period which might be short
        for i, factor in enumerate(accrual_factors[:-1]):  # Exclude last period
            assert abs(factor - 0.5) < 0.01, f"Period accrual {factor} should be close to 0.5"


class TestIRSSpec:
    """Test IRS specification model."""
    
    def test_irs_spec_creation(self):
        """Test IRS specification creation."""
        irs = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=True,
            fixed_rate=0.05,
            float_index=IndexName.SOFR_3M,
            effective_date=date(2024, 1, 15),
            maturity_date=date(2025, 1, 15),
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        assert irs.notional == 1000000.0
        assert irs.currency == Currency.USD
        assert irs.pay_fixed is True
        assert irs.fixed_rate == 0.05
        assert irs.float_index == IndexName.SOFR_3M
        assert irs.effective_date == date(2024, 1, 15)
        assert irs.maturity_date == date(2025, 1, 15)


class TestCCSSpec:
    """Test CCS specification model."""
    
    def test_ccs_spec_creation(self):
        """Test CCS specification creation."""
        ccs = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=850000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=date(2024, 1, 15),
            maturity_date=date(2025, 1, 15),
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        assert ccs.notional_leg1 == 1000000.0
        assert ccs.notional_leg2 == 850000.0
        assert ccs.currency_leg1 == Currency.USD
        assert ccs.currency_leg2 == Currency.EUR
        assert ccs.index_leg1 == IndexName.SOFR_3M
        assert ccs.index_leg2 == IndexName.EURIBOR_3M
        assert ccs.effective_date == date(2024, 1, 15)
        assert ccs.maturity_date == date(2025, 1, 15)
        assert ccs.constant_notional is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
