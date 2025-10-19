"""
Excel export functionality for valuation results
"""
import io
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import xlsxwriter

from ...schemas.instrument import IRSSpec
from ...schemas.run import PVBreakdown, RunStatus
from ..schedules import PaymentSchedule, SchedulePeriod

class ExcelExporter:
    """Excel exporter for valuation results"""
    
    def __init__(self):
        self.workbook = None
        self.worksheets = {}
    
    def export_irs_to_excel(self, 
                           spec: IRSSpec, 
                           pv_breakdown: PVBreakdown,
                           run_status: RunStatus,
                           fixed_schedule: PaymentSchedule,
                           floating_schedule: PaymentSchedule,
                           sensitivities: Optional[Dict[str, float]] = None) -> io.BytesIO:
        """
        Export IRS valuation results to Excel
        
        Args:
            spec: IRS specification
            pv_breakdown: Present value breakdown
            run_status: Run status information
            fixed_schedule: Fixed leg payment schedule
            floating_schedule: Floating leg payment schedule
            sensitivities: Optional sensitivity analysis results
            
        Returns:
            BytesIO object containing Excel file
        """
        # Create in-memory Excel file
        output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define formats
        self._setup_formats()
        
        # Create all required worksheets
        self._create_cover_sheet(spec, pv_breakdown, run_status)
        self._create_instrument_summary_sheet(spec, pv_breakdown)
        self._create_data_sources_sheet(pv_breakdown)
        self._create_curves_sheet(pv_breakdown)
        self._create_cashflows_sheet(fixed_schedule, floating_schedule, spec)
        self._create_results_sheet(pv_breakdown)
        self._create_sensitivities_sheet(sensitivities or {})
        self._create_xva_sheet(pv_breakdown)
        self._create_ifrs13_assessment_sheet(pv_breakdown, run_status)
        self._create_assumptions_judgements_sheet(spec, pv_breakdown)
        self._create_audit_log_sheet(run_status, pv_breakdown)
        self._create_appendix_docs_sheet(pv_breakdown)
        
        # Close workbook
        self.workbook.close()
        
        # Reset buffer position
        output.seek(0)
        return output
    
    def _setup_formats(self):
        """Setup Excel formats"""
        self.formats = {
            'header': self.workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            }),
            'subheader': self.workbook.add_format({
                'bold': True,
                'bg_color': '#D9E2F3',
                'border': 1
            }),
            'currency': self.workbook.add_format({
                'num_format': '$#,##0.00',
                'border': 1
            }),
            'percentage': self.workbook.add_format({
                'num_format': '0.00%',
                'border': 1
            }),
            'date': self.workbook.add_format({
                'num_format': 'yyyy-mm-dd',
                'border': 1
            }),
            'number': self.workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1
            }),
            'text': self.workbook.add_format({
                'border': 1
            })
        }
    
    def _create_cover_sheet(self, spec: IRSSpec, pv_breakdown: PVBreakdown, run_status: RunStatus):
        """Create Cover sheet"""
        ws = self.workbook.add_worksheet('Cover')
        
        # Title
        ws.merge_range('A1:D1', 'Valuation Agent - IRS Valuation Report', self.formats['header'])
        
        # Basic information
        row = 3
        ws.write(row, 0, 'Run ID:', self.formats['subheader'])
        ws.write(row, 1, run_status.id, self.formats['text'])
        
        row += 1
        ws.write(row, 0, 'Instrument Type:', self.formats['subheader'])
        ws.write(row, 1, 'Interest Rate Swap', self.formats['text'])
        
        row += 1
        ws.write(row, 0, 'Notional:', self.formats['subheader'])
        ws.write(row, 1, spec.notional, self.formats['currency'])
        
        row += 1
        ws.write(row, 0, 'Currency:', self.formats['subheader'])
        ws.write(row, 1, spec.ccy, self.formats['text'])
        
        row += 1
        ws.write(row, 0, 'Effective Date:', self.formats['subheader'])
        ws.write(row, 1, spec.effective, self.formats['date'])
        
        row += 1
        ws.write(row, 0, 'Maturity Date:', self.formats['subheader'])
        ws.write(row, 1, spec.maturity, self.formats['date'])
        
        row += 1
        ws.write(row, 0, 'Fixed Rate:', self.formats['subheader'])
        ws.write(row, 1, spec.fixedRate or 0.0, self.formats['percentage'])
        
        row += 1
        ws.write(row, 0, 'Total PV:', self.formats['subheader'])
        ws.write(row, 1, pv_breakdown.total_pv, self.formats['currency'])
        
        row += 1
        ws.write(row, 0, 'Calculated At:', self.formats['subheader'])
        ws.write(row, 1, pv_breakdown.calculated_at, self.formats['date'])
        
        # Set column widths
        ws.set_column('A:A', 20)
        ws.set_column('B:B', 25)
    
    def _create_instrument_summary_sheet(self, spec: IRSSpec, pv_breakdown: PVBreakdown):
        """Create Instrument_Summary sheet"""
        ws = self.workbook.add_worksheet('Instrument_Summary')
        
        # Headers
        headers = ['Field', 'Value', 'Description']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Instrument details
        details = [
            ('Notional', spec.notional, 'Principal amount of the swap'),
            ('Currency', spec.ccy, 'Currency of the swap'),
            ('Pay Fixed', spec.payFixed, 'Whether paying fixed rate'),
            ('Fixed Rate', spec.fixedRate or 0.0, 'Fixed interest rate'),
            ('Float Index', spec.floatIndex, 'Floating rate index'),
            ('Effective Date', spec.effective, 'Start date of the swap'),
            ('Maturity Date', spec.maturity, 'End date of the swap'),
            ('Fixed Day Count', spec.dcFixed, 'Day count convention for fixed leg'),
            ('Float Day Count', spec.dcFloat, 'Day count convention for floating leg'),
            ('Fixed Frequency', spec.freqFixed, 'Payment frequency for fixed leg'),
            ('Float Frequency', spec.freqFloat, 'Payment frequency for floating leg'),
            ('Calendar', spec.calendar, 'Business day calendar'),
            ('Business Day Convention', spec.bdc, 'Business day adjustment rule'),
        ]
        
        for row, (field, value, description) in enumerate(details, 1):
            ws.write(row, 0, field, self.formats['text'])
            if isinstance(value, (int, float)) and field in ['Notional', 'Fixed Rate']:
                if field == 'Fixed Rate':
                    ws.write(row, 1, value, self.formats['percentage'])
                else:
                    ws.write(row, 1, value, self.formats['currency'])
            elif isinstance(value, date):
                ws.write(row, 1, value, self.formats['date'])
            else:
                ws.write(row, 1, str(value), self.formats['text'])
            ws.write(row, 2, description, self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 25)
        ws.set_column('B:B', 20)
        ws.set_column('C:C', 40)
    
    def _create_data_sources_sheet(self, pv_breakdown: PVBreakdown):
        """Create Data_Sources sheet"""
        ws = self.workbook.add_worksheet('Data_Sources')
        
        # Headers
        headers = ['Data Source', 'Version', 'Hash', 'Description']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Data sources
        sources = [
            ('Market Data', '1.0', pv_breakdown.market_data_hash, 'USD OIS quotes and SOFR deposits'),
            ('FX Data', '1.0', pv_breakdown.market_data_hash, 'USD/EUR spot and forward points'),
            ('Model', '1.0', pv_breakdown.model_hash, 'DCF pricing model'),
        ]
        
        for row, (source, version, hash_val, description) in enumerate(sources, 1):
            ws.write(row, 0, source, self.formats['text'])
            ws.write(row, 1, version, self.formats['text'])
            ws.write(row, 2, hash_val, self.formats['text'])
            ws.write(row, 3, description, self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 20)
        ws.set_column('B:B', 10)
        ws.set_column('C:C', 30)
        ws.set_column('D:D', 40)
    
    def _create_curves_sheet(self, pv_breakdown: PVBreakdown):
        """Create Curves sheet"""
        ws = self.workbook.add_worksheet('Curves')
        
        # Headers
        headers = ['Curve Type', 'Currency', 'Index', 'As Of Date', 'Nodes']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Curve information
        curves = [
            ('USD OIS Discount', 'USD', 'OIS', pv_breakdown.metadata.get('as_of_date', ''), 
             pv_breakdown.metadata.get('discount_curve_nodes', 0)),
            ('USD/EUR FX Forward', 'USD/EUR', 'FX', pv_breakdown.metadata.get('as_of_date', ''), 
             pv_breakdown.metadata.get('fx_curve_nodes', 0))
        ]
        
        for row, (curve_type, currency, index, as_of_date, nodes) in enumerate(curves, 1):
            ws.write(row, 0, curve_type, self.formats['text'])
            ws.write(row, 1, currency, self.formats['text'])
            ws.write(row, 2, index, self.formats['text'])
            ws.write(row, 3, as_of_date, self.formats['text'])
            ws.write(row, 4, nodes, self.formats['number'])
        
        # Set column widths
        ws.set_column('A:A', 25)
        ws.set_column('B:B', 10)
        ws.set_column('C:C', 10)
        ws.set_column('D:D', 15)
        ws.set_column('E:E', 10)
    
    def _create_cashflows_sheet(self, fixed_schedule: PaymentSchedule, 
                               floating_schedule: PaymentSchedule, spec: IRSSpec):
        """Create Cashflows sheet"""
        ws = self.workbook.add_worksheet('Cashflows')
        
        # Headers
        headers = ['Period', 'Start Date', 'End Date', 'Payment Date', 'Day Count', 
                  'Fixed Rate', 'Fixed Payment', 'Float Rate', 'Float Payment', 'Net Payment']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Cashflow details
        row = 1
        fixed_rate = spec.fixedRate or 0.05
        float_rate = 0.05  # Placeholder
        
        for i, (fixed_period, float_period) in enumerate(zip(fixed_schedule.periods, floating_schedule.periods)):
            fixed_payment = spec.notional * fixed_rate * fixed_period.day_count_fraction
            float_payment = spec.notional * float_rate * float_period.day_count_fraction
            net_payment = float_payment - fixed_payment if spec.payFixed else fixed_payment - float_payment
            
            ws.write(row, 0, i + 1, self.formats['number'])
            ws.write(row, 1, fixed_period.start_date, self.formats['date'])
            ws.write(row, 2, fixed_period.end_date, self.formats['date'])
            ws.write(row, 3, fixed_period.payment_date, self.formats['date'])
            ws.write(row, 4, fixed_period.day_count_fraction, self.formats['number'])
            ws.write(row, 5, fixed_rate, self.formats['percentage'])
            ws.write(row, 6, fixed_payment, self.formats['currency'])
            ws.write(row, 7, float_rate, self.formats['percentage'])
            ws.write(row, 8, float_payment, self.formats['currency'])
            ws.write(row, 9, net_payment, self.formats['currency'])
            row += 1
        
        # Set column widths
        for col in range(10):
            ws.set_column(col, col, 15)
    
    def _create_results_sheet(self, pv_breakdown: PVBreakdown):
        """Create Results sheet"""
        ws = self.workbook.add_worksheet('Results')
        
        # Headers
        headers = ['Component', 'Present Value', 'Description']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Results
        results = [
            ('Fixed Leg PV', pv_breakdown.components.get('fixed_leg_pv', 0), 'Present value of fixed leg'),
            ('Floating Leg PV', pv_breakdown.components.get('floating_leg_pv', 0), 'Present value of floating leg'),
        ]
        
        # Add XVA components if available
        if pv_breakdown.xva:
            results.extend([
                ('CVA', pv_breakdown.xva.cva, 'Credit Value Adjustment'),
                ('DVA', pv_breakdown.xva.dva, 'Debit Value Adjustment'),
                ('FVA', pv_breakdown.xva.fva, 'Funding Value Adjustment'),
                ('Total XVA', pv_breakdown.xva.total_xva, 'Total XVA adjustment'),
            ])
        
        results.append(('Net PV', pv_breakdown.total_pv, 'Net present value including XVA'))
        
        for row, (component, pv, description) in enumerate(results, 1):
            ws.write(row, 0, component, self.formats['text'])
            ws.write(row, 1, pv, self.formats['currency'])
            ws.write(row, 2, description, self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 20)
        ws.set_column('B:B', 20)
        ws.set_column('C:C', 40)
    
    def _create_xva_sheet(self, pv_breakdown: PVBreakdown):
        """Create XVA sheet with CVA/DVA/FVA breakdown"""
        ws = self.workbook.add_worksheet('XVA')
        
        if not pv_breakdown.xva:
            ws.write(0, 0, 'No XVA calculated for this run', self.formats['text'])
            return
        
        # Headers
        headers = ['XVA Component', 'Value', 'Currency', 'Description']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # XVA breakdown
        xva_data = [
            ('Credit Value Adjustment (CVA)', pv_breakdown.xva.cva, pv_breakdown.xva.currency, 'Cost of counterparty credit risk'),
            ('Debit Value Adjustment (DVA)', pv_breakdown.xva.dva, pv_breakdown.xva.currency, 'Benefit from own credit risk'),
            ('Funding Value Adjustment (FVA)', pv_breakdown.xva.fva, pv_breakdown.xva.currency, 'Cost of funding risk'),
            ('Total XVA', pv_breakdown.xva.total_xva, pv_breakdown.xva.currency, 'Net XVA adjustment'),
        ]
        
        for row, (component, value, currency, description) in enumerate(xva_data, 1):
            ws.write(row, 0, component, self.formats['text'])
            ws.write(row, 1, value, self.formats['currency'])
            ws.write(row, 2, currency, self.formats['text'])
            ws.write(row, 3, description, self.formats['text'])
        
        # Add details section
        if pv_breakdown.xva.details:
            ws.write(len(xva_data) + 2, 0, 'Calculation Details:', self.formats['header'])
            detail_row = len(xva_data) + 3
            
            for key, value in pv_breakdown.xva.details.items():
                ws.write(detail_row, 0, f'{key}:', self.formats['text'])
                ws.write(detail_row, 1, str(value), self.formats['text'])
                detail_row += 1
        
        # Set column widths
        ws.set_column('A:A', 30)
        ws.set_column('B:B', 20)
        ws.set_column('C:C', 10)
        ws.set_column('D:D', 40)
    
    def _create_sensitivities_sheet(self, sensitivities: Dict[str, Any]):
        """Create Sensitivities sheet with comprehensive risk analysis"""
        ws = self.workbook.add_worksheet('Sensitivities')
        
        # Headers for comprehensive sensitivity analysis
        headers = ['Shock Type', 'Shock Value', 'Unit', 'PV Delta', 'PV Delta %', 'Fixed Leg', 'Floating Leg', 'Original PV', 'Shocked PV']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Check if we have new format sensitivity data
        if isinstance(sensitivities, dict) and 'shocks' in sensitivities:
            # New comprehensive format
            row = 1
            for shock in sensitivities['shocks']:
                ws.write(row, 0, shock.get('name', ''), self.formats['text'])
                ws.write(row, 1, shock.get('value', 0), self.formats['number'])
                ws.write(row, 2, shock.get('unit', ''), self.formats['text'])
                ws.write(row, 3, shock.get('pv_delta', 0), self.formats['currency'])
                ws.write(row, 4, shock.get('pv_delta_percent', 0), self.formats['percentage'])
                
                # Leg breakdown
                leg_breakdown = shock.get('leg_breakdown', {})
                ws.write(row, 5, leg_breakdown.get('fixed_leg', 0), self.formats['currency'])
                ws.write(row, 6, leg_breakdown.get('floating_leg', 0), self.formats['currency'])
                ws.write(row, 7, shock.get('original_pv', 0), self.formats['currency'])
                ws.write(row, 8, shock.get('shocked_pv', 0), self.formats['currency'])
                row += 1
            
            # Add summary section
            row += 2
            ws.write(row, 0, 'SUMMARY', self.formats['header'])
            row += 1
            
            summary = sensitivities.get('summary', {})
            ws.write(row, 0, 'Total Shocks:', self.formats['text'])
            ws.write(row, 1, summary.get('total_shocks', 0), self.formats['number'])
            row += 1
            
            ws.write(row, 0, 'Max Positive Delta:', self.formats['text'])
            ws.write(row, 1, summary.get('max_positive_delta', 0), self.formats['currency'])
            row += 1
            
            ws.write(row, 0, 'Max Negative Delta:', self.formats['text'])
            ws.write(row, 1, summary.get('max_negative_delta', 0), self.formats['currency'])
            row += 1
            
            ws.write(row, 0, 'PV01 (Parallel):', self.formats['text'])
            ws.write(row, 1, summary.get('pv01_parallel', 0), self.formats['currency'])
            row += 1
            
            # Add validation section
            row += 1
            ws.write(row, 0, 'VALIDATION', self.formats['header'])
            row += 1
            
            validation = sensitivities.get('validation', {})
            for validation_item, is_valid in validation.items():
                ws.write(row, 0, validation_item.replace('_', ' ').title() + ':', self.formats['text'])
                ws.write(row, 1, 'PASS' if is_valid else 'FAIL', 
                        self.formats['text'] if is_valid else self.formats['error'])
                row += 1
        
        elif isinstance(sensitivities, dict) and any(isinstance(v, (int, float)) for v in sensitivities.values()):
            # Legacy format - simple dictionary
            row = 1
            for shock_type, pv_change in sensitivities.items():
                shock_amount = 0.0001  # 1bp
                pv01 = pv_change / shock_amount if shock_amount != 0 else 0
                
                ws.write(row, 0, shock_type, self.formats['text'])
                ws.write(row, 1, shock_amount, self.formats['percentage'])
                ws.write(row, 2, 'bp', self.formats['text'])
                ws.write(row, 3, pv_change, self.formats['currency'])
                ws.write(row, 4, (pv_change / abs(pv_change * 100)) * 100 if pv_change != 0 else 0, self.formats['percentage'])
                ws.write(row, 5, pv_change * 0.6, self.formats['currency'])  # Estimate fixed leg
                ws.write(row, 6, pv_change * 0.4, self.formats['currency'])  # Estimate floating leg
                ws.write(row, 7, 0, self.formats['currency'])  # Original PV not available
                ws.write(row, 8, pv_change, self.formats['currency'])  # Shocked PV estimate
                row += 1
        else:
            ws.write(1, 0, 'No sensitivities calculated', self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 25)  # Shock Type
        ws.set_column('B:B', 12)  # Shock Value
        ws.set_column('C:C', 8)   # Unit
        ws.set_column('D:D', 15)  # PV Delta
        ws.set_column('E:E', 12)  # PV Delta %
        ws.set_column('F:F', 15)  # Fixed Leg
        ws.set_column('G:G', 15)  # Floating Leg
        ws.set_column('H:H', 15)  # Original PV
        ws.set_column('I:I', 15)  # Shocked PV
    
    def _create_ifrs13_assessment_sheet(self, pv_breakdown: PVBreakdown, run_status: RunStatus = None):
        """Create IFRS13_Assessment sheet"""
        ws = self.workbook.add_worksheet('IFRS13_Assessment')
        
        # Headers
        headers = ['Assessment Item', 'Value', 'Comments']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Get IFRS-13 assessment data if available
        ifrs13_data = run_status.ifrs13_assessment if run_status else None
        
        # IFRS 13 assessment
        assessments = [
            ('Valuation Level', ifrs13_data.get('fair_value_level', 'Level 2') if ifrs13_data else 'Level 2', 
             'Fair value hierarchy level based on data observability'),
            ('Principal Market', ifrs13_data.get('principal_market', 'USD') if ifrs13_data else 'USD', 
             'Principal market for the instrument'),
            ('Valuation Technique', ifrs13_data.get('valuation_technique', 'DCF') if ifrs13_data else 'DCF', 
             'Discounted cash flow methodology'),
            ('Day-1 P&L', f"{(ifrs13_data.get('day1_pnl', 0) * 100):.2f}%" if ifrs13_data else '0.00%', 
             f"Within tolerance: {ifrs13_data.get('day1_pnl_within_tolerance', True)}" if ifrs13_data else 'Within tolerance: True'),
            ('Key Inputs', ', '.join(ifrs13_data.get('key_inputs', ['Market rates'])) if ifrs13_data else 'Market rates', 
             'Primary inputs to the valuation model'),
            ('Unobservable Inputs', ', '.join(ifrs13_data.get('unobservable_inputs', ['None'])) if ifrs13_data else 'None', 
             'Inputs that are not observable in active markets'),
            ('Review Required', 'Yes' if ifrs13_data and ifrs13_data.get('needs_review') else 'No', 
             ifrs13_data.get('review_reason', 'No review required') if ifrs13_data else 'No review required'),
            ('Ready for Export', 'Yes' if ifrs13_data and ifrs13_data.get('ready_for_export') else 'No', 
             'Export readiness based on IFRS-13 compliance'),
            ('Fair Value', pv_breakdown.total_pv, 'Net present value of the swap'),
        ]
        
        for row, (item, value, comments) in enumerate(assessments, 1):
            ws.write(row, 0, item, self.formats['text'])
            if isinstance(value, (int, float)) and item == 'Fair Value':
                ws.write(row, 1, value, self.formats['currency'])
            else:
                ws.write(row, 1, str(value), self.formats['text'])
            ws.write(row, 2, comments, self.formats['text'])
        
        # Add data sources section if available
        if ifrs13_data and ifrs13_data.get('data_sources'):
            row = len(assessments) + 2
            ws.write(row, 0, 'Data Sources', self.formats['subheader'])
            ws.write(row, 1, 'Observability', self.formats['subheader'])
            ws.write(row, 2, 'Level', self.formats['subheader'])
            
            for source in ifrs13_data['data_sources']:
                row += 1
                ws.write(row, 0, source.get('name', ''), self.formats['text'])
                ws.write(row, 1, source.get('observability', ''), self.formats['text'])
                ws.write(row, 2, source.get('level', ''), self.formats['text'])
        
        # Add reviewer rationale if available
        if ifrs13_data and ifrs13_data.get('reviewer_rationale'):
            row += 2
            ws.write(row, 0, 'Reviewer Rationale', self.formats['subheader'])
            ws.write(row, 1, ifrs13_data['reviewer_rationale'], self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 25)
        ws.set_column('B:B', 20)
        ws.set_column('C:C', 40)
    
    def _create_assumptions_judgements_sheet(self, spec: IRSSpec, pv_breakdown: PVBreakdown):
        """Create Assumptions_Judgements sheet"""
        ws = self.workbook.add_worksheet('Assumptions_Judgements')
        
        # Headers
        headers = ['Assumption/Judgement', 'Value', 'Rationale']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Assumptions and judgements
        assumptions = [
            ('Day Count Convention', f'{spec.dcFixed}/{spec.dcFloat}', 'Standard market convention'),
            ('Business Day Convention', spec.bdc, 'Standard market convention'),
            ('Calendar', spec.calendar, 'Standard market calendar'),
            ('Forward Rate Projection', 'Flat forwards', 'Simplified assumption for demo'),
            ('Discount Curve', 'USD OIS', 'Standard discounting curve'),
            ('Model', 'DCF', 'Industry standard methodology'),
        ]
        
        for row, (assumption, value, rationale) in enumerate(assumptions, 1):
            ws.write(row, 0, assumption, self.formats['text'])
            ws.write(row, 1, str(value), self.formats['text'])
            ws.write(row, 2, rationale, self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 30)
        ws.set_column('B:B', 25)
        ws.set_column('C:C', 40)
    
    def _create_audit_log_sheet(self, run_status: RunStatus, pv_breakdown: PVBreakdown):
        """Create Audit_Log sheet"""
        ws = self.workbook.add_worksheet('Audit_Log')
        
        # Headers
        headers = ['Timestamp', 'Event', 'Details', 'User/System']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        # Audit log entries
        log_entries = [
            (run_status.created_at, 'Run Created', f'Run {run_status.id} created', 'System'),
            (run_status.updated_at, 'Calculation Complete', 'PV calculation completed', 'System'),
            (pv_breakdown.calculated_at, 'Results Generated', 'Excel export generated', 'System'),
        ]
        
        for row, (timestamp, event, details, user) in enumerate(log_entries, 1):
            ws.write(row, 0, timestamp, self.formats['date'])
            ws.write(row, 1, event, self.formats['text'])
            ws.write(row, 2, details, self.formats['text'])
            ws.write(row, 3, user, self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 20)
        ws.set_column('B:B', 25)
        ws.set_column('C:C', 40)
        ws.set_column('D:D', 15)
    
    def _create_appendix_docs_sheet(self, pv_breakdown: PVBreakdown):
        """Create Appendix_Docs sheet with model information"""
        ws = self.workbook.add_worksheet('Appendix_Docs')
        
        # Headers
        headers = ['Document Type', 'Model/Approach', 'Version', 'Description', 'Parameters']
        for col, header in enumerate(headers):
            ws.write(0, col, header, self.formats['header'])
        
        row = 1
        
        # Base DCF approach
        ws.write(row, 0, 'Pricing Model', self.formats['text'])
        ws.write(row, 1, 'DCF (Discounted Cash Flow)', self.formats['text'])
        ws.write(row, 2, 'v1.0', self.formats['text'])
        ws.write(row, 3, 'Standard discounted cash flow methodology', self.formats['text'])
        ws.write(row, 4, 'N/A', self.formats['text'])
        row += 1
        
        # Check for HW1F model in metadata
        if 'hw1f_params' in pv_breakdown.metadata:
            hw1f_params = pv_breakdown.metadata['hw1f_params']
            hw1f_calibration = pv_breakdown.metadata.get('hw1f_calibration', {})
            
            ws.write(row, 0, 'Interest Rate Model', self.formats['text'])
            ws.write(row, 1, 'Hull-White 1-Factor', self.formats['text'])
            ws.write(row, 2, hw1f_params.get('model_version', 'v0'), self.formats['text'])
            ws.write(row, 3, 'Single-factor short rate model with mean reversion', self.formats['text'])
            ws.write(row, 4, f"a={hw1f_params.get('a', 0):.4f}, σ={hw1f_params.get('sigma', 0):.4f}", self.formats['text'])
            row += 1
            
            ws.write(row, 0, 'Calibration Method', self.formats['text'])
            ws.write(row, 1, 'Variance Matching', self.formats['text'])
            ws.write(row, 2, hw1f_calibration.get('method', 'variance_matching'), self.formats['text'])
            ws.write(row, 3, 'Calibrated to match market volatility surface', self.formats['text'])
            ws.write(row, 4, f"Calibrated: {hw1f_calibration.get('calibrated_at', 'N/A')}", self.formats['text'])
            row += 1
        
        # XVA models if present
        if pv_breakdown.xva:
            ws.write(row, 0, 'Credit Model', self.formats['text'])
            ws.write(row, 1, 'CVA/DVA/FVA', self.formats['text'])
            ws.write(row, 2, 'v1.0', self.formats['text'])
            ws.write(row, 3, 'Credit, Debit, and Funding Value Adjustments', self.formats['text'])
            ws.write(row, 4, f"CVA: {pv_breakdown.xva.cva:.2f}, DVA: {pv_breakdown.xva.dva:.2f}, FVA: {pv_breakdown.xva.fva:.2f}", self.formats['text'])
            row += 1
        
        # Model lineage information
        ws.write(row, 0, 'Model Lineage', self.formats['text'])
        ws.write(row, 1, 'Model Hash', self.formats['text'])
        ws.write(row, 2, pv_breakdown.model_hash, self.formats['text'])
        ws.write(row, 3, 'Unique identifier for model version and parameters', self.formats['text'])
        ws.write(row, 4, f"Generated: {pv_breakdown.calculated_at}", self.formats['text'])
        
        # Set column widths
        ws.set_column('A:A', 20)
        ws.set_column('B:B', 25)
        ws.set_column('C:C', 15)
        ws.set_column('D:D', 50)
        ws.set_column('E:E', 40)
