"""
Mathematical invariants and validation for swap pricing
"""
from typing import List, Dict, Any, Tuple
from datetime import date
from dataclasses import dataclass

from ...schemas.instrument import IRSSpec
from ..schedules import PaymentSchedule, SchedulePeriod

@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    message: str
    details: Dict[str, Any] = None

def validate_accrual_sum_sanity(schedule: PaymentSchedule, tolerance: float = 1e-6) -> ValidationResult:
    """
    Validate that the sum of accrual periods equals the total term
    
    Args:
        schedule: Payment schedule to validate
        tolerance: Tolerance for floating point comparison
        
    Returns:
        ValidationResult indicating if the schedule is valid
    """
    total_accrual = sum(period.day_count_fraction for period in schedule.periods)
    expected_term = (schedule.termination_date - schedule.effective_date).days / 365.0
    
    difference = abs(total_accrual - expected_term)
    
    if difference <= tolerance:
        return ValidationResult(
            is_valid=True,
            message="Accrual sum validation passed",
            details={
                "total_accrual": total_accrual,
                "expected_term": expected_term,
                "difference": difference
            }
        )
    else:
        return ValidationResult(
            is_valid=False,
            message=f"Accrual sum validation failed: difference {difference:.6f} exceeds tolerance {tolerance}",
            details={
                "total_accrual": total_accrual,
                "expected_term": expected_term,
                "difference": difference,
                "tolerance": tolerance
            }
        )

def validate_par_check_atm_swap(spec: IRSSpec, fixed_leg_pv: float, floating_leg_pv: float, 
                               tolerance: float = 1e-6) -> ValidationResult:
    """
    Validate that an at-the-money swap has approximately zero net present value
    
    Args:
        spec: IRS specification
        fixed_leg_pv: Fixed leg present value
        floating_leg_pv: Floating leg present value
        tolerance: Tolerance for PV comparison
        
    Returns:
        ValidationResult indicating if the swap is at par
    """
    net_pv = floating_leg_pv - fixed_leg_pv
    
    # Check if this is an ATM swap (fixed rate close to market rate)
    # For now, we'll assume any swap with a reasonable fixed rate could be ATM
    is_atm = spec.fixedRate is not None and 0.01 <= spec.fixedRate <= 0.10
    
    if is_atm and abs(net_pv) <= tolerance:
        return ValidationResult(
            is_valid=True,
            message="ATM swap par check passed",
            details={
                "net_pv": net_pv,
                "fixed_leg_pv": fixed_leg_pv,
                "floating_leg_pv": floating_leg_pv,
                "tolerance": tolerance
            }
        )
    elif is_atm:
        return ValidationResult(
            is_valid=False,
            message=f"ATM swap par check failed: net PV {net_pv:.6f} exceeds tolerance {tolerance}",
            details={
                "net_pv": net_pv,
                "fixed_leg_pv": fixed_leg_pv,
                "floating_leg_pv": floating_leg_pv,
                "tolerance": tolerance
            }
        )
    else:
        return ValidationResult(
            is_valid=True,
            message="Non-ATM swap - par check not applicable",
            details={
                "net_pv": net_pv,
                "fixed_rate": spec.fixedRate,
                "is_atm": False
            }
        )

def validate_schedule_consistency(fixed_schedule: PaymentSchedule, 
                                floating_schedule: PaymentSchedule) -> ValidationResult:
    """
    Validate that fixed and floating leg schedules are consistent
    
    Args:
        fixed_schedule: Fixed leg payment schedule
        floating_schedule: Floating leg payment schedule
        
    Returns:
        ValidationResult indicating if schedules are consistent
    """
    issues = []
    
    # Check effective dates match
    if fixed_schedule.effective_date != floating_schedule.effective_date:
        issues.append(f"Effective dates don't match: {fixed_schedule.effective_date} vs {floating_schedule.effective_date}")
    
    # Check termination dates match
    if fixed_schedule.termination_date != floating_schedule.termination_date:
        issues.append(f"Termination dates don't match: {fixed_schedule.termination_date} vs {floating_schedule.termination_date}")
    
    # Check number of periods (may differ for different frequencies)
    if len(fixed_schedule.periods) != len(floating_schedule.periods):
        issues.append(f"Different number of periods: {len(fixed_schedule.periods)} vs {len(floating_schedule.periods)}")
    
    if issues:
        return ValidationResult(
            is_valid=False,
            message="Schedule consistency validation failed",
            details={"issues": issues}
        )
    else:
        return ValidationResult(
            is_valid=True,
            message="Schedule consistency validation passed",
            details={
                "fixed_periods": len(fixed_schedule.periods),
                "floating_periods": len(floating_schedule.periods)
            }
        )

def validate_positive_notional(spec: IRSSpec) -> ValidationResult:
    """Validate that notional amount is positive"""
    if spec.notional > 0:
        return ValidationResult(
            is_valid=True,
            message="Notional validation passed",
            details={"notional": spec.notional}
        )
    else:
        return ValidationResult(
            is_valid=False,
            message=f"Notional must be positive, got {spec.notional}",
            details={"notional": spec.notional}
        )

def validate_date_order(spec: IRSSpec) -> ValidationResult:
    """Validate that effective date is before maturity date"""
    if spec.effective < spec.maturity:
        return ValidationResult(
            is_valid=True,
            message="Date order validation passed",
            details={
                "effective_date": spec.effective,
                "maturity_date": spec.maturity
            }
        )
    else:
        return ValidationResult(
            is_valid=False,
            message=f"Effective date {spec.effective} must be before maturity date {spec.maturity}",
            details={
                "effective_date": spec.effective,
                "maturity_date": spec.maturity
            }
        )

def run_all_validations(spec: IRSSpec, fixed_leg_pv: float, floating_leg_pv: float,
                       fixed_schedule: PaymentSchedule, floating_schedule: PaymentSchedule) -> List[ValidationResult]:
    """
    Run all validation checks for an IRS
    
    Args:
        spec: IRS specification
        fixed_leg_pv: Fixed leg present value
        floating_leg_pv: Floating leg present value
        fixed_schedule: Fixed leg payment schedule
        floating_schedule: Floating leg payment schedule
        
    Returns:
        List of validation results
    """
    validations = [
        validate_positive_notional(spec),
        validate_date_order(spec),
        validate_accrual_sum_sanity(fixed_schedule),
        validate_accrual_sum_sanity(floating_schedule),
        validate_schedule_consistency(fixed_schedule, floating_schedule),
        validate_par_check_atm_swap(spec, fixed_leg_pv, floating_leg_pv)
    ]
    
    return validations

def get_validation_summary(validations: List[ValidationResult]) -> Dict[str, Any]:
    """
    Get a summary of validation results
    
    Args:
        validations: List of validation results
        
    Returns:
        Summary dictionary
    """
    total_validations = len(validations)
    passed_validations = sum(1 for v in validations if v.is_valid)
    failed_validations = total_validations - passed_validations
    
    return {
        "total_validations": total_validations,
        "passed_validations": passed_validations,
        "failed_validations": failed_validations,
        "all_passed": failed_validations == 0,
        "validation_details": [
            {
                "message": v.message,
                "is_valid": v.is_valid,
                "details": v.details
            }
            for v in validations
        ]
    }
