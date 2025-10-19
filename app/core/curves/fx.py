"""FX forward curve bootstrapping."""

from typing import List, Dict, Any
from datetime import date, datetime
import pandas as pd
import numpy as np

from ..models import Currency


class FXForwardCurve:
    """FX forward curve bootstrapping."""
    
    def __init__(self, base_currency: Currency, quote_currency: Currency, as_of: date):
        """Initialize FX forward curve.
        
        Args:
            base_currency: Base currency (e.g., USD)
            quote_currency: Quote currency (e.g., EUR)
            as_of: As-of date for the curve
        """
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.as_of = as_of
        self.spot_rate = 0.0
        self.forward_points = []
        self.forward_rates = {}
    
    def bootstrap_from_data(self, spot_rate: float, points_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bootstrap FX forward curve from spot and points data.
        
        Args:
            spot_rate: Current spot rate
            points_data: List of forward points data with 'tenor' and 'points' keys
            
        Returns:
            Bootstrapped FX forward curve information
        """
        try:
            self.spot_rate = spot_rate
            
            # Sort points by tenor
            sorted_points = sorted(points_data, key=lambda x: self._parse_tenor(x['tenor']))
            
            # Build forward curve nodes
            forward_nodes = []
            for points_data in sorted_points:
                tenor = points_data['tenor']
                points = float(points_data['points'])
                
                # Calculate maturity date
                maturity_date = self._calculate_maturity_date(tenor)
                
                # Calculate forward rate: forward = spot + points
                # Points are typically in price terms (not percentage)
                forward_rate = spot_rate + points
                
                forward_node = {
                    'tenor': tenor,
                    'spot_rate': spot_rate,
                    'points': points,
                    'forward_rate': forward_rate,
                    'maturity_date': maturity_date.isoformat()
                }
                forward_nodes.append(forward_node)
                self.forward_points.append(forward_node)
                self.forward_rates[maturity_date] = forward_rate
            
            return {
                'pair': f"{self.base_currency.value}/{self.quote_currency.value}",
                'as_of': self.as_of.isoformat(),
                'spot_rate': spot_rate,
                'method': 'SpotPlusPoints',
                'nodes': forward_nodes,
                'node_count': len(forward_nodes)
            }
            
        except Exception as e:
            raise ValueError(f"Error bootstrapping FX forward curve: {str(e)}")
    
    def _parse_tenor(self, tenor: str) -> int:
        """Parse tenor string to days for sorting.
        
        Args:
            tenor: Tenor string like '1M', '3M', '1Y', etc.
            
        Returns:
            Number of days
        """
        tenor = tenor.upper()
        if tenor.endswith('D'):
            return int(tenor[:-1])
        elif tenor.endswith('W'):
            return int(tenor[:-1]) * 7
        elif tenor.endswith('M'):
            return int(tenor[:-1]) * 30  # Approximate
        elif tenor.endswith('Y'):
            return int(tenor[:-1]) * 365  # Approximate
        else:
            raise ValueError(f"Invalid tenor format: {tenor}")
    
    def _calculate_maturity_date(self, tenor: str) -> date:
        """Calculate maturity date from tenor.
        
        Args:
            tenor: Tenor string
            
        Returns:
            Maturity date
        """
        tenor = tenor.upper()
        if tenor.endswith('D'):
            days = int(tenor[:-1])
        elif tenor.endswith('W'):
            days = int(tenor[:-1]) * 7
        elif tenor.endswith('M'):
            days = int(tenor[:-1]) * 30  # Approximate
        elif tenor.endswith('Y'):
            days = int(tenor[:-1]) * 365  # Approximate
        else:
            raise ValueError(f"Invalid tenor format: {tenor}")
        
        # Simple date addition (in real implementation, would use QuantLib calendars)
        from datetime import timedelta
        return self.as_of + timedelta(days=days)
    
    def get_forward_rate(self, maturity_date: date) -> float:
        """Get forward rate for a given maturity date.
        
        Args:
            maturity_date: Maturity date
            
        Returns:
            Forward rate
        """
        if maturity_date in self.forward_rates:
            return self.forward_rates[maturity_date]
        
        # Linear interpolation between nodes (simple implementation)
        sorted_dates = sorted(self.forward_rates.keys())
        
        if maturity_date <= sorted_dates[0]:
            return self.forward_rates[sorted_dates[0]]
        elif maturity_date >= sorted_dates[-1]:
            return self.forward_rates[sorted_dates[-1]]
        
        # Find surrounding dates
        for i in range(len(sorted_dates) - 1):
            if sorted_dates[i] <= maturity_date <= sorted_dates[i + 1]:
                # Linear interpolation
                t1 = (maturity_date - sorted_dates[i]).days
                t2 = (sorted_dates[i + 1] - maturity_date).days
                total = (sorted_dates[i + 1] - sorted_dates[i]).days
                
                rate1 = self.forward_rates[sorted_dates[i]]
                rate2 = self.forward_rates[sorted_dates[i + 1]]
                
                return rate1 * (t2 / total) + rate2 * (t1 / total)
        
        return self.spot_rate  # Fallback to spot rate


def bootstrap_fx_forward_curve(
    base_currency: Currency, 
    quote_currency: Currency, 
    as_of: date, 
    spot_rate: float, 
    points_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Bootstrap FX forward curve.
    
    Args:
        base_currency: Base currency
        quote_currency: Quote currency
        as_of: As-of date
        spot_rate: Current spot rate
        points_data: Forward points data
        
    Returns:
        Bootstrapped FX forward curve information
    """
    curve = FXForwardCurve(base_currency, quote_currency, as_of)
    return curve.bootstrap_from_data(spot_rate, points_data)
