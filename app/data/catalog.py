import pandas as pd
import os
from typing import Dict, List, Optional
from pathlib import Path
from datetime import date

class QuoteData:
    """Container for quote data"""
    def __init__(self, tenor: str, rate: float, quote_type: str):
        self.tenor = tenor
        self.rate = rate
        self.quote_type = quote_type

class MarketDataCatalog:
    """Catalog for loading and managing market data"""
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Default to samples directory
            self.data_dir = Path(__file__).parent / "samples"
        else:
            self.data_dir = Path(data_dir)
    
    def load_quotes(self, filename: str) -> List[QuoteData]:
        """
        Load quotes from CSV file
        
        Args:
            filename: Name of the CSV file
            
        Returns:
            List of QuoteData objects
        """
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Quote file not found: {file_path}")
        
        df = pd.read_csv(file_path)
        
        quotes = []
        for _, row in df.iterrows():
            quote = QuoteData(
                tenor=row['tenor'],
                rate=row['rate'],
                quote_type=row['quote_type']
            )
            quotes.append(quote)
        
        return quotes
    
    def get_usd_ois_quotes(self) -> List[QuoteData]:
        """Get USD OIS quotes"""
        return self.load_quotes("usd_ois_quotes.csv")
    
    def get_usd_sofr_depos(self) -> List[QuoteData]:
        """Get USD SOFR deposit quotes"""
        return self.load_quotes("usd_sofr_depos.csv")
    
    def list_available_files(self) -> List[str]:
        """List all available quote files"""
        csv_files = list(self.data_dir.glob("*.csv"))
        return [f.name for f in csv_files]

# Global catalog instance
catalog = MarketDataCatalog()

