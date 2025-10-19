"""
Tests for sensitivity analysis functionality
"""
import pytest
from datetime import date
from app.risk.sensitivities import (
    RiskSensitivities, 
    validate_sensitivity_symmetry,
    create_custom_shock,
    ShockResult,
    SensitivityResults
)


class TestRiskSensitivities:
    """Test the RiskSensitivities class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.risk_engine = RiskSensitivities()
        
        # Sample curve data
        self.sample_curve = {
            "nodes": [
                {"tenor": "1M", "rate": 0.05},
                {"tenor": "3M", "rate": 0.052},
                {"tenor": "6M", "rate": 0.054},
                {"tenor": "1Y", "rate": 0.0575},
                {"tenor": "2Y", "rate": 0.06},
                {"tenor": "5Y", "rate": 0.0625},
                {"tenor": "10Y", "rate": 0.065},
                {"tenor": "30Y", "rate": 0.067}
            ],
            "currency": "USD",
            "curve_type": "OIS"
        }
    
    def test_parallel_bump(self):
        """Test parallel curve bump functionality"""
        # Test +1bp bump
        shocked_curve = self.risk_engine.parallel_bump(self.sample_curve, 1.0)
        
        # Check that all rates increased by 1bp
        for i, node in enumerate(shocked_curve["nodes"]):
            original_rate = self.sample_curve["nodes"][i]["rate"]
            expected_rate = original_rate + 0.0001  # 1bp in decimal
            assert abs(node["rate"] - expected_rate) < 1e-10
        
        # Check metadata
        assert shocked_curve["shock_applied"] == "parallel_1.0bp"
        assert shocked_curve["shock_type"] == "parallel"
        assert shocked_curve["shock_value"] == 1.0
    
    def test_parallel_bump_negative(self):
        """Test negative parallel curve bump"""
        shocked_curve = self.risk_engine.parallel_bump(self.sample_curve, -2.0)
        
        # Check that all rates decreased by 2bp
        for i, node in enumerate(shocked_curve["nodes"]):
            original_rate = self.sample_curve["nodes"][i]["rate"]
            expected_rate = original_rate - 0.0002  # 2bp in decimal
            assert abs(node["rate"] - expected_rate) < 1e-10
    
    def test_curve_twist(self):
        """Test curve twist functionality"""
        # Test steepening twist (short down, long up)
        twisted_curve = self.risk_engine.twist(self.sample_curve, -1.0, 1.0)
        
        # Check short end (1Y and below) decreased
        short_nodes = [node for node in twisted_curve["nodes"] if self.risk_engine._is_short_tenor(node["tenor"])]
        for node in short_nodes:
            original_node = next(n for n in self.sample_curve["nodes"] if n["tenor"] == node["tenor"])
            assert node["rate"] < original_node["rate"]
        
        # Check long end (10Y and above) increased
        long_nodes = [node for node in twisted_curve["nodes"] if self.risk_engine._is_long_tenor(node["tenor"])]
        for node in long_nodes:
            original_node = next(n for n in self.sample_curve["nodes"] if n["tenor"] == node["tenor"])
            assert node["rate"] > original_node["rate"]
    
    def test_fx_shock(self):
        """Test FX shock functionality"""
        # Test +1% FX shock
        original_rate = 1.2000  # USD/EUR
        shocked_rate = self.risk_engine.fx_shock(original_rate, 1.0)
        expected_rate = original_rate * 1.01
        assert abs(shocked_rate - expected_rate) < 1e-10
        
        # Test -2% FX shock
        shocked_rate = self.risk_engine.fx_shock(original_rate, -2.0)
        expected_rate = original_rate * 0.98
        assert abs(shocked_rate - expected_rate) < 1e-10
    
    def test_tenor_classification(self):
        """Test tenor classification for twist calculations"""
        # Test short tenors
        assert self.risk_engine._is_short_tenor("1M")
        assert self.risk_engine._is_short_tenor("1Y")
        assert self.risk_engine._is_short_tenor("2Y")
        assert not self.risk_engine._is_short_tenor("5Y")
        
        # Test long tenors
        assert self.risk_engine._is_long_tenor("10Y")
        assert self.risk_engine._is_long_tenor("30Y")
        assert not self.risk_engine._is_long_tenor("5Y")
    
    def test_tenor_to_years(self):
        """Test tenor to years conversion"""
        assert self.risk_engine._tenor_to_years("1M") == 1/12
        assert self.risk_engine._tenor_to_years("6M") == 0.5
        assert self.risk_engine._tenor_to_years("1Y") == 1.0
        assert self.risk_engine._tenor_to_years("5Y") == 5.0
    
    def test_interpolate_twist(self):
        """Test twist interpolation for middle tenors"""
        # Test interpolation between 2Y (-1bp) and 10Y (+1bp)
        interpolated_5y = self.risk_engine._interpolate_twist("5Y", -0.0001, 0.0001)
        
        # 5Y should be roughly in the middle, so close to 0
        assert abs(interpolated_5y) < 0.00005  # Less than 0.5bp
    
    def test_calculate_sensitivities_dummy(self):
        """Test sensitivity calculation with dummy pricing function"""
        curves = {"USD_OIS": self.sample_curve}
        
        results = self.risk_engine.calculate_sensitivities(
            run_id="test_run",
            original_pv=1000000.0,
            currency="USD",
            curves=curves,
            fx_rates=None,
            pricing_function=None  # Will use dummy results
        )
        
        # Check basic structure
        assert results.run_id == "test_run"
        assert results.original_pv == 1000000.0
        assert results.currency == "USD"
        assert len(results.shocks) > 0
        assert results.calculation_time >= 0
        
        # Check that we have expected shock types
        shock_names = [s.shock_name for s in results.shocks]
        assert "parallel_1bp_up" in shock_names
        assert "parallel_1bp_down" in shock_names
        assert "fx_1pct_up" in shock_names
        assert "fx_1pct_down" in shock_names
    
    def test_parallel_symmetry(self):
        """Test that parallel bumps show proper symmetry"""
        curves = {"USD_OIS": self.sample_curve}
        
        results = self.risk_engine.calculate_sensitivities(
            run_id="test_run",
            original_pv=1000000.0,
            currency="USD",
            curves=curves,
            fx_rates=None,
            pricing_function=None
        )
        
        # Find parallel bump results
        up_1bp = next((s for s in results.shocks if s.shock_name == "parallel_1bp_up"), None)
        down_1bp = next((s for s in results.shocks if s.shock_name == "parallel_1bp_down"), None)
        
        assert up_1bp is not None
        assert down_1bp is not None
        
        # Check symmetry (should be roughly opposite)
        assert up_1bp.pv_delta > 0  # Up bump should increase PV for pay-fixed
        assert down_1bp.pv_delta < 0  # Down bump should decrease PV for pay-fixed
        
        # Check magnitude is roughly equal
        symmetry_ratio = abs(up_1bp.pv_delta / down_1bp.pv_delta)
        assert 0.8 <= symmetry_ratio <= 1.2  # 20% tolerance


class TestValidation:
    """Test validation functions"""
    
    def test_validate_sensitivity_symmetry(self):
        """Test sensitivity symmetry validation"""
        # Create mock results with good symmetry
        up_shock = ShockResult(
            shock_name="parallel_1bp_up",
            shock_value=1.0,
            shock_unit="bp",
            pv_delta=1000.0,
            pv_delta_percent=0.1,
            leg_breakdown={"fixed_leg": 600.0, "floating_leg": 400.0},
            original_pv=1000000.0,
            shocked_pv=1001000.0
        )
        
        down_shock = ShockResult(
            shock_name="parallel_1bp_down",
            shock_value=-1.0,
            shock_unit="bp",
            pv_delta=-1000.0,
            pv_delta_percent=-0.1,
            leg_breakdown={"fixed_leg": -600.0, "floating_leg": -400.0},
            original_pv=1000000.0,
            shocked_pv=999000.0
        )
        
        results = SensitivityResults(
            run_id="test",
            original_pv=1000000.0,
            currency="USD",
            shocks=[up_shock, down_shock],
            calculation_time=1.0
        )
        
        validation = validate_sensitivity_symmetry(results)
        
        assert validation["parallel_1bp_symmetry"] is True
        assert validation["parallel_sign_sanity"] is True
    
    def test_validate_sensitivity_symmetry_poor(self):
        """Test validation with poor symmetry"""
        # Create mock results with poor symmetry
        up_shock = ShockResult(
            shock_name="parallel_1bp_up",
            shock_value=1.0,
            shock_unit="bp",
            pv_delta=1000.0,
            pv_delta_percent=0.1,
            leg_breakdown={"fixed_leg": 600.0, "floating_leg": 400.0},
            original_pv=1000000.0,
            shocked_pv=1001000.0
        )
        
        down_shock = ShockResult(
            shock_name="parallel_1bp_down",
            shock_value=-1.0,
            shock_unit="bp",
            pv_delta=-500.0,  # Poor symmetry
            pv_delta_percent=-0.05,
            leg_breakdown={"fixed_leg": -300.0, "floating_leg": -200.0},
            original_pv=1000000.0,
            shocked_pv=999500.0
        )
        
        results = SensitivityResults(
            run_id="test",
            original_pv=1000000.0,
            currency="USD",
            shocks=[up_shock, down_shock],
            calculation_time=1.0
        )
        
        validation = validate_sensitivity_symmetry(results)
        
        assert validation["parallel_1bp_symmetry"] is False  # Poor symmetry
        assert validation["parallel_sign_sanity"] is True  # Signs are correct


class TestCustomShocks:
    """Test custom shock creation"""
    
    def test_create_parallel_shock(self):
        """Test creating parallel shock"""
        shock = create_custom_shock("parallel", {"value": 5.0, "unit": "bp"})
        
        assert shock["type"] == "parallel"
        assert shock["value"] == 5.0
        assert shock["unit"] == "bp"
    
    def test_create_twist_shock(self):
        """Test creating twist shock"""
        shock = create_custom_shock("twist", {"short": -2.0, "long": 3.0, "unit": "bp"})
        
        assert shock["type"] == "twist"
        assert shock["short"] == -2.0
        assert shock["long"] == 3.0
        assert shock["unit"] == "bp"
    
    def test_create_fx_shock(self):
        """Test creating FX shock"""
        shock = create_custom_shock("fx", {"value": 2.5, "unit": "%"})
        
        assert shock["type"] == "fx"
        assert shock["value"] == 2.5
        assert shock["unit"] == "%"
    
    def test_create_invalid_shock(self):
        """Test creating invalid shock type"""
        with pytest.raises(ValueError):
            create_custom_shock("invalid", {})


if __name__ == "__main__":
    pytest.main([__file__])

