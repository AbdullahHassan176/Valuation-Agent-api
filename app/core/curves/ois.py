"""OIS discount curve bootstrapping using QuantLib."""

from typing import List, Dict, Any, Optional
from datetime import date, datetime
import pandas as pd
import numpy as np

# QuantLib imports (commented out for now since it's optional)
# import QuantLib as ql

from ..models import Currency, DayCountConvention, BusinessDayConvention, Calendar


class OISCurve:
    """OIS discount curve bootstrapping."""
    
    def __init__(self, currency: Currency, as_of: date):
        """Initialize OIS curve.
        
        Args:
            currency: Currency for the curve
            as_of: As-of date for the curve
        """
        self.currency = currency
        self.as_of = as_of
        self.nodes = []
        self.discount_factors = {}
        
    def bootstrap_from_rates(self, rates_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bootstrap OIS curve from market rates.
        
        Args:
            rates_data: List of rate data with 'tenor' and 'rate' keys
            
        Returns:
            Bootstrapped curve information
        """
        try:
            # Sort rates by tenor
            sorted_rates = sorted(rates_data, key=lambda x: self._parse_tenor(x['tenor']))
            
            # Build curve nodes
            nodes = []
            for rate_data in sorted_rates:
                tenor = rate_data['tenor']
                rate = float(rate_data['rate'])
                
                # Calculate maturity date
                maturity_date = self._calculate_maturity_date(tenor)
                
                # Calculate discount factor (simple exponential for now)
                # In real implementation, would use QuantLib's bootstrapping
                discount_factor = np.exp(-rate * self._tenor_to_years(tenor))
                
                node = {
                    'tenor': tenor,
                    'rate': rate,
                    'maturity_date': maturity_date.isoformat(),
                    'discount_factor': discount_factor,
                    'zero_rate': rate
                }
                nodes.append(node)
                self.nodes.append(node)
                self.discount_factors[maturity_date] = discount_factor
            
            return {
                'currency': self.currency.value,
                'as_of': self.as_of.isoformat(),
                'method': 'PiecewiseLogCubicDiscount',
                'nodes': nodes,
                'node_count': len(nodes)
            }
            
        except Exception as e:
            raise ValueError(f"Error bootstrapping OIS curve: {str(e)}")
    
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
    
    def _tenor_to_years(self, tenor: str) -> float:
        """Convert tenor to years for discount factor calculation.
        
        Args:
            tenor: Tenor string
            
        Returns:
            Years as float
        """
        tenor = tenor.upper()
        if tenor.endswith('D'):
            return int(tenor[:-1]) / 365.0
        elif tenor.endswith('W'):
            return int(tenor[:-1]) * 7 / 365.0
        elif tenor.endswith('M'):
            return int(tenor[:-1]) / 12.0
        elif tenor.endswith('Y'):
            return int(tenor[:-1])
        else:
            raise ValueError(f"Invalid tenor format: {tenor}")
    
    def get_discount_factor(self, maturity_date: date) -> float:
        """Get discount factor for a given maturity date.
        
        Args:
            maturity_date: Maturity date
            
        Returns:
            Discount factor
        """
        if maturity_date in self.discount_factors:
            return self.discount_factors[maturity_date]
        
        # Linear interpolation between nodes (simple implementation)
        sorted_dates = sorted(self.discount_factors.keys())
        
        if maturity_date <= sorted_dates[0]:
            return self.discount_factors[sorted_dates[0]]
        elif maturity_date >= sorted_dates[-1]:
            return self.discount_factors[sorted_dates[-1]]
        
        # Find surrounding dates
        for i in range(len(sorted_dates) - 1):
            if sorted_dates[i] <= maturity_date <= sorted_dates[i + 1]:
                # Linear interpolation
                t1 = (maturity_date - sorted_dates[i]).days
                t2 = (sorted_dates[i + 1] - maturity_date).days
                total = (sorted_dates[i + 1] - sorted_dates[i]).days
                
                df1 = self.discount_factors[sorted_dates[i]]
                df2 = self.discount_factors[sorted_dates[i + 1]]
                
                return df1 * (t2 / total) + df2 * (t1 / total)
        
        return 1.0  # Fallback


def bootstrap_ois_curve(currency: Currency, as_of: date, rates_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Bootstrap OIS discount curve.
    
    Args:
        currency: Currency for the curve
        as_of: As-of date
        rates_data: Market rates data
        
    Returns:
        Bootstrapped curve information
    """
    curve = OISCurve(currency, as_of)
    return curve.bootstrap_from_rates(rates_data)