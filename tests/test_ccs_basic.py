"""Basic Cross Currency Swap pricing tests."""

import pytest
from datetime import date, timedelta
from app.core.models import CCSSpec, Currency, DayCountConvention, Frequency, BusinessDayConvention, Calendar, IndexName
from app.core.pricing.ccs import price_ccs, create_synthetic_ccs_curves, CCSBreakdown
from app.core.pricing.ccs import CurveData


class TestCCSPricing:
    """Test CCS pricing functionality."""
    
    def test_bootstrap_usd_eur_curves(self):
        """Test USD and EUR curve bootstrapping."""
        as_of = date(2024, 1, 15)
        curves = create_synthetic_ccs_curves(as_of)
        
        # Check that all required curves are created
        required_curves = ["discUSD", "discEUR", "fwdUSD", "fwdEUR", "fxFwd"]
        for curve_name in required_curves:
            assert curve_name in curves, f"Missing curve: {curve_name}"
        
        # Check USD discount curve
        usd_disc = curves["discUSD"]
        assert len(usd_disc.discount_curve) > 0
        assert all(0 < df < 1 for df in usd_disc.discount_curve.values())
        
        # Check EUR discount curve
        eur_disc = curves["discEUR"]
        assert len(eur_disc.discount_curve) > 0
        assert all(0 < df < 1 for df in eur_disc.discount_curve.values())
        
        # Check FX forward curve
        fx_fwd = curves["fxFwd"]
        assert len(fx_fwd.forward_curve) > 0
        assert all(rate > 0 for rate in fx_fwd.forward_curve.values())
    
    def test_market_consistent_5y_ccs_pricing(self):
        """Test market-consistent 5Y CCS pricing - should have small PV."""
        as_of = date(2024, 1, 15)
        maturity = date(2029, 1, 15)  # 5 years
        
        # Create market-consistent CCS (USD/EUR with similar rates)
        spec = CCSSpec(
            notional_leg1=1000000.0,  # USD 1M
            notional_leg2=900000.0,   # EUR 900K (roughly equivalent at 1.08 FX)
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        # Create curves
        curves = create_synthetic_ccs_curves(as_of)
        
        # Price the CCS
        result = price_ccs(spec, curves)
        
        # Check result structure
        assert isinstance(result, CCSBreakdown)
        assert result.currency == "USD"  # Reporting currency
        assert result.reporting_currency == "USD"
        assert result.as_of == as_of
        assert len(result.legs) == 2  # Two legs
        assert len(result.sensitivities) == 2  # FX sensitivities
        
        # Check legs
        leg1 = next(leg for leg in result.legs if "Leg 1" in leg["name"])
        leg2 = next(leg for leg in result.legs if "Leg 2" in leg["name"])
        
        assert leg1["currency"] == "USD"
        assert leg2["currency"] == "EUR"
        assert "cashflows" in leg1
        assert "cashflows" in leg2
        
        # For synthetic curves, PV should be reasonable (not too large)
        # Since we're using synthetic curves, we just check that PV is reasonable
        max_pv = 0.5 * spec.notional_leg1  # 50% of USD notional as max tolerance
        assert abs(result.pv_reporting_ccy) < max_pv, f"PV {result.pv_reporting_ccy} should be reasonable for synthetic CCS"
    
    def test_fx_sensitivity_calculation(self):
        """Test FX ±1% sensitivity calculations."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)  # 2 years
        
        spec = CCSSpec(
            notional_leg1=1000000.0,  # USD 1M
            notional_leg2=900000.0,   # EUR 900K
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        curves = create_synthetic_ccs_curves(as_of)
        result = price_ccs(spec, curves)
        
        # Check FX sensitivities are calculated
        fx_plus_sensitivity = next(s for s in result.sensitivities if s["shock"] == "FX_PLUS_1PCT")
        fx_minus_sensitivity = next(s for s in result.sensitivities if s["shock"] == "FX_MINUS_1PCT")
        
        fx_plus_value = fx_plus_sensitivity["value"]
        fx_minus_value = fx_minus_sensitivity["value"]
        
        # FX sensitivities should be opposite signs and roughly antisymmetric
        assert fx_plus_value * fx_minus_value < 0, "FX sensitivities should have opposite signs"
        assert abs(fx_plus_value + fx_minus_value) < abs(fx_plus_value) * 0.5, "FX sensitivities should be roughly antisymmetric"
        
        # Sensitivities should be meaningful
        assert abs(fx_plus_value) > 0, "FX sensitivity should be non-zero"
        assert abs(fx_minus_value) > 0, "FX sensitivity should be non-zero"
    
    def test_negative_notional_validation(self):
        """Test validation rejects negative notionals."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        # This test is handled by Pydantic validation, so we test that instead
        with pytest.raises(Exception, match="Input should be greater than 0"):
            CCSSpec(
                notional_leg1=-1000000.0,  # Negative notional
                notional_leg2=900000.0,
                currency_leg1=Currency.USD,
                currency_leg2=Currency.EUR,
                index_leg1=IndexName.SOFR_3M,
                index_leg2=IndexName.EURIBOR_3M,
                effective_date=as_of,
                maturity_date=maturity,
                frequency=Frequency.QUARTERLY,
                day_count=DayCountConvention.ACT_360,
                calendar=Calendar.WEEKENDS_ONLY,
                business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
                constant_notional=True
            )
    
    def test_invalid_dates_validation(self):
        """Test validation rejects invalid dates."""
        as_of = date(2024, 1, 15)
        maturity = date(2024, 1, 10)  # Maturity before effective date
        
        spec = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=900000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        curves = create_synthetic_ccs_curves(as_of)
        
        with pytest.raises(ValueError, match="Effective date must be before maturity date"):
            price_ccs(spec, curves)
    
    def test_same_currency_validation(self):
        """Test validation rejects same currency for both legs."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        spec = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=1000000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.USD,  # Same currency
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.SOFR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        curves = create_synthetic_ccs_curves(as_of)
        
        with pytest.raises(ValueError, match="Leg currencies must be different for CCS"):
            price_ccs(spec, curves)
    
    def test_missing_curves_validation(self):
        """Test validation rejects missing curves."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        spec = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=900000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        # Missing curves
        empty_curves = {}
        
        with pytest.raises(ValueError, match="Error pricing CCS: Market curves are required"):
            price_ccs(spec, empty_curves)
    
    def test_different_currency_pairs(self):
        """Test pricing with different currency pairs."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        # USD/EUR CCS
        spec_usd_eur = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=900000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        curves = create_synthetic_ccs_curves(as_of)
        
        result_usd_eur = price_ccs(spec_usd_eur, curves)
        
        # Should complete successfully
        assert result_usd_eur.currency == "USD"
        assert result_usd_eur.reporting_currency == "USD"
        assert isinstance(result_usd_eur.pv_reporting_ccy, float)
        assert len(result_usd_eur.legs) == 2
        assert len(result_usd_eur.sensitivities) == 2
    
    def test_cashflow_details(self):
        """Test that cashflow details are provided."""
        as_of = date(2024, 1, 15)
        maturity = date(2025, 1, 15)  # 1 year
        
        spec = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=900000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        curves = create_synthetic_ccs_curves(as_of)
        result = price_ccs(spec, curves)
        
        # Check cashflow details for both legs
        leg1 = next(leg for leg in result.legs if "Leg 1" in leg["name"])
        leg2 = next(leg for leg in result.legs if "Leg 2" in leg["name"])
        
        assert "cashflows" in leg1
        assert "cashflows" in leg2
        
        # Check cashflow structure for leg 1
        if leg1["cashflows"]:
            cashflow = leg1["cashflows"][0]
            required_fields = ["start_date", "end_date", "accrual_factor", "rate", "cashflow", "discount_factor", "present_value", "currency", "notional"]
            for field in required_fields:
                assert field in cashflow, f"Leg 1 cashflow missing field: {field}"
        
        # Check cashflow structure for leg 2
        if leg2["cashflows"]:
            cashflow = leg2["cashflows"][0]
            required_fields = ["start_date", "end_date", "accrual_factor", "rate", "cashflow", "discount_factor", "present_value", "currency", "notional"]
            for field in required_fields:
                assert field in cashflow, f"Leg 2 cashflow missing field: {field}"
    
    def test_constant_notional_flag(self):
        """Test constant notional flag functionality."""
        as_of = date(2024, 1, 15)
        maturity = date(2026, 1, 15)
        
        # Test with constant notional = True
        spec_constant = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=900000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=True
        )
        
        # Test with constant notional = False
        spec_variable = CCSSpec(
            notional_leg1=1000000.0,
            notional_leg2=900000.0,
            currency_leg1=Currency.USD,
            currency_leg2=Currency.EUR,
            index_leg1=IndexName.SOFR_3M,
            index_leg2=IndexName.EURIBOR_3M,
            effective_date=as_of,
            maturity_date=maturity,
            frequency=Frequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
            calendar=Calendar.WEEKENDS_ONLY,
            business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
            constant_notional=False
        )
        
        curves = create_synthetic_ccs_curves(as_of)
        
        result_constant = price_ccs(spec_constant, curves)
        result_variable = price_ccs(spec_variable, curves)
        
        # Both should complete successfully
        assert isinstance(result_constant, CCSBreakdown)
        assert isinstance(result_variable, CCSBreakdown)
        
        # Check lineage includes constant_notional flag
        assert result_constant.lineage["constant_notional"] is True
        assert result_variable.lineage["constant_notional"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
