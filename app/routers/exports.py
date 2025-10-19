"""
Export endpoints for valuation results
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import io

from ..core.exporters.excel import ExcelExporter
from ..core.schedules import create_schedule
from ..core.pricing.irs import calculate_fixed_leg_pv, calculate_floating_leg_pv
from ..core.curves.ois import bootstrap_usd_ois_curve
from ..schemas.instrument import IRSSpec
from ..schemas.run import RunStatus, RunStatusEnum

router = APIRouter()

# In-memory storage for runs (in production, this would be a database)
runs_db: Dict[str, RunStatus] = {}
results_db: Dict[str, Any] = {}

@router.get("/exports/{run_id}/excel")
async def export_excel(run_id: str):
    """
    Export valuation results to Excel
    
    Args:
        run_id: Run identifier
        
    Returns:
        Excel file stream
    """
    # Check if run exists
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    run_status = runs_db[run_id]
    
    # Check if run is completed and ready for export
    if run_status.status != RunStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Run {run_id} is not completed")
    
    # Check IFRS-13 assessment for export readiness
    if run_status.ifrs13_assessment and not run_status.ifrs13_assessment.get("ready_for_export", False):
        raise HTTPException(
            status_code=400, 
            detail=f"Run {run_id} requires IFRS-13 review before export. Reason: {run_status.ifrs13_assessment.get('review_reason', 'Unknown')}"
        )
    
    # Get results
    if run_id not in results_db:
        raise HTTPException(status_code=404, detail=f"Results for run {run_id} not found")
    
    results = results_db[run_id]
    spec = run_status.request.spec
    
    # Ensure spec is IRSSpec
    if not isinstance(spec, IRSSpec):
        raise HTTPException(status_code=400, detail="Excel export only supported for IRS instruments")
    
    try:
        # Bootstrap discount curve
        discount_curve = bootstrap_usd_ois_curve(run_status.request.asOf)
        
        # Create payment schedules
        fixed_schedule = create_schedule(
            effective_date=spec.effective,
            termination_date=spec.maturity,
            frequency=spec.freqFixed,
            day_count_convention=spec.dcFixed,
            business_day_convention=spec.bdc,
            calendar_name=spec.calendar
        )
        
        floating_schedule = create_schedule(
            effective_date=spec.effective,
            termination_date=spec.maturity,
            frequency=spec.freqFloat,
            day_count_convention=spec.dcFloat,
            business_day_convention=spec.bdc,
            calendar_name=spec.calendar
        )
        
        # Calculate sensitivities (placeholder for now)
        sensitivities = {
            "Parallel +1bp": 0.0,  # Will be calculated in sensitivity analysis
            "Parallel -1bp": 0.0,
        }
        
        # Create Excel exporter
        exporter = ExcelExporter()
        excel_file = exporter.export_irs_to_excel(
            spec=spec,
            pv_breakdown=results,
            run_status=run_status,
            fixed_schedule=fixed_schedule,
            floating_schedule=floating_schedule,
            sensitivities=sensitivities
        )
        
        # Return Excel file as stream
        return StreamingResponse(
            io.BytesIO(excel_file.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=irs_valuation_{run_id}.xlsx"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel export: {str(e)}")

@router.get("/exports/{run_id}/cashflows")
async def export_cashflows(run_id: str):
    """
    Export cashflows as JSON
    
    Args:
        run_id: Run identifier
        
    Returns:
        Cashflows data
    """
    # Check if run exists
    if run_id not in runs_db:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    run_status = runs_db[run_id]
    spec = run_status.request.spec
    
    if not isinstance(spec, IRSSpec):
        raise HTTPException(status_code=400, detail="Cashflow export only supported for IRS instruments")
    
    try:
        # Create payment schedules
        fixed_schedule = create_schedule(
            effective_date=spec.effective,
            termination_date=spec.maturity,
            frequency=spec.freqFixed,
            day_count_convention=spec.dcFixed,
            business_day_convention=spec.bdc,
            calendar_name=spec.calendar
        )
        
        floating_schedule = create_schedule(
            effective_date=spec.effective,
            termination_date=spec.maturity,
            frequency=spec.freqFloat,
            day_count_convention=spec.dcFloat,
            business_day_convention=spec.bdc,
            calendar_name=spec.calendar
        )
        
        # Convert schedules to JSON-serializable format
        fixed_cashflows = []
        for period in fixed_schedule.periods:
            fixed_cashflows.append({
                "period_number": period.period_number,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
                "payment_date": period.payment_date.isoformat(),
                "day_count_fraction": period.day_count_fraction,
                "payment_amount": spec.notional * (spec.fixedRate or 0.05) * period.day_count_fraction
            })
        
        floating_cashflows = []
        for period in floating_schedule.periods:
            floating_cashflows.append({
                "period_number": period.period_number,
                "start_date": period.start_date.isoformat(),
                "end_date": period.end_date.isoformat(),
                "payment_date": period.payment_date.isoformat(),
                "day_count_fraction": period.day_count_fraction,
                "payment_amount": spec.notional * 0.05 * period.day_count_fraction  # Placeholder rate
            })
        
        return {
            "run_id": run_id,
            "fixed_leg_cashflows": fixed_cashflows,
            "floating_leg_cashflows": floating_cashflows,
            "instrument_details": {
                "notional": spec.notional,
                "currency": spec.ccy,
                "effective_date": spec.effective.isoformat(),
                "maturity_date": spec.maturity.isoformat(),
                "fixed_rate": spec.fixedRate,
                "pay_fixed": spec.payFixed
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cashflow export: {str(e)}")
