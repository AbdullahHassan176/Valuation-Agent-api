"""Market data adapters for different providers."""

from typing import List, Dict, Any, Optional
from datetime import date
import pandas as pd
import os

from .types import MarketDataRequest, MarketDataResponse, RateData, FXPointsData, FXSpotData
from ..models import Currency


class SyntheticDataProvider:
    """Synthetic market data provider for testing."""
    
    def __init__(self, data_dir: str = "app/data/samples"):
        """Initialize synthetic data provider.
        
        Args:
            data_dir: Directory containing sample data files
        """
        self.data_dir = data_dir
    
    def get_ois_rates(self, currency: Currency, as_of: date) -> List[Dict[str, Any]]:
        """Get OIS rates for a currency.
        
        Args:
            currency: Currency
            as_of: As-of date
            
        Returns:
            List of rate data
        """
        try:
            # Load from CSV file
            filename = f"{currency.value.lower()}_ois.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(filepath):
                # Generate synthetic data if file doesn't exist
                return self._generate_synthetic_ois_rates(currency)
            
            df = pd.read_csv(filepath)
            rates = []
            
            for _, row in df.iterrows():
                rates.append({
                    'tenor': str(row['tenor']),
                    'rate': float(row['rate']),
                    'date': as_of.isoformat()
                })
            
            return rates
            
        except Exception as e:
            # Fallback to synthetic data
            return self._generate_synthetic_ois_rates(currency)
    
    def get_fx_spot(self, pair: str, as_of: date) -> Dict[str, Any]:
        """Get FX spot rate for a currency pair.
        
        Args:
            pair: Currency pair (e.g., 'USD/EUR')
            as_of: As-of date
            
        Returns:
            Spot rate data
        """
        try:
            # Load from CSV file
            filename = f"fx_{pair.replace('/', '_').lower()}.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(filepath):
                # Generate synthetic data if file doesn't exist
                return self._generate_synthetic_fx_spot(pair)
            
            df = pd.read_csv(filepath)
            # Get the most recent spot rate
            latest_row = df.iloc[-1]
            
            return {
                'pair': pair,
                'spot_rate': float(latest_row['spot']),
                'date': as_of.isoformat()
            }
            
        except Exception as e:
            # Fallback to synthetic data
            return self._generate_synthetic_fx_spot(pair)
    
    def get_fx_points(self, pair: str, as_of: date) -> List[Dict[str, Any]]:
        """Get FX forward points for a currency pair.
        
        Args:
            pair: Currency pair (e.g., 'USD/EUR')
            as_of: As-of date
            
        Returns:
            List of forward points data
        """
        try:
            # Load from CSV file
            filename = f"fx_{pair.replace('/', '_').lower()}.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(filepath):
                # Generate synthetic data if file doesn't exist
                return self._generate_synthetic_fx_points(pair)
            
            df = pd.read_csv(filepath)
            points = []
            
            for _, row in df.iterrows():
                points.append({
                    'tenor': str(row['tenor']),
                    'points': float(row['points']),
                    'date': as_of.isoformat()
                })
            
            return points
            
        except Exception as e:
            # Fallback to synthetic data
            return self._generate_synthetic_fx_points(pair)
    
    def _generate_synthetic_ois_rates(self, currency: Currency) -> List[Dict[str, Any]]:
        """Generate synthetic OIS rates for testing."""
        base_rates = {
            'USD': [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50],
            'EUR': [0.03, 0.08, 0.12, 0.16, 0.20, 0.24, 0.28, 0.32, 0.36, 0.40]
        }
        
        tenors = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y']
        rates = base_rates.get(currency.value, base_rates['USD'])
        
        return [
            {'tenor': tenor, 'rate': rate, 'date': date.today().isoformat()}
            for tenor, rate in zip(tenors, rates)
        ]
    
    def _generate_synthetic_fx_spot(self, pair: str) -> Dict[str, Any]:
        """Generate synthetic FX spot rate for testing."""
        spot_rates = {
            'USD/EUR': 0.85,
            'EUR/USD': 1.18,
            'USD/GBP': 0.78,
            'GBP/USD': 1.28
        }
        
        return {
            'pair': pair,
            'spot_rate': spot_rates.get(pair, 1.0),
            'date': date.today().isoformat()
        }
    
    def _generate_synthetic_fx_points(self, pair: str) -> List[Dict[str, Any]]:
        """Generate synthetic FX forward points for testing."""
        tenors = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y']
        base_points = [0.001, 0.003, 0.005, 0.008, 0.012, 0.015, 0.020]
        
        return [
            {'tenor': tenor, 'points': points, 'date': date.today().isoformat()}
            for tenor, points in zip(tenors, base_points)
        ]


class ECBDataProvider:
    """ECB data provider (stub implementation)."""
    
    def get_ois_rates(self, currency: Currency, as_of: date) -> List[Dict[str, Any]]:
        """Get OIS rates from ECB (stub)."""
        # TODO: Implement ECB API integration
        return []


class FREDDataProvider:
    """FRED data provider (stub implementation)."""
    
    def get_ois_rates(self, currency: Currency, as_of: date) -> List[Dict[str, Any]]:
        """Get OIS rates from FRED (stub)."""
        # TODO: Implement FRED API integration
        return []


class BOEDataProvider:
    """Bank of England data provider (stub implementation)."""
    
    def get_ois_rates(self, currency: Currency, as_of: date) -> List[Dict[str, Any]]:
        """Get OIS rates from BoE (stub)."""
        # TODO: Implement BoE API integration
        return []


def get_data_provider(provider: str) -> Any:
    """Get market data provider by name.
    
    Args:
        provider: Provider name ('synthetic', 'ecb', 'fred', 'boe')
        
    Returns:
        Data provider instance
    """
    providers = {
        'synthetic': SyntheticDataProvider(),
        'ecb': ECBDataProvider(),
        'fred': FREDDataProvider(),
        'boe': BOEDataProvider()
    }
    
    return providers.get(provider, providers['synthetic'])
