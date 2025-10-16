from typing import List, Optional
from datetime import date
from ..schemas.instrument import IRSSpec, CCSSpec

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_irs_spec(spec: IRSSpec) -> List[str]:
    """
    Validate IRS specification
    
    Args:
        spec: IRS specification to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check notional is positive
    if spec.notional <= 0:
        errors.append(f"Notional must be positive, got {spec.notional}")
    
    # Check currency is valid (basic check)
    if len(spec.ccy) != 3:
        errors.append(f"Currency must be 3 characters, got '{spec.ccy}'")
    
    # Check dates are in correct order
    if spec.effective >= spec.maturity:
        errors.append(f"Effective date ({spec.effective}) must be before maturity date ({spec.maturity})")
    
    # Check fixed rate is non-negative if provided
    if spec.fixedRate is not None and spec.fixedRate < 0:
        errors.append(f"Fixed rate must be non-negative, got {spec.fixedRate}")
    
    # Check floating index is not empty
    if not spec.floatIndex or not spec.floatIndex.strip():
        errors.append("Floating index cannot be empty")
    
    # Check day count conventions are valid
    valid_dc = ["ACT/360", "ACT/365", "30/360", "ACT/ACT"]
    if spec.dcFixed not in valid_dc:
        errors.append(f"Invalid fixed leg day count convention: {spec.dcFixed}")
    if spec.dcFloat not in valid_dc:
        errors.append(f"Invalid floating leg day count convention: {spec.dcFloat}")
    
    # Check frequencies are valid
    valid_freq = ["D", "W", "M", "Q", "S", "A"]
    if spec.freqFixed not in valid_freq:
        errors.append(f"Invalid fixed leg frequency: {spec.freqFixed}")
    if spec.freqFloat not in valid_freq:
        errors.append(f"Invalid floating leg frequency: {spec.freqFloat}")
    
    # Check business day convention is valid
    valid_bdc = ["FOLLOWING", "MODIFIED_FOLLOWING", "PRECEDING", "MODIFIED_PRECEDING"]
    if spec.bdc not in valid_bdc:
        errors.append(f"Invalid business day convention: {spec.bdc}")
    
    # Check calendar is not empty
    if not spec.calendar or not spec.calendar.strip():
        errors.append("Calendar cannot be empty")
    
    return errors

def validate_ccs_spec(spec: CCSSpec) -> List[str]:
    """
    Validate CCS specification
    
    Args:
        spec: CCS specification to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Run IRS validation first (CCS inherits from IRS)
    irs_errors = validate_irs_spec(spec)
    errors.extend(irs_errors)
    
    # Check second currency notional is positive
    if spec.notionalCcy2 <= 0:
        errors.append(f"Second currency notional must be positive, got {spec.notionalCcy2}")
    
    # Check second currency is valid
    if len(spec.ccy2) != 3:
        errors.append(f"Second currency must be 3 characters, got '{spec.ccy2}'")
    
    # Check currencies are different
    if spec.ccy == spec.ccy2:
        errors.append("Currencies must be different for cross-currency swap")
    
    # Check FX rate is positive if provided
    if spec.fxRate is not None and spec.fxRate <= 0:
        errors.append(f"FX rate must be positive, got {spec.fxRate}")
    
    return errors

def validate_calendar(calendar: str) -> bool:
    """
    Validate calendar identifier (placeholder implementation)
    
    In a real implementation, this would check against a database
    of valid calendar identifiers.
    
    Args:
        calendar: Calendar identifier to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Placeholder - accept common currency codes
    valid_calendars = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
    return calendar.upper() in valid_calendars

def validate_business_dates(effective_date: date, maturity_date: date, calendar: str) -> List[str]:
    """
    Validate business dates (placeholder implementation)
    
    In a real implementation, this would:
    1. Check if dates are business days
    2. Apply business day conventions
    3. Validate against holiday calendars
    
    Args:
        effective_date: Effective date
        maturity_date: Maturity date
        calendar: Calendar identifier
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Basic checks
    if effective_date >= maturity_date:
        errors.append(f"Effective date ({effective_date}) must be before maturity date ({maturity_date})")
    
    # Check calendar is valid
    if not validate_calendar(calendar):
        errors.append(f"Invalid calendar: {calendar}")
    
    # Placeholder for business day checks
    # In real implementation, would check against holiday calendar
    
    return errors

def validate_market_data_profile(profile: str) -> bool:
    """
    Validate market data profile (placeholder implementation)
    
    Args:
        profile: Market data profile identifier
        
    Returns:
        True if valid, False otherwise
    """
    # Placeholder - accept common profiles
    valid_profiles = ["default", "live", "test", "historical"]
    return profile.lower() in valid_profiles

def validate_approach_list(approaches: List[str]) -> List[str]:
    """
    Validate pricing approaches
    
    Args:
        approaches: List of pricing approaches
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not approaches:
        errors.append("At least one pricing approach must be specified")
    
    # Valid approaches (placeholder)
    valid_approaches = [
        "discount_curve",
        "forward_curve", 
        "basis_adjustment",
        "fx_conversion",
        "overnight_index",
        "cross_currency_basis"
    ]
    
    for approach in approaches:
        if approach not in valid_approaches:
            errors.append(f"Invalid pricing approach: {approach}")
    
    return errors
