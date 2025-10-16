import pytest
from datetime import date
from app.validators.math import (
    validate_irs_spec, 
    validate_ccs_spec, 
    validate_calendar,
    validate_market_data_profile,
    validate_approach_list,
    ValidationError
)
from app.schemas.instrument import IRSSpec, CCSSpec

class TestIRSValidation:
    """Test IRS specification validation"""
    
    def test_valid_irs_spec(self):
        """Test valid IRS specification passes validation"""
        spec = IRSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING"
        )
        
        errors = validate_irs_spec(spec)
        assert len(errors) == 0
    
    def test_negative_notional(self):
        """Test negative notional fails validation"""
        spec = IRSSpec(
            notional=-1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING"
        )
        
        errors = validate_irs_spec(spec)
        assert len(errors) == 1
        assert "Notional must be positive" in errors[0]
    
    def test_invalid_currency(self):
        """Test invalid currency fails validation"""
        spec = IRSSpec(
            notional=1000000.0,
            ccy="US",  # Invalid - should be 3 characters
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING"
        )
        
        errors = validate_irs_spec(spec)
        assert len(errors) == 1
        assert "Currency must be 3 characters" in errors[0]
    
    def test_invalid_date_order(self):
        """Test effective date after maturity fails validation"""
        spec = IRSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2025, 1, 1),  # After maturity
            maturity=date(2024, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING"
        )
        
        errors = validate_irs_spec(spec)
        assert len(errors) == 1
        assert "Effective date" in errors[0] and "must be before maturity date" in errors[0]
    
    def test_negative_fixed_rate(self):
        """Test negative fixed rate fails validation"""
        spec = IRSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=-0.05,  # Negative rate
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING"
        )
        
        errors = validate_irs_spec(spec)
        assert len(errors) == 1
        assert "Fixed rate must be non-negative" in errors[0]
    
    def test_empty_floating_index(self):
        """Test empty floating index fails validation"""
        spec = IRSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="",  # Empty index
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING"
        )
        
        errors = validate_irs_spec(spec)
        assert len(errors) == 1
        assert "Floating index cannot be empty" in errors[0]
    
    def test_invalid_day_count_convention(self):
        """Test invalid day count convention fails validation"""
        spec = IRSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="INVALID",  # Invalid day count
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING"
        )
        
        errors = validate_irs_spec(spec)
        assert len(errors) == 1
        assert "Invalid fixed leg day count convention" in errors[0]

class TestCCSValidation:
    """Test CCS specification validation"""
    
    def test_valid_ccs_spec(self):
        """Test valid CCS specification passes validation"""
        spec = CCSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING",
            notionalCcy2=850000.0,
            ccy2="EUR",
            fxRate=0.85
        )
        
        errors = validate_ccs_spec(spec)
        assert len(errors) == 0
    
    def test_negative_second_notional(self):
        """Test negative second currency notional fails validation"""
        spec = CCSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING",
            notionalCcy2=-850000.0,  # Negative
            ccy2="EUR",
            fxRate=0.85
        )
        
        errors = validate_ccs_spec(spec)
        assert len(errors) == 1
        assert "Second currency notional must be positive" in errors[0]
    
    def test_same_currencies(self):
        """Test same currencies fails validation"""
        spec = CCSSpec(
            notional=1000000.0,
            ccy="USD",
            payFixed=True,
            fixedRate=0.05,
            floatIndex="USD-LIBOR-3M",
            effective=date(2024, 1, 1),
            maturity=date(2025, 1, 1),
            dcFixed="ACT/360",
            dcFloat="ACT/360",
            freqFixed="Q",
            freqFloat="Q",
            calendar="USD",
            bdc="FOLLOWING",
            notionalCcy2=1000000.0,
            ccy2="USD",  # Same as ccy
            fxRate=1.0
        )
        
        errors = validate_ccs_spec(spec)
        assert len(errors) == 1
        assert "Currencies must be different" in errors[0]

class TestUtilityValidators:
    """Test utility validation functions"""
    
    def test_validate_calendar(self):
        """Test calendar validation"""
        assert validate_calendar("USD") == True
        assert validate_calendar("EUR") == True
        assert validate_calendar("INVALID") == False
        assert validate_calendar("") == False
    
    def test_validate_market_data_profile(self):
        """Test market data profile validation"""
        assert validate_market_data_profile("default") == True
        assert validate_market_data_profile("live") == True
        assert validate_market_data_profile("test") == True
        assert validate_market_data_profile("invalid") == False
        assert validate_market_data_profile("") == False
    
    def test_validate_approach_list(self):
        """Test approach list validation"""
        # Valid approaches
        assert len(validate_approach_list(["discount_curve"])) == 0
        assert len(validate_approach_list(["discount_curve", "forward_curve"])) == 0
        
        # Empty list
        errors = validate_approach_list([])
        assert len(errors) == 1
        assert "At least one pricing approach must be specified" in errors[0]
        
        # Invalid approach
        errors = validate_approach_list(["invalid_approach"])
        assert len(errors) == 1
        assert "Invalid pricing approach" in errors[0]
