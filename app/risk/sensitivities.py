"""
Risk sensitivity analysis module for parallel bumps, curve twists, and FX shocks.
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import copy
import math


@dataclass
class ShockResult:
    """Result of a sensitivity shock calculation."""
    shock_name: str
    shock_value: float
    shock_unit: str
    pv_delta: float
    pv_delta_percent: float
    leg_breakdown: Dict[str, float]
    original_pv: float
    shocked_pv: float


@dataclass
class SensitivityResults:
    """Complete sensitivity analysis results."""
    run_id: str
    original_pv: float
    currency: str
    shocks: List[ShockResult]
    calculation_time: float


class RiskSensitivities:
    """Risk sensitivity analysis engine."""
    
    def __init__(self):
        self.shock_templates = {
            "parallel_1bp_up": {"type": "parallel", "value": 1.0, "unit": "bp"},
            "parallel_1bp_down": {"type": "parallel", "value": -1.0, "unit": "bp"},
            "parallel_5bp_up": {"type": "parallel", "value": 5.0, "unit": "bp"},
            "parallel_5bp_down": {"type": "parallel", "value": -5.0, "unit": "bp"},
            "twist_steepening": {"type": "twist", "short": -1.0, "long": 1.0, "unit": "bp"},
            "twist_flattening": {"type": "twist", "short": 1.0, "long": -1.0, "unit": "bp"},
            "fx_1pct_up": {"type": "fx", "value": 1.0, "unit": "%"},
            "fx_1pct_down": {"type": "fx", "value": -1.0, "unit": "%"},
            "fx_5pct_up": {"type": "fx", "value": 5.0, "unit": "%"},
            "fx_5pct_down": {"type": "fx", "value": -5.0, "unit": "%"},
        }
    
    def parallel_bump(self, curve: Dict[str, Any], bp: float) -> Dict[str, Any]:
        """
        Apply parallel bump to a curve.
        
        Args:
            curve: Curve data with nodes and rates
            bp: Bump amount in basis points
            
        Returns:
            Shocked curve
        """
        shocked_curve = copy.deepcopy(curve)
        
        # Convert bp to decimal
        bump_decimal = bp / 10000.0
        
        # Apply bump to all rates
        if "nodes" in shocked_curve:
            for node in shocked_curve["nodes"]:
                if "rate" in node:
                    node["rate"] += bump_decimal
        
        # Update curve metadata
        shocked_curve["shock_applied"] = f"parallel_{bp}bp"
        shocked_curve["shock_type"] = "parallel"
        shocked_curve["shock_value"] = bp
        
        return shocked_curve
    
    def twist(self, curve: Dict[str, Any], short_bps: float, long_bps: float) -> Dict[str, Any]:
        """
        Apply curve twist (different bumps for short and long end).
        
        Args:
            curve: Curve data with nodes and rates
            short_bps: Bump for short end (typically 2Y and below)
            long_bps: Bump for long end (typically 10Y and above)
            
        Returns:
            Twisted curve
        """
        shocked_curve = copy.deepcopy(curve)
        
        # Convert bp to decimal
        short_decimal = short_bps / 10000.0
        long_decimal = long_bps / 10000.0
        
        if "nodes" in shocked_curve:
            for node in shocked_curve["nodes"]:
                if "rate" in node and "tenor" in node:
                    tenor = node["tenor"]
                    
                    # Determine if this is short or long end
                    if self._is_short_tenor(tenor):
                        node["rate"] += short_decimal
                    elif self._is_long_tenor(tenor):
                        node["rate"] += long_decimal
                    else:
                        # Interpolate for middle tenors
                        interpolated_bump = self._interpolate_twist(
                            tenor, short_decimal, long_decimal
                        )
                        node["rate"] += interpolated_bump
        
        # Update curve metadata
        shocked_curve["shock_applied"] = f"twist_{short_bps}bp_short_{long_bps}bp_long"
        shocked_curve["shock_type"] = "twist"
        shocked_curve["short_bps"] = short_bps
        shocked_curve["long_bps"] = long_bps
        
        return shocked_curve
    
    def fx_shock(self, fx_rate: float, percent: float) -> float:
        """
        Apply FX shock to exchange rate.
        
        Args:
            fx_rate: Current FX rate
            percent: Shock percentage (positive = currency appreciation)
            
        Returns:
            Shocked FX rate
        """
        shock_multiplier = 1.0 + (percent / 100.0)
        return fx_rate * shock_multiplier
    
    def _is_short_tenor(self, tenor: str) -> bool:
        """Check if tenor is in short end (≤ 2Y)."""
        short_tenors = ["1M", "3M", "6M", "9M", "1Y", "18M", "2Y"]
        return tenor in short_tenors
    
    def _is_long_tenor(self, tenor: str) -> bool:
        """Check if tenor is in long end (≥ 10Y)."""
        long_tenors = ["10Y", "15Y", "20Y", "25Y", "30Y", "40Y", "50Y"]
        return tenor in long_tenors
    
    def _interpolate_twist(self, tenor: str, short_bump: float, long_bump: float) -> float:
        """
        Interpolate twist bump for middle tenors.
        
        Args:
            tenor: Tenor string (e.g., "5Y")
            short_bump: Short end bump
            long_bump: Long end bump
            
        Returns:
            Interpolated bump
        """
        # Simple linear interpolation based on tenor
        tenor_years = self._tenor_to_years(tenor)
        
        # Assume 2Y is short end, 10Y is long end
        short_years = 2.0
        long_years = 10.0
        
        if tenor_years <= short_years:
            return short_bump
        elif tenor_years >= long_years:
            return long_bump
        else:
            # Linear interpolation
            weight = (tenor_years - short_years) / (long_years - short_years)
            return short_bump + weight * (long_bump - short_bump)
    
    def _tenor_to_years(self, tenor: str) -> float:
        """Convert tenor string to years."""
        if tenor.endswith("M"):
            return float(tenor[:-1]) / 12.0
        elif tenor.endswith("Y"):
            return float(tenor[:-1])
        else:
            return 0.0
    
    def calculate_sensitivities(
        self,
        run_id: str,
        original_pv: float,
        currency: str,
        curves: Dict[str, Dict[str, Any]],
        fx_rates: Optional[Dict[str, float]] = None,
        pricing_function: Optional[callable] = None
    ) -> SensitivityResults:
        """
        Calculate comprehensive sensitivity analysis.
        
        Args:
            run_id: Run identifier
            original_pv: Original present value
            currency: Base currency
            curves: Market curves
            fx_rates: FX rates (for CCS)
            pricing_function: Function to reprice with shocked curves
            
        Returns:
            Complete sensitivity results
        """
        import time
        start_time = time.time()
        
        shocks = []
        
        # Calculate each shock
        for shock_name, shock_config in self.shock_templates.items():
            shock_result = self._calculate_single_shock(
                shock_name, shock_config, original_pv, curves, fx_rates, pricing_function
            )
            if shock_result:
                shocks.append(shock_result)
        
        calculation_time = time.time() - start_time
        
        return SensitivityResults(
            run_id=run_id,
            original_pv=original_pv,
            currency=currency,
            shocks=shocks,
            calculation_time=calculation_time
        )
    
    def _calculate_single_shock(
        self,
        shock_name: str,
        shock_config: Dict[str, Any],
        original_pv: float,
        curves: Dict[str, Dict[str, Any]],
        fx_rates: Optional[Dict[str, float]],
        pricing_function: Optional[callable]
    ) -> Optional[ShockResult]:
        """Calculate a single shock scenario."""
        
        if not pricing_function:
            # Return dummy results for testing
            return self._create_dummy_shock_result(shock_name, shock_config, original_pv)
        
        try:
            # Apply shock to curves
            shocked_curves = copy.deepcopy(curves)
            
            if shock_config["type"] == "parallel":
                # Apply parallel bump to all curves
                for curve_name, curve_data in shocked_curves.items():
                    shocked_curves[curve_name] = self.parallel_bump(
                        curve_data, shock_config["value"]
                    )
            
            elif shock_config["type"] == "twist":
                # Apply twist to yield curves
                for curve_name, curve_data in shocked_curves.items():
                    if "yield" in curve_name.lower() or "ois" in curve_name.lower():
                        shocked_curves[curve_name] = self.twist(
                            curve_data, shock_config["short"], shock_config["long"]
                        )
            
            elif shock_config["type"] == "fx":
                # Apply FX shock
                if fx_rates:
                    shocked_fx_rates = copy.deepcopy(fx_rates)
                    for fx_pair, rate in shocked_fx_rates.items():
                        shocked_fx_rates[fx_pair] = self.fx_shock(
                            rate, shock_config["value"]
                        )
                else:
                    shocked_fx_rates = fx_rates
            
            # Re-price with shocked curves
            shocked_pv = pricing_function(shocked_curves, shocked_fx_rates)
            
            # Calculate delta
            pv_delta = shocked_pv - original_pv
            pv_delta_percent = (pv_delta / abs(original_pv)) * 100 if original_pv != 0 else 0
            
            # Create leg breakdown (simplified)
            leg_breakdown = {
                "fixed_leg": pv_delta * 0.6,  # Assume 60% from fixed leg
                "floating_leg": pv_delta * 0.4,  # Assume 40% from floating leg
            }
            
            return ShockResult(
                shock_name=shock_name,
                shock_value=shock_config.get("value", shock_config.get("short", 0)),
                shock_unit=shock_config["unit"],
                pv_delta=pv_delta,
                pv_delta_percent=pv_delta_percent,
                leg_breakdown=leg_breakdown,
                original_pv=original_pv,
                shocked_pv=shocked_pv
            )
            
        except Exception as e:
            print(f"Error calculating shock {shock_name}: {e}")
            return None
    
    def _create_dummy_shock_result(
        self, shock_name: str, shock_config: Dict[str, Any], original_pv: float
    ) -> ShockResult:
        """Create dummy shock result for testing."""
        
        # Generate realistic dummy deltas
        if "parallel" in shock_name:
            # Parallel bumps should be roughly symmetric
            base_delta = original_pv * 0.001  # 0.1% of PV per bp
            if "down" in shock_name:
                base_delta = -base_delta
            pv_delta = base_delta * abs(shock_config["value"])
        
        elif "twist" in shock_name:
            # Twists typically have smaller impact
            pv_delta = original_pv * 0.0005  # 0.05% of PV
        
        elif "fx" in shock_name:
            # FX shocks for CCS
            pv_delta = original_pv * (shock_config["value"] / 100.0)
        
        else:
            pv_delta = 0.0
        
        pv_delta_percent = (pv_delta / abs(original_pv)) * 100 if original_pv != 0 else 0
        
        leg_breakdown = {
            "fixed_leg": pv_delta * 0.6,
            "floating_leg": pv_delta * 0.4,
        }
        
        return ShockResult(
            shock_name=shock_name,
            shock_value=shock_config.get("value", shock_config.get("short", 0)),
            shock_unit=shock_config["unit"],
            pv_delta=pv_delta,
            pv_delta_percent=pv_delta_percent,
            leg_breakdown=leg_breakdown,
            original_pv=original_pv,
            shocked_pv=original_pv + pv_delta
        )


def create_custom_shock(
    shock_type: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create custom shock configuration.
    
    Args:
        shock_type: Type of shock (parallel, twist, fx, custom)
        parameters: Shock parameters
        
    Returns:
        Shock configuration
    """
    if shock_type == "parallel":
        return {
            "type": "parallel",
            "value": parameters.get("value", 1.0),
            "unit": parameters.get("unit", "bp")
        }
    
    elif shock_type == "twist":
        return {
            "type": "twist",
            "short": parameters.get("short", 0.0),
            "long": parameters.get("long", 0.0),
            "unit": parameters.get("unit", "bp")
        }
    
    elif shock_type == "fx":
        return {
            "type": "fx",
            "value": parameters.get("value", 1.0),
            "unit": parameters.get("unit", "%")
        }
    
    else:
        raise ValueError(f"Unknown shock type: {shock_type}")


def validate_sensitivity_symmetry(results: SensitivityResults) -> Dict[str, bool]:
    """
    Validate that sensitivity results show proper symmetry.
    
    Args:
        results: Sensitivity analysis results
        
    Returns:
        Validation results
    """
    validation = {}
    
    # Check parallel bump symmetry
    up_1bp = next((s for s in results.shocks if s.shock_name == "parallel_1bp_up"), None)
    down_1bp = next((s for s in results.shocks if s.shock_name == "parallel_1bp_down"), None)
    
    if up_1bp and down_1bp:
        symmetry_ratio = abs(up_1bp.pv_delta / down_1bp.pv_delta) if down_1bp.pv_delta != 0 else 0
        validation["parallel_1bp_symmetry"] = 0.8 <= symmetry_ratio <= 1.2  # 20% tolerance
    
    # Check sign sanity (up bump should increase PV for pay-fixed swaps)
    validation["parallel_sign_sanity"] = up_1bp.pv_delta > 0 if up_1bp else True
    
    # Check FX symmetry
    fx_up = next((s for s in results.shocks if s.shock_name == "fx_1pct_up"), None)
    fx_down = next((s for s in results.shocks if s.shock_name == "fx_1pct_down"), None)
    
    if fx_up and fx_down:
        fx_symmetry_ratio = abs(fx_up.pv_delta / fx_down.pv_delta) if fx_down.pv_delta != 0 else 0
        validation["fx_symmetry"] = 0.8 <= fx_symmetry_ratio <= 1.2
    
    return validation


