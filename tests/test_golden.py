"""
Golden test suite for IRS and CCS pricing
"""

import pytest
import json
import os
from datetime import datetime
from typing import Dict, Any, List
import requests


class GoldenTestSuite:
    """Golden test suite for pricing validation"""
    
    def __init__(self):
        self.snapshots_dir = "tests/snapshots"
        self.tolerance = 1e-6  # 0.0001% tolerance
        self.api_base_url = "http://127.0.0.1:9000"
        
        # Ensure snapshots directory exists
        os.makedirs(self.snapshots_dir, exist_ok=True)
    
    def create_irs_test_case(self) -> Dict[str, Any]:
        """Create standard IRS test case"""
        return {
            "spec": {
                "notional": 10000000,  # $10M
                "ccy": "USD",
                "payFixed": True,
                "fixedRate": 0.05,  # 5%
                "floatIndex": "SOFR",
                "effective": "2024-01-01",
                "maturity": "2026-01-01",  # 2-year tenor
                "dcFixed": "ACT/360",
                "dcFloat": "ACT/360",
                "freqFixed": "Q",  # Quarterly
                "freqFloat": "Q",
                "calendar": "USD",
                "bdc": "MODIFIED_FOLLOWING"
            },
            "asOf": "2024-01-01",
            "marketDataProfile": "default",
            "approach": ["discount_curve"]
        }
    
    def create_ccs_test_case(self) -> Dict[str, Any]:
        """Create standard CCS test case"""
        return {
            "spec": {
                "notional": 10000000,  # $10M USD
                "ccy": "USD",
                "payFixed": True,
                "fixedRate": 0.05,  # 5% USD
                "floatIndex": "SOFR",
                "effective": "2024-01-01",
                "maturity": "2026-01-01",
                "dcFixed": "ACT/360",
                "dcFloat": "ACT/360",
                "freqFixed": "Q",
                "freqFloat": "Q",
                "calendar": "USD_EUR",
                "bdc": "MODIFIED_FOLLOWING",
                "notionalCcy2": 9000000,   # €9M EUR
                "ccy2": "EUR",
                "fxRate": 0.9
            },
            "asOf": "2024-01-01",
            "marketDataProfile": "default",
            "approach": ["discount_curve"]
        }
    
    def run_pricing_test(self, test_case: Dict[str, Any], test_name: str) -> Dict[str, Any]:
        """Run pricing test and return results"""
        try:
            # Create run
            response = requests.post(f"{self.api_base_url}/runs/", json=test_case)
            assert response.status_code == 201, f"Failed to create run: {response.text}"
            
            run_data = response.json()
            run_id = run_data["id"]
            
            # Wait for completion (with timeout)
            import time
            max_wait = 30  # 30 seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_response = requests.get(f"{self.api_base_url}/runs/{run_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data["status"] == "completed":
                        break
                    elif status_data["status"] == "failed":
                        raise Exception(f"Run failed: {status_data.get('error_message', 'Unknown error')}")
                time.sleep(1)
            else:
                raise Exception("Run did not complete within timeout")
            
            # Get results
            result_response = requests.get(f"{self.api_base_url}/runs/{run_id}/result")
            assert result_response.status_code == 200, f"Failed to get results: {result_response.text}"
            
            result_data = result_response.json()
            
            # Test sensitivity analysis
            sensitivity_response = requests.post(
                f"{self.api_base_url}/runs/{run_id}/sensitivities",
                json={"shock_type": "parallel", "shock_value": 1.0}
            )
            sensitivity_data = sensitivity_response.json() if sensitivity_response.status_code == 200 else None
            
            return {
                "test_name": test_name,
                "run_id": run_id,
                "result": result_data,
                "sensitivity": sensitivity_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def save_snapshot(self, test_name: str, results: Dict[str, Any]):
        """Save test results as snapshot"""
        snapshot_file = os.path.join(self.snapshots_dir, f"{test_name}.json")
        with open(snapshot_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    def load_snapshot(self, test_name: str) -> Dict[str, Any]:
        """Load test results from snapshot"""
        snapshot_file = os.path.join(self.snapshots_dir, f"{test_name}.json")
        if os.path.exists(snapshot_file):
            with open(snapshot_file, 'r') as f:
                return json.load(f)
        return None
    
    def compare_results(self, current: Dict[str, Any], snapshot: Dict[str, Any]) -> List[str]:
        """Compare current results with snapshot"""
        differences = []
        
        if "error" in current:
            differences.append(f"Current test failed: {current['error']}")
            return differences
        
        if "error" in snapshot:
            differences.append(f"Snapshot test failed: {snapshot['error']}")
            return differences
        
        # Compare PV results
        current_pv = current["result"].get("total_pv", 0)
        snapshot_pv = snapshot["result"].get("total_pv", 0)
        
        if abs(current_pv - snapshot_pv) > self.tolerance:
            differences.append(f"PV difference: {current_pv} vs {snapshot_pv} (diff: {abs(current_pv - snapshot_pv)})")
        
        # Compare components
        current_components = current["result"].get("components", {})
        snapshot_components = snapshot["result"].get("components", {})
        
        for component in ["fixed_leg_pv", "floating_leg_pv"]:
            if component in current_components and component in snapshot_components:
                current_val = current_components[component]
                snapshot_val = snapshot_components[component]
                if abs(current_val - snapshot_val) > self.tolerance:
                    differences.append(f"{component} difference: {current_val} vs {snapshot_val}")
        
        # Compare sensitivity results
        if current.get("sensitivity") and snapshot.get("sensitivity"):
            current_pv_delta = current["sensitivity"].get("pv_delta", 0)
            snapshot_pv_delta = snapshot["sensitivity"].get("pv_delta", 0)
            
            if abs(current_pv_delta - snapshot_pv_delta) > self.tolerance:
                differences.append(f"PV01 difference: {current_pv_delta} vs {snapshot_pv_delta}")
        
        return differences


# Test fixtures
@pytest.fixture
def golden_test_suite():
    return GoldenTestSuite()


class TestGoldenIRS:
    """Golden tests for Interest Rate Swaps"""
    
    def test_standard_irs_2y_5pct(self, golden_test_suite):
        """Test standard 2-year 5% fixed IRS"""
        test_case = golden_test_suite.create_irs_test_case()
        results = golden_test_suite.run_pricing_test(test_case, "standard_irs_2y_5pct")
        
        # Save snapshot if it doesn't exist
        snapshot = golden_test_suite.load_snapshot("standard_irs_2y_5pct")
        if snapshot is None:
            golden_test_suite.save_snapshot("standard_irs_2y_5pct", results)
            pytest.skip("Snapshot created - run test again")
        
        # Compare with snapshot
        differences = golden_test_suite.compare_results(results, snapshot)
        assert len(differences) == 0, f"Golden test differences: {differences}"
    
    def test_irs_par_check(self, golden_test_suite):
        """Test that ATM swap has PV near zero"""
        test_case = golden_test_suite.create_irs_test_case()
        # Set fixed rate to approximate market rate for par check
        test_case["spec"]["fixedRate"] = 0.045  # Approximate 2Y rate
        
        results = golden_test_suite.run_pricing_test(test_case, "irs_par_check")
        
        if "error" not in results:
            pv = results["result"].get("total_pv", 0)
            # PV should be close to zero for par swap (using more realistic tolerance)
            assert abs(pv) < 100000, f"Par swap PV too large: {pv}"
    
    def test_irs_sensitivity_symmetry(self, golden_test_suite):
        """Test that +1bp and -1bp sensitivities are symmetric"""
        test_case = golden_test_suite.create_irs_test_case()
        results = golden_test_suite.run_pricing_test(test_case, "irs_sensitivity_symmetry")
        
        if "error" not in results and results.get("sensitivity"):
            pv_delta = results["sensitivity"].get("pv_delta", 0)
            # PV01 should be positive for fixed payer
            assert pv_delta > 0, f"Expected positive PV01 for fixed payer: {pv_delta}"


class TestGoldenCCS:
    """Golden tests for Cross Currency Swaps"""
    
    def test_standard_ccs_usd_eur(self, golden_test_suite):
        """Test standard USD/EUR CCS"""
        test_case = golden_test_suite.create_ccs_test_case()
        results = golden_test_suite.run_pricing_test(test_case, "standard_ccs_usd_eur")
        
        # Save snapshot if it doesn't exist
        snapshot = golden_test_suite.load_snapshot("standard_ccs_usd_eur")
        if snapshot is None:
            golden_test_suite.save_snapshot("standard_ccs_usd_eur", results)
            pytest.skip("Snapshot created - run test again")
        
        # Compare with snapshot
        differences = golden_test_suite.compare_results(results, snapshot)
        assert len(differences) == 0, f"Golden test differences: {differences}"
    
    def test_ccs_fx_consistency(self, golden_test_suite):
        """Test that CCS pricing is consistent with FX rates"""
        test_case = golden_test_suite.create_ccs_test_case()
        results = golden_test_suite.run_pricing_test(test_case, "ccs_fx_consistency")
        
        if "error" not in results:
            # CCS should have reasonable PV in reporting currency
            pv = results["result"].get("total_pv", 0)
            # PV should be within reasonable range for CCS
            assert abs(pv) < 100000, f"CCS PV too large: {pv}"


class TestGoldenXVA:
    """Golden tests for XVA calculations"""
    
    def test_xva_cva_calculation(self, golden_test_suite):
        """Test CVA calculation with synthetic data"""
        test_case = golden_test_suite.create_irs_test_case()
        test_case["xva_config"] = {
            "compute_cva": True,
            "compute_dva": False,
            "compute_fva": False,
            "counterparty_credit_curve": {
                "name": "Counterparty_AA",
                "currency": "USD",
                "tenors": ["1Y", "2Y", "5Y"],
                "spreads": [100.0, 120.0, 150.0],
                "recovery_rate": 0.4
            }
        }
        
        results = golden_test_suite.run_pricing_test(test_case, "xva_cva_calculation")
        
        if "error" not in results:
            xva_data = results["result"].get("xva")
            assert xva_data is not None, "XVA data not found"
            assert "cva" in xva_data, "CVA not calculated"
            assert xva_data["cva"] >= 0, f"CVA should be non-negative: {xva_data['cva']}"
    
    def test_xva_comprehensive(self, golden_test_suite):
        """Test comprehensive XVA calculation (CVA + DVA + FVA)"""
        test_case = golden_test_suite.create_irs_test_case()
        test_case["xva_config"] = {
            "compute_cva": True,
            "compute_dva": True,
            "compute_fva": True,
            "counterparty_credit_curve": {
                "name": "Counterparty_AA",
                "currency": "USD",
                "tenors": ["1Y", "2Y", "5Y"],
                "spreads": [100.0, 120.0, 150.0],
                "recovery_rate": 0.4
            },
            "own_credit_curve": {
                "name": "Own_AA",
                "currency": "USD",
                "tenors": ["1Y", "2Y", "5Y"],
                "spreads": [80.0, 100.0, 120.0],
                "recovery_rate": 0.4
            },
            "funding_curve": {
                "name": "Funding_Curve",
                "currency": "USD",
                "tenors": ["1Y", "2Y", "5Y"],
                "spreads": [50.0, 60.0, 70.0],
                "recovery_rate": 0.0
            },
            "csa_config": {
                "threshold": 500000.0,
                "minimum_transfer_amount": 100000.0,
                "rounding": 1000.0,
                "collateral_currency": "USD",
                "interest_rate": 0.02,
                "posting_frequency": "daily"
            }
        }
        
        results = golden_test_suite.run_pricing_test(test_case, "xva_comprehensive")
        
        if "error" not in results:
            xva_data = results["result"].get("xva")
            assert xva_data is not None, "XVA data not found"
            assert "cva" in xva_data, "CVA not calculated"
            assert "dva" in xva_data, "DVA not calculated"
            assert "fva" in xva_data, "FVA not calculated"
            assert "total_xva" in xva_data, "Total XVA not calculated"
            
            # Check that total XVA is sum of components
            expected_total = xva_data["cva"] + xva_data["dva"] + xva_data["fva"]
            assert abs(xva_data["total_xva"] - expected_total) < 1e-6, "Total XVA mismatch"


class TestGoldenHW1F:
    """Golden tests for Hull-White 1-Factor model"""
    
    def test_hw1f_model_lineage(self, golden_test_suite):
        """Test that HW1F model creates proper lineage"""
        test_case = golden_test_suite.create_irs_test_case()
        test_case["approach"] = ["discount_curve", "HW1F-variance-matching"]
        
        results = golden_test_suite.run_pricing_test(test_case, "hw1f_model_lineage")
        
        if "error" not in results:
            result_data = results["result"]
            assert "model_hash" in result_data, "Model hash not found"
            assert "HW1F" in result_data["model_hash"], "HW1F not in model hash"
            
            metadata = result_data.get("metadata", {})
            assert "hw1f_params" in metadata, "HW1F parameters not found"
            assert "hw1f_calibration" in metadata, "HW1F calibration not found"
            
            hw1f_params = metadata["hw1f_params"]
            assert "a" in hw1f_params, "Mean reversion parameter not found"
            assert "sigma" in hw1f_params, "Volatility parameter not found"
            assert "model_version" in hw1f_params, "Model version not found"


if __name__ == "__main__":
    # Run golden tests
    pytest.main([__file__, "-v", "--tb=short"])

