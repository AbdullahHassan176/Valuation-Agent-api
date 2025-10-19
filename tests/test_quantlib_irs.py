import pytest
from datetime import date, timedelta
from app.core.pricing.irs_quantlib import price_irs
from app.schemas.instrument import IRSSpec
from app.core.curves.base import CurveBundle


def test_irs_basic_pricing():
    """Test basic IRS pricing with QuantLib."""
    # Create test IRS specification
    spec = IRSSpec(
        notional=1000000.0,
        ccy="USD",
        effective=date.today(),
        maturity=date.today() + timedelta(days=1825),  # 5 years
        fixedRate=0.05,
        freqFixed="Semi-Annual",
        freqFloat="Quarterly",
        dcFixed="ACT/360",
        dcFloat="ACT/360",
        bdc="Following",
        calendar="USD"
    )
    
    # Create test curve bundle
    curves = CurveBundle(
        as_of_date=date.today(),
        market_data_profile="synthetic",
        curves={}
    )
    
    # Price the IRS
    result = price_irs(spec, curves)
    
    # Basic assertions
    assert result.total_pv is not None
    assert result.components["notional"] == 1000000.0
    assert result.components["fixed_rate"] == 0.05
    assert "pv01" in result.components
    assert result.metadata["pricing_model"] == "quantlib_vanilla_swap"
    assert result.metadata["quantlib_version"] is not None


def test_irs_pv01_consistency():
    """Test PV01 calculation consistency."""
    # Create test IRS specification
    spec = IRSSpec(
        notional=1000000.0,
        ccy="USD",
        effective=date.today(),
        maturity=date.today() + timedelta(days=1825),  # 5 years
        fixedRate=0.05,
        freqFixed="Semi-Annual",
        freqFloat="Quarterly",
        dcFixed="ACT/360",
        dcFloat="ACT/360",
        bdc="Following",
        calendar="USD"
    )
    
    # Create test curve bundle
    curves = CurveBundle(
        as_of_date=date.today(),
        market_data_profile="synthetic",
        curves={}
    )
    
    # Price the IRS
    result = price_irs(spec, curves)
    
    # Check PV01 is reasonable (should be positive for a receiver swap)
    pv01 = result.components["pv01"]
    assert pv01 is not None
    assert pv01 > 0  # Should be positive for receiver swap
    assert pv01 < 100000  # Should be reasonable magnitude


def test_irs_atm_pricing():
    """Test ATM IRS pricing (should be close to zero)."""
    # Create ATM IRS (fixed rate = forward rate)
    spec = IRSSpec(
        notional=1000000.0,
        ccy="USD",
        effective=date.today(),
        maturity=date.today() + timedelta(days=1825),  # 5 years
        fixedRate=0.05,  # ATM rate
        freqFixed="Semi-Annual",
        freqFloat="Quarterly",
        dcFixed="ACT/360",
        dcFloat="ACT/360",
        bdc="Following",
        calendar="USD"
    )
    
    # Create test curve bundle
    curves = CurveBundle(
        as_of_date=date.today(),
        market_data_profile="synthetic",
        curves={}
    )
    
    # Price the IRS
    result = price_irs(spec, curves)
    
    # ATM swap should have PV close to zero
    # Allow for some tolerance due to day count differences
    assert abs(result.total_pv) < 1000  # Should be small


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
