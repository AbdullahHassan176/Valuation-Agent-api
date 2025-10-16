from typing import List, Dict, Any
from dataclasses import dataclass
from .catalog import QuoteData

@dataclass
class ValidationResult:
    """Result of a validation check"""
    passed: bool
    message: str
    severity: str  # "error", "warning", "info"

class DataValidator:
    """Great Expectations-like data validation for market data"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
    
    def validate_quotes_continuity(self, quotes: List[QuoteData]) -> List[ValidationResult]:
        """
        Validate that quotes have no gaps in tenor coverage
        
        Args:
            quotes: List of quote data
            
        Returns:
            List of validation results
        """
        results = []
        
        if not quotes:
            results.append(ValidationResult(
                passed=False,
                message="No quotes provided",
                severity="error"
            ))
            return results
        
        # Check for required tenors
        required_tenors = ["ON", "1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y"]
        missing_tenors = []
        
        quote_tenors = {q.tenor for q in quotes}
        for tenor in required_tenors:
            if tenor not in quote_tenors:
                missing_tenors.append(tenor)
        
        if missing_tenors:
            results.append(ValidationResult(
                passed=False,
                message=f"Missing required tenors: {', '.join(missing_tenors)}",
                severity="error"
            ))
        
        # Check for duplicate tenors
        tenor_counts = {}
        for quote in quotes:
            tenor_counts[quote.tenor] = tenor_counts.get(quote.tenor, 0) + 1
        
        duplicates = [tenor for tenor, count in tenor_counts.items() if count > 1]
        if duplicates:
            results.append(ValidationResult(
                passed=False,
                message=f"Duplicate tenors found: {', '.join(duplicates)}",
                severity="error"
            ))
        
        return results
    
    def validate_rates_monotonicity(self, quotes: List[QuoteData]) -> List[ValidationResult]:
        """
        Validate that rates are monotonically increasing with tenor
        
        Args:
            quotes: List of quote data
            
        Returns:
            List of validation results
        """
        results = []
        
        if len(quotes) < 2:
            return results
        
        # Sort quotes by tenor (simple string sort for now)
        sorted_quotes = sorted(quotes, key=lambda q: q.tenor)
        
        for i in range(1, len(sorted_quotes)):
            prev_rate = sorted_quotes[i-1].rate
            curr_rate = sorted_quotes[i].rate
            
            if curr_rate < prev_rate:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Rate inversion: {sorted_quotes[i-1].tenor} ({prev_rate:.4f}) > {sorted_quotes[i].tenor} ({curr_rate:.4f})",
                    severity="error"
                ))
        
        return results
    
    def validate_rates_range(self, quotes: List[QuoteData], min_rate: float = 0.0, max_rate: float = 0.20) -> List[ValidationResult]:
        """
        Validate that rates are within reasonable range
        
        Args:
            quotes: List of quote data
            min_rate: Minimum acceptable rate
            max_rate: Maximum acceptable rate
            
        Returns:
            List of validation results
        """
        results = []
        
        for quote in quotes:
            if quote.rate < min_rate:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Rate too low: {quote.tenor} rate {quote.rate:.4f} < {min_rate:.4f}",
                    severity="error"
                ))
            elif quote.rate > max_rate:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Rate too high: {quote.tenor} rate {quote.rate:.4f} > {max_rate:.4f}",
                    severity="error"
                ))
        
        return results
    
    def validate_quote_types(self, quotes: List[QuoteData], expected_type: str) -> List[ValidationResult]:
        """
        Validate that all quotes have the expected type
        
        Args:
            quotes: List of quote data
            expected_type: Expected quote type
            
        Returns:
            List of validation results
        """
        results = []
        
        for quote in quotes:
            if quote.quote_type != expected_type:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Unexpected quote type: {quote.tenor} has type '{quote.quote_type}', expected '{expected_type}'",
                    severity="error"
                ))
        
        return results
    
    def validate_all(self, quotes: List[QuoteData], expected_type: str = "OIS") -> List[ValidationResult]:
        """
        Run all validation checks
        
        Args:
            quotes: List of quote data
            expected_type: Expected quote type
            
        Returns:
            List of all validation results
        """
        all_results = []
        
        # Run all validation checks
        all_results.extend(self.validate_quotes_continuity(quotes))
        all_results.extend(self.validate_rates_monotonicity(quotes))
        all_results.extend(self.validate_rates_range(quotes))
        all_results.extend(self.validate_quote_types(quotes, expected_type))
        
        return all_results
    
    def has_errors(self, results: List[ValidationResult]) -> bool:
        """Check if any validation results are errors"""
        return any(result.severity == "error" and not result.passed for result in results)
    
    def get_error_messages(self, results: List[ValidationResult]) -> List[str]:
        """Get all error messages"""
        return [result.message for result in results if result.severity == "error" and not result.passed]
