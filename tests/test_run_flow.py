import pytest
import asyncio
from datetime import date, datetime
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.app import app
from app.schemas.instrument import IRSSpec, CCSSpec
from app.schemas.run import RunRequest, RunStatus as RunStatusEnum
from app.core.curves.base import bootstrap_curves
from app.core.pricing.irs import price_irs
from app.core.pricing.ccs import price_ccs

client = TestClient(app)

# Sample test data
sample_irs_spec = IRSSpec(
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

sample_ccs_spec = CCSSpec(
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

class TestRunFlow:
    """Test the complete run flow from creation to completion"""
    
    def test_create_irs_run_success(self):
        """Test successful IRS run creation"""
        run_request = RunRequest(
            spec=sample_irs_spec,
            asOf=date(2024, 1, 1),
            marketDataProfile="default",
            approach=["discount_curve"]
        )
        
        response = client.post("/runs", json=run_request.dict())
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"
        assert "id" in data
        assert data["request"]["spec"]["notional"] == 1000000.0
        
        return data["id"]
    
    def test_create_ccs_run_success(self):
        """Test successful CCS run creation"""
        run_request = RunRequest(
            spec=sample_ccs_spec,
            asOf=date(2024, 1, 1),
            marketDataProfile="default",
            approach=["discount_curve", "fx_conversion"]
        )
        
        response = client.post("/runs", json=run_request.dict())
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"
        assert "id" in data
        assert data["request"]["spec"]["notionalCcy2"] == 850000.0
        
        return data["id"]
    
    def test_create_run_validation_error(self):
        """Test run creation with validation errors"""
        invalid_spec = IRSSpec(
            notional=-1000000.0,  # Invalid - negative notional
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
        
        run_request = RunRequest(
            spec=invalid_spec,
            asOf=date(2024, 1, 1),
            marketDataProfile="default",
            approach=["discount_curve"]
        )
        
        response = client.post("/runs", json=run_request.dict())
        
        assert response.status_code == 201  # Still returns 201 but with failed status
        data = response.json()
        assert data["status"] == "failed"
        assert "error_message" in data
        assert "Notional must be positive" in data["error_message"]
    
    def test_get_run_status(self):
        """Test getting run status"""
        # First create a run
        run_request = RunRequest(
            spec=sample_irs_spec,
            asOf=date(2024, 1, 1),
            marketDataProfile="default",
            approach=["discount_curve"]
        )
        
        create_response = client.post("/runs", json=run_request.dict())
        run_id = create_response.json()["id"]
        
        # Get run status
        response = client.get(f"/runs/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run_id
        assert data["status"] in ["queued", "running", "completed", "failed"]
    
    def test_get_run_not_found(self):
        """Test getting non-existent run"""
        response = client.get("/runs/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_run_processing_flow(self):
        """Test the complete run processing flow"""
        # This test would need to be run with actual async processing
        # For now, we'll test the components individually
        
        # Test curve bootstrapping
        curves = bootstrap_curves("default", date(2024, 1, 1))
        assert curves.market_data_profile == "default"
        assert curves.as_of_date == date(2024, 1, 1)
        assert len(curves.curves) > 0
        
        # Test IRS pricing
        result = price_irs(sample_irs_spec, curves)
        assert result.total_pv == 0.0  # Dummy implementation
        assert "fixed_leg_pv" in result.components
        assert "floating_leg_pv" in result.components
        assert result.market_data_hash.startswith("dummy_market_data")
        
        # Test CCS pricing
        result = price_ccs(sample_ccs_spec, curves)
        assert result.total_pv == 0.0  # Dummy implementation
        assert "ccy1_leg_pv" in result.components
        assert "ccy2_leg_pv" in result.components
        assert result.market_data_hash.startswith("dummy_market_data")
    
    def test_get_run_result_not_completed(self):
        """Test getting result for non-completed run"""
        # Create a run
        run_request = RunRequest(
            spec=sample_irs_spec,
            asOf=date(2024, 1, 1),
            marketDataProfile="default",
            approach=["discount_curve"]
        )
        
        create_response = client.post("/runs", json=run_request.dict())
        run_id = create_response.json()["id"]
        
        # Try to get result immediately (should fail)
        response = client.get(f"/runs/{run_id}/result")
        
        assert response.status_code == 400
        assert "not completed yet" in response.json()["detail"]
    
    def test_get_run_result_not_found(self):
        """Test getting result for non-existent run"""
        response = client.get("/runs/nonexistent-id/result")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

class TestPricingFunctions:
    """Test pricing functions directly"""
    
    def test_price_irs_dummy(self):
        """Test IRS pricing function returns dummy results"""
        curves = bootstrap_curves("default", date(2024, 1, 1))
        result = price_irs(sample_irs_spec, curves)
        
        assert result.total_pv == 0.0
        assert result.components["fixed_leg_pv"] == 0.0
        assert result.components["floating_leg_pv"] == 0.0
        assert result.components["net_pv"] == 0.0
        assert result.components["notional"] == 1000000.0
        assert result.components["currency"] == "USD"
        assert result.metadata["instrument_type"] == "IRS"
        assert result.metadata["pricing_model"] == "dummy_irs_pricer"
    
    def test_price_ccs_dummy(self):
        """Test CCS pricing function returns dummy results"""
        curves = bootstrap_curves("default", date(2024, 1, 1))
        result = price_ccs(sample_ccs_spec, curves)
        
        assert result.total_pv == 0.0
        assert result.components["ccy1_leg_pv"] == 0.0
        assert result.components["ccy2_leg_pv"] == 0.0
        assert result.components["fx_adjustment"] == 0.0
        assert result.components["net_pv"] == 0.0
        assert result.components["ccy1_notional"] == 1000000.0
        assert result.components["ccy2_notional"] == 850000.0
        assert result.components["ccy1"] == "USD"
        assert result.components["ccy2"] == "EUR"
        assert result.metadata["instrument_type"] == "CCS"
        assert result.metadata["pricing_model"] == "dummy_ccs_pricer"

class TestCurveBootstrapping:
    """Test curve bootstrapping functionality"""
    
    def test_bootstrap_curves_dummy(self):
        """Test curve bootstrapping returns dummy curves"""
        curves = bootstrap_curves("default", date(2024, 1, 1))
        
        assert curves.market_data_profile == "default"
        assert curves.as_of_date == date(2024, 1, 1)
        assert len(curves.curves) > 0
        assert len(curves.curve_refs) > 0
        
        # Check discount curve
        discount_curve = curves.get_curve("USD_DISCOUNT")
        assert discount_curve is not None
        assert len(discount_curve) > 0
        
        # Check forward curve
        forward_curve = curves.get_curve("USD_LIBOR_3M")
        assert forward_curve is not None
        assert len(forward_curve) > 0
    
    def test_curve_interpolation(self):
        """Test curve interpolation (placeholder)"""
        from app.core.curves.base import interpolate_curve, CurvePoint
        
        points = [
            CurvePoint(date=date(2024, 1, 1), rate=0.05, discount_factor=1.0),
            CurvePoint(date=date(2025, 1, 1), rate=0.06, discount_factor=0.95),
        ]
        
        # Test interpolation at existing point
        rate = interpolate_curve(points, date(2024, 1, 1))
        assert rate == 0.05
        
        # Test interpolation between points
        rate = interpolate_curve(points, date(2024, 7, 1))
        assert 0.05 <= rate <= 0.06
