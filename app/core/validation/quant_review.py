"""
Quant Review Guide Implementation
Comprehensive validation system for valuation runs based on Quant Review Guide
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum
import json

class ValidationStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"

@dataclass
class ValidationCheck:
    """Individual validation check result"""
    id: str
    name: str
    status: ValidationStatus
    message: str
    details: Dict[str, Any]
    category: str
    priority: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"

@dataclass
class ValidationReport:
    """Complete validation report for a valuation run"""
    run_id: str
    timestamp: datetime
    overall_status: ValidationStatus
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    checks: List[ValidationCheck]
    summary: Dict[str, Any]

class QuantReviewValidator:
    """Main validator implementing Quant Review Guide checklist"""
    
    def __init__(self):
        self.checks = []
    
    def validate_run_summary(self, run_data: Dict[str, Any]) -> List[ValidationCheck]:
        """Validate Run_Summary sheet data"""
        checks = []
        
        # Run ID validation
        run_id = run_data.get('run_id', '')
        if run_id and len(run_id) > 5:
            checks.append(ValidationCheck(
                id="run_id_format",
                name="Run ID Format",
                status=ValidationStatus.PASSED,
                message="Run ID format is valid",
                details={"run_id": run_id},
                category="Run_Summary",
                priority="HIGH"
            ))
        else:
            checks.append(ValidationCheck(
                id="run_id_format",
                name="Run ID Format",
                status=ValidationStatus.FAILED,
                message="Run ID is missing or invalid format",
                details={"run_id": run_id},
                category="Run_Summary",
                priority="HIGH"
            ))
        
        # Instrument details validation
        instrument_type = run_data.get('instrument_type', '')
        if instrument_type in ['IRS', 'CCS', 'FRA', 'SWAP']:
            checks.append(ValidationCheck(
                id="instrument_type",
                name="Instrument Type",
                status=ValidationStatus.PASSED,
                message="Valid instrument type",
                details={"instrument_type": instrument_type},
                category="Run_Summary",
                priority="CRITICAL"
            ))
        else:
            checks.append(ValidationCheck(
                id="instrument_type",
                name="Instrument Type",
                status=ValidationStatus.FAILED,
                message="Invalid or missing instrument type",
                details={"instrument_type": instrument_type},
                category="Run_Summary",
                priority="CRITICAL"
            ))
        
        # Valuation date validation
        valuation_date = run_data.get('valuation_date')
        if valuation_date:
            try:
                val_date = datetime.strptime(valuation_date, '%Y-%m-%d').date()
                if val_date <= date.today():
                    checks.append(ValidationCheck(
                        id="valuation_date",
                        name="Valuation Date",
                        status=ValidationStatus.PASSED,
                        message="Valuation date is valid",
                        details={"valuation_date": valuation_date},
                        category="Run_Summary",
                        priority="CRITICAL"
                    ))
                else:
                    checks.append(ValidationCheck(
                        id="valuation_date",
                        name="Valuation Date",
                        status=ValidationStatus.WARNING,
                        message="Valuation date is in the future",
                        details={"valuation_date": valuation_date},
                        category="Run_Summary",
                        priority="HIGH"
                    ))
            except ValueError:
                checks.append(ValidationCheck(
                    id="valuation_date",
                    name="Valuation Date",
                    status=ValidationStatus.FAILED,
                    message="Invalid date format",
                    details={"valuation_date": valuation_date},
                    category="Run_Summary",
                    priority="CRITICAL"
                ))
        else:
            checks.append(ValidationCheck(
                id="valuation_date",
                name="Valuation Date",
                status=ValidationStatus.FAILED,
                message="Valuation date is missing",
                details={},
                category="Run_Summary",
                priority="CRITICAL"
            ))
        
        # Model version validation
        model_version = run_data.get('model_version', '')
        if model_version and len(model_version) > 0:
            checks.append(ValidationCheck(
                id="model_version",
                name="Model Version",
                status=ValidationStatus.PASSED,
                message="Model version is specified",
                details={"model_version": model_version},
                category="Run_Summary",
                priority="MEDIUM"
            ))
        else:
            checks.append(ValidationCheck(
                id="model_version",
                name="Model Version",
                status=ValidationStatus.WARNING,
                message="Model version not specified",
                details={},
                category="Run_Summary",
                priority="MEDIUM"
            ))
        
        return checks
    
    def validate_instrument_summary(self, instrument_data: Dict[str, Any]) -> List[ValidationCheck]:
        """Validate Instrument_Summary sheet data"""
        checks = []
        
        # Notional amount validation
        notional = instrument_data.get('notional', 0)
        if notional > 0:
            checks.append(ValidationCheck(
                id="notional_amount",
                name="Notional Amount",
                status=ValidationStatus.PASSED,
                message="Notional amount is positive",
                details={"notional": notional},
                category="Instrument_Summary",
                priority="CRITICAL"
            ))
        else:
            checks.append(ValidationCheck(
                id="notional_amount",
                name="Notional Amount",
                status=ValidationStatus.FAILED,
                message="Notional amount must be positive",
                details={"notional": notional},
                category="Instrument_Summary",
                priority="CRITICAL"
            ))
        
        # Currency validation
        currency = instrument_data.get('currency', '')
        valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']
        if currency in valid_currencies:
            checks.append(ValidationCheck(
                id="currency_code",
                name="Currency Code",
                status=ValidationStatus.PASSED,
                message="Valid currency code",
                details={"currency": currency},
                category="Instrument_Summary",
                priority="HIGH"
            ))
        else:
            checks.append(ValidationCheck(
                id="currency_code",
                name="Currency Code",
                status=ValidationStatus.FAILED,
                message="Invalid or missing currency code",
                details={"currency": currency},
                category="Instrument_Summary",
                priority="HIGH"
            ))
        
        # Rate conventions validation
        fixed_rate = instrument_data.get('fixed_rate')
        if fixed_rate is not None:
            if 0 <= fixed_rate <= 1:  # Assuming rates are in decimal form
                checks.append(ValidationCheck(
                    id="fixed_rate_range",
                    name="Fixed Rate Range",
                    status=ValidationStatus.PASSED,
                    message="Fixed rate is within reasonable range",
                    details={"fixed_rate": fixed_rate},
                    category="Instrument_Summary",
                    priority="HIGH"
                ))
            else:
                checks.append(ValidationCheck(
                    id="fixed_rate_range",
                    name="Fixed Rate Range",
                    status=ValidationStatus.WARNING,
                    message="Fixed rate seems unusual",
                    details={"fixed_rate": fixed_rate},
                    category="Instrument_Summary",
                    priority="MEDIUM"
                ))
        
        # Schedule parameters validation
        frequency = instrument_data.get('frequency', '')
        valid_frequencies = ['1M', '3M', '6M', '12M', '1Y', '2Y', '5Y', '10Y']
        if frequency in valid_frequencies:
            checks.append(ValidationCheck(
                id="frequency_valid",
                name="Payment Frequency",
                status=ValidationStatus.PASSED,
                message="Valid payment frequency",
                details={"frequency": frequency},
                category="Instrument_Summary",
                priority="HIGH"
            ))
        else:
            checks.append(ValidationCheck(
                id="frequency_valid",
                name="Payment Frequency",
                status=ValidationStatus.FAILED,
                message="Invalid payment frequency",
                details={"frequency": frequency},
                category="Instrument_Summary",
                priority="HIGH"
            ))
        
        return checks
    
    def validate_data_sources(self, data_sources: Dict[str, Any]) -> List[ValidationCheck]:
        """Validate Data_Sources sheet data"""
        checks = []
        
        # Market data completeness
        required_curves = ['OIS', 'LIBOR', 'SOFR']
        available_curves = data_sources.get('available_curves', [])
        
        missing_curves = [curve for curve in required_curves if curve not in available_curves]
        if not missing_curves:
            checks.append(ValidationCheck(
                id="curve_completeness",
                name="Curve Completeness",
                status=ValidationStatus.PASSED,
                message="All required curves are available",
                details={"available_curves": available_curves},
                category="Data_Sources",
                priority="CRITICAL"
            ))
        else:
            checks.append(ValidationCheck(
                id="curve_completeness",
                name="Curve Completeness",
                status=ValidationStatus.FAILED,
                message=f"Missing required curves: {missing_curves}",
                details={"available_curves": available_curves, "missing_curves": missing_curves},
                category="Data_Sources",
                priority="CRITICAL"
            ))
        
        # Data timestamps validation
        data_timestamp = data_sources.get('data_timestamp')
        if data_timestamp:
            try:
                timestamp = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
                age_hours = (datetime.now() - timestamp).total_seconds() / 3600
                if age_hours <= 24:
                    checks.append(ValidationCheck(
                        id="data_freshness",
                        name="Data Freshness",
                        status=ValidationStatus.PASSED,
                        message="Market data is current",
                        details={"age_hours": age_hours, "timestamp": data_timestamp},
                        category="Data_Sources",
                        priority="HIGH"
                    ))
                elif age_hours <= 72:
                    checks.append(ValidationCheck(
                        id="data_freshness",
                        name="Data Freshness",
                        status=ValidationStatus.WARNING,
                        message="Market data is somewhat stale",
                        details={"age_hours": age_hours, "timestamp": data_timestamp},
                        category="Data_Sources",
                        priority="MEDIUM"
                    ))
                else:
                    checks.append(ValidationCheck(
                        id="data_freshness",
                        name="Data Freshness",
                        status=ValidationStatus.FAILED,
                        message="Market data is too stale",
                        details={"age_hours": age_hours, "timestamp": data_timestamp},
                        category="Data_Sources",
                        priority="HIGH"
                    ))
            except ValueError:
                checks.append(ValidationCheck(
                    id="data_freshness",
                    name="Data Freshness",
                    status=ValidationStatus.FAILED,
                    message="Invalid timestamp format",
                    details={"timestamp": data_timestamp},
                    category="Data_Sources",
                    priority="HIGH"
                ))
        
        # Interpolation methods validation
        interpolation_method = data_sources.get('interpolation_method', '')
        valid_methods = ['linear', 'cubic', 'spline', 'log_linear']
        if interpolation_method in valid_methods:
            checks.append(ValidationCheck(
                id="interpolation_method",
                name="Interpolation Method",
                status=ValidationStatus.PASSED,
                message="Valid interpolation method",
                details={"method": interpolation_method},
                category="Data_Sources",
                priority="MEDIUM"
            ))
        else:
            checks.append(ValidationCheck(
                id="interpolation_method",
                name="Interpolation Method",
                status=ValidationStatus.WARNING,
                message="Interpolation method not specified or unknown",
                details={"method": interpolation_method},
                category="Data_Sources",
                priority="MEDIUM"
            ))
        
        return checks
    
    def validate_curves(self, curves_data: Dict[str, Any]) -> List[ValidationCheck]:
        """Validate Curves sheet data"""
        checks = []
        
        # Discount curve validation
        discount_curves = curves_data.get('discount_curves', {})
        for currency, curve_data in discount_curves.items():
            if 'rates' in curve_data and len(curve_data['rates']) > 0:
                rates = curve_data['rates']
                if all(rate > 0 for rate in rates):
                    checks.append(ValidationCheck(
                        id=f"discount_curve_{currency}",
                        name=f"Discount Curve - {currency}",
                        status=ValidationStatus.PASSED,
                        message="Discount curve has positive rates",
                        details={"currency": currency, "rate_count": len(rates)},
                        category="Curves",
                        priority="CRITICAL"
                    ))
                else:
                    checks.append(ValidationCheck(
                        id=f"discount_curve_{currency}",
                        name=f"Discount Curve - {currency}",
                        status=ValidationStatus.FAILED,
                        message="Discount curve has non-positive rates",
                        details={"currency": currency, "rates": rates},
                        category="Curves",
                        priority="CRITICAL"
                    ))
            else:
                checks.append(ValidationCheck(
                    id=f"discount_curve_{currency}",
                    name=f"Discount Curve - {currency}",
                    status=ValidationStatus.FAILED,
                    message="Discount curve data is missing",
                    details={"currency": currency},
                    category="Curves",
                    priority="CRITICAL"
                ))
        
        # Forward curve validation
        forward_curves = curves_data.get('forward_curves', {})
        for currency, curve_data in forward_curves.items():
            if 'rates' in curve_data and len(curve_data['rates']) > 0:
                rates = curve_data['rates']
                if all(rate >= 0 for rate in rates):
                    checks.append(ValidationCheck(
                        id=f"forward_curve_{currency}",
                        name=f"Forward Curve - {currency}",
                        status=ValidationStatus.PASSED,
                        message="Forward curve has non-negative rates",
                        details={"currency": currency, "rate_count": len(rates)},
                        category="Curves",
                        priority="HIGH"
                    ))
                else:
                    checks.append(ValidationCheck(
                        id=f"forward_curve_{currency}",
                        name=f"Forward Curve - {currency}",
                        status=ValidationStatus.WARNING,
                        message="Forward curve has negative rates",
                        details={"currency": currency, "rates": rates},
                        category="Curves",
                        priority="MEDIUM"
                    ))
        
        # Curve shape validation
        for currency, curve_data in discount_curves.items():
            if 'rates' in curve_data and len(curve_data['rates']) > 1:
                rates = curve_data['rates']
                # Check for reasonable curve shape (monotonic or slight inversion)
                is_monotonic = all(rates[i] <= rates[i+1] for i in range(len(rates)-1))
                has_inversion = any(rates[i] > rates[i+1] for i in range(len(rates)-1))
                
                if is_monotonic or (has_inversion and max(rates) - min(rates) < 0.05):
                    checks.append(ValidationCheck(
                        id=f"curve_shape_{currency}",
                        name=f"Curve Shape - {currency}",
                        status=ValidationStatus.PASSED,
                        message="Curve shape is reasonable",
                        details={"currency": currency, "is_monotonic": is_monotonic},
                        category="Curves",
                        priority="MEDIUM"
                    ))
                else:
                    checks.append(ValidationCheck(
                        id=f"curve_shape_{currency}",
                        name=f"Curve Shape - {currency}",
                        status=ValidationStatus.WARNING,
                        message="Curve shape seems unusual",
                        details={"currency": currency, "rates": rates},
                        category="Curves",
                        priority="MEDIUM"
                    ))
        
        return checks
    
    def validate_calculations(self, calculation_data: Dict[str, Any]) -> List[ValidationCheck]:
        """Validate calculation results"""
        checks = []
        
        # Present value validation
        present_value = calculation_data.get('present_value', 0)
        notional = calculation_data.get('notional', 1)
        
        if abs(present_value) <= notional * 0.1:  # PV should be reasonable relative to notional
            checks.append(ValidationCheck(
                id="present_value_reasonable",
                name="Present Value Reasonableness",
                status=ValidationStatus.PASSED,
                message="Present value is within reasonable range",
                details={"present_value": present_value, "notional": notional},
                category="Calculations",
                priority="CRITICAL"
            ))
        else:
            checks.append(ValidationCheck(
                id="present_value_reasonable",
                name="Present Value Reasonableness",
                status=ValidationStatus.WARNING,
                message="Present value seems unusually large",
                details={"present_value": present_value, "notional": notional},
                category="Calculations",
                priority="HIGH"
            ))
        
        # Payment schedule validation
        payment_schedule = calculation_data.get('payment_schedule', [])
        if payment_schedule:
            total_payments = sum(payment.get('amount', 0) for payment in payment_schedule)
            if abs(total_payments) > 0:
                checks.append(ValidationCheck(
                    id="payment_schedule",
                    name="Payment Schedule",
                    status=ValidationStatus.PASSED,
                    message="Payment schedule has non-zero total",
                    details={"total_payments": total_payments, "payment_count": len(payment_schedule)},
                    category="Calculations",
                    priority="HIGH"
                ))
            else:
                checks.append(ValidationCheck(
                    id="payment_schedule",
                    name="Payment Schedule",
                    status=ValidationStatus.WARNING,
                    message="Payment schedule total is zero",
                    details={"total_payments": total_payments},
                    category="Calculations",
                    priority="MEDIUM"
                ))
        
        # Risk metrics validation
        pv01 = calculation_data.get('pv01', 0)
        if abs(pv01) > 0:
            checks.append(ValidationCheck(
                id="pv01_calculation",
                name="PV01 Calculation",
                status=ValidationStatus.PASSED,
                message="PV01 is calculated and non-zero",
                details={"pv01": pv01},
                category="Calculations",
                priority="HIGH"
            ))
        else:
            checks.append(ValidationCheck(
                id="pv01_calculation",
                name="PV01 Calculation",
                status=ValidationStatus.WARNING,
                message="PV01 is zero or not calculated",
                details={"pv01": pv01},
                category="Calculations",
                priority="MEDIUM"
            ))
        
        return checks
    
    def validate_ifrs_compliance(self, ifrs_data: Dict[str, Any]) -> List[ValidationCheck]:
        """Validate IFRS-13 compliance"""
        checks = []
        
        # Hierarchy level validation
        hierarchy_level = ifrs_data.get('hierarchy_level')
        if hierarchy_level in [1, 2, 3]:
            checks.append(ValidationCheck(
                id="hierarchy_level",
                name="IFRS Hierarchy Level",
                status=ValidationStatus.PASSED,
                message="Valid hierarchy level assigned",
                details={"hierarchy_level": hierarchy_level},
                category="IFRS_Compliance",
                priority="CRITICAL"
            ))
        else:
            checks.append(ValidationCheck(
                id="hierarchy_level",
                name="IFRS Hierarchy Level",
                status=ValidationStatus.FAILED,
                message="Invalid or missing hierarchy level",
                details={"hierarchy_level": hierarchy_level},
                category="IFRS_Compliance",
                priority="CRITICAL"
            ))
        
        # Data observability validation
        observability = ifrs_data.get('data_observability', '')
        if observability in ['high', 'medium', 'low']:
            checks.append(ValidationCheck(
                id="data_observability",
                name="Data Observability",
                status=ValidationStatus.PASSED,
                message="Data observability is assessed",
                details={"observability": observability},
                category="IFRS_Compliance",
                priority="HIGH"
            ))
        else:
            checks.append(ValidationCheck(
                id="data_observability",
                name="Data Observability",
                status=ValidationStatus.WARNING,
                message="Data observability not assessed",
                details={"observability": observability},
                category="IFRS_Compliance",
                priority="MEDIUM"
            ))
        
        # Day-1 P&L validation
        day1_pnl = ifrs_data.get('day1_pnl', 0)
        notional = ifrs_data.get('notional', 1)
        pnl_ratio = abs(day1_pnl) / notional if notional > 0 else 0
        
        if pnl_ratio <= 0.01:  # Day-1 P&L should be small relative to notional
            checks.append(ValidationCheck(
                id="day1_pnl",
                name="Day-1 P&L",
                status=ValidationStatus.PASSED,
                message="Day-1 P&L is within tolerance",
                details={"day1_pnl": day1_pnl, "pnl_ratio": pnl_ratio},
                category="IFRS_Compliance",
                priority="HIGH"
            ))
        else:
            checks.append(ValidationCheck(
                id="day1_pnl",
                name="Day-1 P&L",
                status=ValidationStatus.WARNING,
                message="Day-1 P&L is large relative to notional",
                details={"day1_pnl": day1_pnl, "pnl_ratio": pnl_ratio},
                category="IFRS_Compliance",
                priority="MEDIUM"
            ))
        
        return checks
    
    def generate_validation_report(self, run_data: Dict[str, Any]) -> ValidationReport:
        """Generate comprehensive validation report"""
        all_checks = []
        
        # Run all validation categories
        all_checks.extend(self.validate_run_summary(run_data.get('run_summary', {})))
        all_checks.extend(self.validate_instrument_summary(run_data.get('instrument_summary', {})))
        all_checks.extend(self.validate_data_sources(run_data.get('data_sources', {})))
        all_checks.extend(self.validate_curves(run_data.get('curves', {})))
        all_checks.extend(self.validate_calculations(run_data.get('calculations', {})))
        all_checks.extend(self.validate_ifrs_compliance(run_data.get('ifrs_compliance', {})))
        
        # Calculate summary statistics
        total_checks = len(all_checks)
        passed_checks = sum(1 for check in all_checks if check.status == ValidationStatus.PASSED)
        failed_checks = sum(1 for check in all_checks if check.status == ValidationStatus.FAILED)
        warning_checks = sum(1 for check in all_checks if check.status == ValidationStatus.WARNING)
        
        # Determine overall status
        if failed_checks == 0:
            overall_status = ValidationStatus.PASSED
        elif failed_checks <= 2:
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.FAILED
        
        # Create summary
        summary = {
            "validation_timestamp": datetime.now().isoformat(),
            "run_id": run_data.get('run_id', 'unknown'),
            "critical_failures": [check for check in all_checks 
                               if check.status == ValidationStatus.FAILED and check.priority == "CRITICAL"],
            "high_priority_warnings": [check for check in all_checks 
                                     if check.status == ValidationStatus.WARNING and check.priority == "HIGH"],
            "category_summary": {
                category: {
                    "total": len([c for c in all_checks if c.category == category]),
                    "passed": len([c for c in all_checks if c.category == category and c.status == ValidationStatus.PASSED]),
                    "failed": len([c for c in all_checks if c.category == category and c.status == ValidationStatus.FAILED]),
                    "warnings": len([c for c in all_checks if c.category == category and c.status == ValidationStatus.WARNING])
                }
                for category in set(check.category for check in all_checks)
            }
        }
        
        return ValidationReport(
            run_id=run_data.get('run_id', 'unknown'),
            timestamp=datetime.now(),
            overall_status=overall_status,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            checks=all_checks,
            summary=summary
        )

def validate_valuation_run(run_data: Dict[str, Any]) -> ValidationReport:
    """Main function to validate a valuation run"""
    validator = QuantReviewValidator()
    return validator.generate_validation_report(run_data)
