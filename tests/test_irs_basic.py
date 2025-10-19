"""Basic IRS pricing tests."""

import pytest
from datetime import date, timedelta
from app.core.models import IRSSpec, Currency, DayCountConvention, Frequency, BusinessDayConvention, Calendar, IndexName
from app.core.pricing.irs import price_irs, create_synthetic_curves, PVBreakdown
from app.core.pricing.irs import CurveData


class TestIRSPricing:
    """Test IRS pricing functionality."""
    
    def test_bootstrap_usd_curve(self):
        """Test USD curve bootstrapping."""
        as_of = date(2024, 1, 15)
        curves = create_synthetic_curves(as_of, "USD")
        
        # Check that curves are created
        assert "discount" in curves
        assert "forward" in curves
        
        # Check discount curve has reasonable values
        discount_curve = curves["discount"]
        assert len(discount_curve.discount_curve) > 0
        assert all(0 < df < 1 for df in discount_curve.discount_curve.values())
        
        # Check forward curve has reasonable values
        forward_curve = curves["forward"]
        assert len(forward_curve.forward_curve) > 0
        assert all(rate >= 0 for rate in forward_curve.forward_curve.values())
    
    def test_atm_5y_swap_pricing(self):
        """Test ATM 5Y swap pricing - should have small PV."""
        as_of = date(2024, 1, 15)
        maturity = date(2029, 1, 15)  # 5 years
        
        # Create ATM swap (pay fixed = false, so receiving fixed)
        spec = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=False,  # Receiving fixed
            fixed_rate=0.05,  # 5% fixed rate
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # Create curves
        curves = create_synthetic_curves(as_of, "USD")
        
        # Price the swap
        result = price_irs(spec, curves)
        
        # Check result structure
        assert isinstance(result, PVBreakdown)
        assert result.currency == "USD"
        assert result.as_of == as_of
        assert len(result.legs) == 2  # Fixed and floating legs
        assert len(result.sensitivities) > 0
        
        # Check legs
        fixed_leg = next(leg for leg in result.legs if leg["name"] == "Fixed Leg")
        float_leg = next(leg for leg in result.legs if leg["name"] == "Floating Leg")
        
        assert fixed_leg["currency"] == "USD"
        assert float_leg["currency"] == "USD"
        assert "cashflows" in fixed_leg
        assert "cashflows" in float_leg
        
        # For ATM swap, PV should be close to zero
        # Since we're using synthetic curves with 5% rates, the PV should be small
        epsilon = 0.01 * spec.notional  # 1% of notional as tolerance
        assert abs(result.pv_base_ccy) < epsilon, f"PV {result.pv_base_ccy} should be close to zero for ATM swap"
    
    def test_pv01_calculation(self):
        """Test PV01 calculation."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)  # 2 years
        
        spec = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=True,  # Paying fixed
            fixed_rate=0.05,
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        curves = create_synthetic_curves(as_of, "USD")
        result = price_irs(spec, curves)
        
        # Check PV01 is calculated
        pv01_sensitivity = next(s for s in result.sensitivities if s["shock"] == "PV01")
        pv01_value = pv01_sensitivity["value"]
        
        # PV01 should be positive and within reasonable range
        assert pv01_value > 0, "PV01 should be positive"
        assert pv01_value < 1000, "PV01 should be reasonable (less than $1000 per bp)"
        assert pv01_value > 10, "PV01 should be meaningful (more than $10 per bp)"
    
    def test_negative_notional_validation(self):
        """Test validation rejects negative notional."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        # This test is handled by Pydantic validation, so we test that instead
        with pytest.raises(Exception, match="Input should be greater than 0"):
            IRSSpec(
                notional=-1000000.0,  # Negative notional
                currency=Currency.USD,
                pay_fixed=True,
                fixed_rate=0.05,
                float_index=IndexName.SOFR_3M,
                effective_date=as_of,
                maturity_date=maturity,
                day_count_fixed=DayCountConvention.ACT_360,
                day_count_float=DayCountConvention.ACT_360,
                frequency_fixed=Frequency.QUARTERLY,
                frequency_float=Frequency.QUARTERLY,
                calendar=Calendar.WEEKENDS_ONLY,
                business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
            )
    
    def test_invalid_dates_validation(self):
        """Test validation rejects invalid dates."""
        as_of = date(2024, 1, 15)
        maturity = date(2024, 1, 10)  # Maturity before effective date
        
        spec = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=True,
            fixed_rate=0.05,
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        curves = create_synthetic_curves(as_of, "USD")
        
        with pytest.raises(ValueError, match="Effective date must be before maturity date"):
            price_irs(spec, curves)
    
    def test_missing_curves_validation(self):
        """Test validation rejects missing curves."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        spec = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=True,
            fixed_rate=0.05,
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # Missing curves
        empty_curves = {}
        
        with pytest.raises(ValueError, match="Error pricing IRS: Market curves are required"):
            price_irs(spec, empty_curves)
    
    def test_pay_fixed_vs_receive_fixed(self):
        """Test that pay fixed vs receive fixed gives opposite signs."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        # Pay fixed swap (higher fixed rate)
        spec_pay = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=True,
            fixed_rate=0.06,  # Higher fixed rate
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # Receive fixed swap (same higher fixed rate)
        spec_receive = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=False,
            fixed_rate=0.06,  # Same higher fixed rate
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        curves = create_synthetic_curves(as_of, "USD")
        
        result_pay = price_irs(spec_pay, curves)
        result_receive = price_irs(spec_receive, curves)
        
        # PVs should have opposite signs
        assert result_pay.pv_base_ccy * result_receive.pv_base_ccy < 0, "Pay and receive fixed should have opposite PV signs"
        
        # Absolute values should be approximately equal
        assert abs(abs(result_pay.pv_base_ccy) - abs(result_receive.pv_base_ccy)) < 1.0, "Absolute PVs should be approximately equal"
    
    def test_different_currencies(self):
        """Test pricing with different currencies."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        # USD swap
        spec_usd = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=True,
            fixed_rate=0.05,
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        # EUR swap
        spec_eur = IRSSpec(
            notional=1000000.0,
            currency=Currency.EUR,
            pay_fixed=True,
            fixed_rate=0.05,
            float_index=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        curves_usd = create_synthetic_curves(as_of, "USD")
        curves_eur = create_synthetic_curves(as_of, "EUR")
        
        result_usd = price_irs(spec_usd, curves_usd)
        result_eur = price_irs(spec_eur, curves_eur)
        
        # Both should complete successfully
        assert result_usd.currency == "USD"
        assert result_eur.currency == "EUR"
        assert isinstance(result_usd.pv_base_ccy, float)
        assert isinstance(result_eur.pv_base_ccy, float)
    
    def test_cashflow_details(self):
        """Test that cashflow details are provided."""
        as_of = date(2024, 1, 15)
        maturity = date(2025, 1, 15)  # 1 year
        
        spec = IRSSpec(
            notional=1000000.0,
            currency=Currency.USD,
            pay_fixed=True,
            fixed_rate=0.05,
            float_index=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            day_count_fixed=DayCountConvention.ACT_360,
            day_count_float=DayCountConvention.ACT_360,
            frequency_fixed=Frequency.QUARTERLY,
            frequency_float=Frequency.QUARTERLY,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING
        )
        
        curves = create_synthetic_curves(as_of, "USD")
        result = price_irs(spec, curves)
        
        # Check cashflow details
        fixed_leg = next(leg for leg in result.legs if leg["name"] == "Fixed Leg")
        float_leg = next(leg for leg in result.legs if leg["name"] == "Floating Leg")
        
        assert "cashflows" in fixed_leg
        assert "cashflows" in float_leg
        
        # Check cashflow structure
        if fixed_leg["cashflows"]:
            cashflow = fixed_leg["cashflows"][0]
            required_fields = ["start_date", "end_date", "accrual_factor", "rate", "cashflow", "discount_factor", "present_value"]
            for field in required_fields:
                assert field in cashflow, f"Cashflow missing field: {field}"
        
        if float_leg["cashflows"]:
            cashflow = float_leg["cashflows"][0]
            required_fields = ["start_date", "end_date", "accrual_factor", "rate", "cashflow", "discount_factor", "present_value"]
            for field in required_fields:
                assert field in cashflow, f"Cashflow missing field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
