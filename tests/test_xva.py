"""
Tests for XVA (CVA/DVA/FVA) functionality
"""
import pytest
from datetime import date, datetime
from app.xva.simple import (
    compute_cva, compute_dva, compute_fva, compute_xva,
    create_synthetic_ee_grid, create_proxy_credit_curve,
    EEGrid, EEPoint, CreditCurve, CSAConfig, XVAConfig, XVAResults
)


class TestXVAComputations:
    """Test XVA computation functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create synthetic EE grid
        self.ee_grid = create_synthetic_ee_grid(
            start_date=date(2024, 1, 1),
            end_date=date(2026, 1, 1),
            frequency="monthly",
            peak_exposure=1000000.0,
            currency="USD"
        )
        
        # Create proxy credit curves
        self.counterparty_curve = create_proxy_credit_curve(
            name="Counterparty_AA",
            currency="USD",
            base_spread=100.0,
            curve_shape="flat"
        )
        
        self.own_curve = create_proxy_credit_curve(
            name="Own_AA",
            currency="USD",
            base_spread=80.0,
            curve_shape="flat"
        )
        
        self.funding_curve = create_proxy_credit_curve(
            name="Funding_Curve",
            currency="USD",
            base_spread=50.0,
            curve_shape="flat"
        )
    
    def test_compute_cva(self):
        """Test CVA computation"""
        cva = compute_cva(self.ee_grid, self.counterparty_curve)
        
        # CVA should be positive (cost to us)
        assert cva > 0
        
        # CVA should be reasonable relative to exposure
        max_exposure = max(point.expected_positive_exposure for point in self.ee_grid.points)
        assert cva < max_exposure * 0.1  # Less than 10% of max exposure
    
    def test_compute_dva(self):
        """Test DVA computation"""
        dva = compute_dva(self.ee_grid, self.own_curve)
        
        # DVA should be positive (benefit to us)
        assert dva > 0
        
        # DVA should be reasonable relative to exposure
        max_exposure = max(abs(point.expected_negative_exposure) for point in self.ee_grid.points)
        assert dva < max_exposure * 0.1
    
    def test_compute_fva(self):
        """Test FVA computation"""
        fva = compute_fva(self.ee_grid, self.funding_curve)
        
        # FVA should be positive (funding cost)
        assert fva > 0
        
        # FVA should be reasonable relative to exposure
        max_exposure = max(abs(point.expected_exposure) for point in self.ee_grid.points)
        assert fva < max_exposure * 0.05  # Less than 5% of max exposure
    
    def test_compute_fva_with_csa(self):
        """Test FVA computation with CSA benefits"""
        csa_config = CSAConfig(
            threshold=500000.0,
            minimum_transfer_amount=100000.0,
            rounding=1000.0,
            collateral_currency="USD",
            interest_rate=0.02,  # 2% interest on collateral
            posting_frequency="daily"
        )
        
        fva_with_csa = compute_fva(self.ee_grid, self.funding_curve, csa_config)
        fva_without_csa = compute_fva(self.ee_grid, self.funding_curve)
        
        # FVA with CSA should be lower (better) than without CSA
        assert fva_with_csa < fva_without_csa
    
    def test_compute_comprehensive_xva(self):
        """Test comprehensive XVA computation"""
        csa_config = CSAConfig(
            threshold=500000.0,
            minimum_transfer_amount=100000.0,
            rounding=1000.0,
            collateral_currency="USD",
            interest_rate=0.02,
            posting_frequency="daily"
        )
        
        xva_config = XVAConfig(
            compute_cva=True,
            compute_dva=True,
            compute_fva=True,
            counterparty_credit_curve=self.counterparty_curve,
            own_credit_curve=self.own_curve,
            funding_curve=self.funding_curve,
            csa_config=csa_config
        )
        
        results = compute_xva(self.ee_grid, xva_config)
        
        # Check results structure
        assert isinstance(results, XVAResults)
        assert results.cva > 0
        assert results.dva > 0
        assert results.fva > 0
        assert results.total_xva == results.cva + results.dva + results.fva
        assert results.currency == "USD"
        assert results.calculation_date == self.ee_grid.calculation_date
        
        # Check details
        assert 'cva' in results.details
        assert 'dva' in results.details
        assert 'fva' in results.details
    
    def test_xva_partial_configuration(self):
        """Test XVA with partial configuration"""
        # Test CVA only
        xva_config_cva = XVAConfig(
            compute_cva=True,
            compute_dva=False,
            compute_fva=False,
            counterparty_credit_curve=self.counterparty_curve
        )
        
        results_cva = compute_xva(self.ee_grid, xva_config_cva)
        assert results_cva.cva > 0
        assert results_cva.dva == 0.0
        assert results_cva.fva == 0.0
        assert results_cva.total_xva == results_cva.cva
        
        # Test DVA only
        xva_config_dva = XVAConfig(
            compute_cva=False,
            compute_dva=True,
            compute_fva=False,
            own_credit_curve=self.own_curve
        )
        
        results_dva = compute_xva(self.ee_grid, xva_config_dva)
        assert results_dva.cva == 0.0
        assert results_dva.dva > 0
        assert results_dva.fva == 0.0
        assert results_dva.total_xva == results_dva.dva


class TestSyntheticData:
    """Test synthetic data generation"""
    
    def test_create_synthetic_ee_grid(self):
        """Test synthetic EE grid creation"""
        ee_grid = create_synthetic_ee_grid(
            start_date=date(2024, 1, 1),
            end_date=date(2025, 1, 1),
            frequency="monthly",
            peak_exposure=500000.0,
            currency="EUR"
        )
        
        assert len(ee_grid.points) > 0
        assert ee_grid.currency == "EUR"
        assert ee_grid.calculation_date == date(2024, 1, 1)
        
        # Check that exposures are reasonable
        for point in ee_grid.points:
            assert abs(point.expected_exposure) <= 500000.0 * 1.2  # Allow some noise
            assert point.expected_positive_exposure >= 0
            assert point.expected_negative_exposure <= 0
    
    def test_create_proxy_credit_curve(self):
        """Test proxy credit curve creation"""
        curve = create_proxy_credit_curve(
            name="Test_Curve",
            currency="USD",
            base_spread=150.0,
            curve_shape="upward"
        )
        
        assert curve.name == "Test_Curve"
        assert curve.currency == "USD"
        assert len(curve.tenors) == len(curve.spreads)
        assert curve.recovery_rate == 0.4
        
        # Check upward sloping curve
        assert curve.spreads[0] == 150.0  # Base spread
        assert curve.spreads[-1] > curve.spreads[0]  # Upward sloping
    
    def test_credit_curve_shapes(self):
        """Test different credit curve shapes"""
        # Flat curve
        flat_curve = create_proxy_credit_curve(
            name="Flat",
            currency="USD",
            base_spread=100.0,
            curve_shape="flat"
        )
        assert all(spread == 100.0 for spread in flat_curve.spreads)
        
        # Upward curve
        upward_curve = create_proxy_credit_curve(
            name="Upward",
            currency="USD",
            base_spread=100.0,
            curve_shape="upward"
        )
        assert upward_curve.spreads[-1] > upward_curve.spreads[0]
        
        # Downward curve
        downward_curve = create_proxy_credit_curve(
            name="Downward",
            currency="USD",
            base_spread=100.0,
            curve_shape="downward"
        )
        assert downward_curve.spreads[-1] < downward_curve.spreads[0]


class TestXVAEdgeCases:
    """Test XVA edge cases and error handling"""
    
    def test_empty_ee_grid(self):
        """Test XVA with empty EE grid"""
        empty_grid = EEGrid(
            points=[],
            currency="USD",
            calculation_date=date(2024, 1, 1)
        )
        
        curve = create_proxy_credit_curve("Test", "USD", 100.0)
        
        cva = compute_cva(empty_grid, curve)
        dva = compute_dva(empty_grid, curve)
        fva = compute_fva(empty_grid, curve)
        
        assert cva == 0.0
        assert dva == 0.0
        assert fva == 0.0
    
    def test_zero_exposure(self):
        """Test XVA with zero exposure"""
        zero_grid = EEGrid(
            points=[
                EEPoint(
                    date=date(2024, 1, 1),
                    expected_exposure=0.0,
                    expected_positive_exposure=0.0,
                    expected_negative_exposure=0.0
                )
            ],
            currency="USD",
            calculation_date=date(2024, 1, 1)
        )
        
        curve = create_proxy_credit_curve("Test", "USD", 100.0)
        
        cva = compute_cva(zero_grid, curve)
        dva = compute_dva(zero_grid, curve)
        fva = compute_fva(zero_grid, curve)
        
        assert cva == 0.0
        assert dva == 0.0
        assert fva == 0.0
    
    def test_high_credit_spreads(self):
        """Test XVA with high credit spreads"""
        high_spread_curve = CreditCurve(
            name="High_Risk",
            currency="USD",
            tenors=["1Y", "2Y", "5Y"],
            spreads=[1000.0, 1200.0, 1500.0],  # Very high spreads
            recovery_rate=0.2  # Low recovery
        )
        
        ee_grid = create_synthetic_ee_grid(
            start_date=date(2024, 1, 1),
            end_date=date(2025, 1, 1),
            frequency="monthly",
            peak_exposure=1000000.0
        )
        
        cva = compute_cva(ee_grid, high_spread_curve)
        
        # High spreads should result in high CVA
        assert cva > 0
        # But should still be reasonable
        max_exposure = max(point.expected_positive_exposure for point in ee_grid.points)
        assert cva < max_exposure * 0.5  # Less than 50% of max exposure


if __name__ == "__main__":
    pytest.main([__file__])

