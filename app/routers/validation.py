"""
Validation API endpoints for Quant Review Guide implementation
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

from ..core.validation.quant_review import (
    validate_valuation_run, 
    ValidationReport, 
    ValidationCheck, 
    ValidationStatus
)

router = APIRouter(prefix="/validation", tags=["validation"])

class ValidationRequest(BaseModel):
    """Request model for validation"""
    run_data: Dict[str, Any]

class ValidationResponse(BaseModel):
    """Response model for validation results"""
    run_id: str
    timestamp: str
    overall_status: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    checks: List[Dict[str, Any]]
    summary: Dict[str, Any]

class ValidationCheckResponse(BaseModel):
    """Response model for individual validation check"""
    id: str
    name: str
    status: str
    message: str
    details: Dict[str, Any]
    category: str
    priority: str

@router.post("/validate-run", response_model=ValidationResponse)
async def validate_run(request: ValidationRequest):
    """
    Validate a valuation run using Quant Review Guide checklist
    
    This endpoint performs comprehensive validation of a valuation run
    including run summary, instrument details, data sources, curves,
    calculations, and IFRS compliance.
    """
    try:
        # Perform validation
        report = validate_valuation_run(request.run_data)
        
        # Convert to response format
        checks_data = []
        for check in report.checks:
            checks_data.append({
                "id": check.id,
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "details": check.details,
                "category": check.category,
                "priority": check.priority
            })
        
        return ValidationResponse(
            run_id=report.run_id,
            timestamp=report.timestamp.isoformat(),
            overall_status=report.overall_status.value,
            total_checks=report.total_checks,
            passed_checks=report.passed_checks,
            failed_checks=report.failed_checks,
            warning_checks=report.warning_checks,
            checks=checks_data,
            summary=report.summary
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )

@router.get("/validation-categories")
async def get_validation_categories():
    """
    Get list of validation categories and their descriptions
    """
    categories = {
        "Run_Summary": {
            "description": "Run identification and basic parameters",
            "checks": [
                "Run ID format validation",
                "Instrument type validation", 
                "Valuation date validation",
                "Model version validation"
            ]
        },
        "Instrument_Summary": {
            "description": "Trade details and parameters",
            "checks": [
                "Notional amount validation",
                "Currency code validation",
                "Rate conventions validation",
                "Schedule parameters validation"
            ]
        },
        "Data_Sources": {
            "description": "Market data and curve information",
            "checks": [
                "Curve completeness validation",
                "Data freshness validation",
                "Interpolation method validation"
            ]
        },
        "Curves": {
            "description": "Discount and forward curve details",
            "checks": [
                "Discount curve validation",
                "Forward curve validation",
                "Curve shape validation"
            ]
        },
        "Calculations": {
            "description": "Valuation calculations and results",
            "checks": [
                "Present value reasonableness",
                "Payment schedule validation",
                "Risk metrics validation"
            ]
        },
        "IFRS_Compliance": {
            "description": "IFRS-13 compliance requirements",
            "checks": [
                "Hierarchy level validation",
                "Data observability validation",
                "Day-1 P&L validation"
            ]
        }
    }
    
    return {
        "categories": categories,
        "total_categories": len(categories),
        "description": "Quant Review Guide validation categories"
    }

@router.get("/validation-priorities")
async def get_validation_priorities():
    """
    Get validation priority levels and their descriptions
    """
    priorities = {
        "CRITICAL": {
            "description": "Must pass for run to be considered valid",
            "examples": ["Run ID format", "Instrument type", "Notional amount", "Hierarchy level"]
        },
        "HIGH": {
            "description": "Important for data quality and accuracy",
            "examples": ["Currency validation", "Data freshness", "Present value reasonableness"]
        },
        "MEDIUM": {
            "description": "Good practice and quality indicators",
            "examples": ["Model version", "Interpolation method", "Curve shape"]
        },
        "LOW": {
            "description": "Nice to have for completeness",
            "examples": ["Documentation completeness", "Metadata validation"]
        }
    }
    
    return {
        "priorities": priorities,
        "description": "Validation priority levels for Quant Review Guide"
    }

@router.post("/validate-specific-category")
async def validate_specific_category(
    category: str,
    request: ValidationRequest
):
    """
    Validate a specific category of the valuation run
    
    Categories: Run_Summary, Instrument_Summary, Data_Sources, 
    Curves, Calculations, IFRS_Compliance
    """
    try:
        from ..core.validation.quant_review import QuantReviewValidator
        
        validator = QuantReviewValidator()
        run_data = request.run_data
        
        # Validate specific category
        if category == "Run_Summary":
            checks = validator.validate_run_summary(run_data.get('run_summary', {}))
        elif category == "Instrument_Summary":
            checks = validator.validate_instrument_summary(run_data.get('instrument_summary', {}))
        elif category == "Data_Sources":
            checks = validator.validate_data_sources(run_data.get('data_sources', {}))
        elif category == "Curves":
            checks = validator.validate_curves(run_data.get('curves', {}))
        elif category == "Calculations":
            checks = validator.validate_calculations(run_data.get('calculations', {}))
        elif category == "IFRS_Compliance":
            checks = validator.validate_ifrs_compliance(run_data.get('ifrs_compliance', {}))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category: {category}. Valid categories are: Run_Summary, Instrument_Summary, Data_Sources, Curves, Calculations, IFRS_Compliance"
            )
        
        # Convert to response format
        checks_data = []
        for check in checks:
            checks_data.append({
                "id": check.id,
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "details": check.details,
                "category": check.category,
                "priority": check.priority
            })
        
        return {
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "total_checks": len(checks),
            "passed_checks": len([c for c in checks if c.status == ValidationStatus.PASSED]),
            "failed_checks": len([c for c in checks if c.status == ValidationStatus.FAILED]),
            "warning_checks": len([c for c in checks if c.status == ValidationStatus.WARNING]),
            "checks": checks_data
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Category validation failed: {str(e)}"
        )

@router.get("/validation-status")
async def get_validation_status():
    """
    Get current validation system status and health
    """
    return {
        "status": "operational",
        "version": "1.0.0",
        "description": "Quant Review Guide validation system",
        "features": [
            "Run summary validation",
            "Instrument parameter validation", 
            "Market data validation",
            "Curve validation",
            "Calculation validation",
            "IFRS-13 compliance validation"
        ],
        "supported_categories": [
            "Run_Summary",
            "Instrument_Summary", 
            "Data_Sources",
            "Curves",
            "Calculations",
            "IFRS_Compliance"
        ],
        "timestamp": datetime.now().isoformat()
    }




