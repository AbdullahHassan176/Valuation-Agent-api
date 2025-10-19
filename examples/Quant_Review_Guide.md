# Quant Review Guide

This guide provides detailed instructions for reviewing Excel outputs from the Valuation Agent Workspace.

## 📊 Excel Workbook Structure

### 1. Cover Sheet
**Purpose**: Executive summary and metadata
**Key Fields to Review**:
- **Run ID**: Unique identifier for audit trail
- **Instrument Type**: IRS/CCS classification
- **Notional Amount**: Principal value
- **Valuation Date**: As-of date for pricing
- **Model Version**: Pricing methodology used
- **Data Hash**: Market data integrity check

**Review Checklist**:
- [ ] Run ID matches system records
- [ ] Instrument details are correct
- [ ] Valuation date is appropriate
- [ ] Model version is current

### 2. Instrument_Summary Sheet
**Purpose**: Trade details and parameters
**Key Fields to Review**:
- **Trade Details**: Notional, currency, effective/maturity dates
- **Rate Information**: Fixed rates, floating indices
- **Schedule Parameters**: Frequency, day count conventions
- **Calendar Information**: Business day conventions, holiday calendars

**Review Checklist**:
- [ ] Notional amounts are correct
- [ ] Currency pairs match trade documentation
- [ ] Rate conventions are appropriate
- [ ] Schedule parameters match trade terms
- [ ] Calendar settings are correct for jurisdiction

### 3. Data_Sources Sheet
**Purpose**: Market data and curve information
**Key Fields to Review**:
- **Curve Sources**: OIS, LIBOR, SOFR curves
- **Data Timestamps**: When market data was captured
- **Data Quality**: Completeness and reasonableness
- **Interpolation Methods**: Curve construction methodology

**Review Checklist**:
- [ ] Market data is current and complete
- [ ] Curve sources are appropriate
- [ ] Data timestamps are reasonable
- [ ] Interpolation methods are documented

### 4. Curves Sheet
**Purpose**: Discount and forward curve details
**Key Fields to Review**:
- **Discount Curves**: OIS curves for each currency
- **Forward Curves**: Projected floating rates
- **Curve Shapes**: Reasonableness of curve structure
- **Bootstrap Results**: Curve construction validation

**Review Checklist**:
- [ ] Discount curves are properly bootstrapped
- [ ] Forward curves are reasonable
- [ ] Curve shapes are market-consistent
- [ ] Bootstrap results are validated

### 5. Cashflows Sheet
**Purpose**: Payment schedule and calculations
**Key Fields to Review**:
- **Payment Dates**: Schedule generation accuracy
- **Day Count Fractions**: Day count convention application
- **Fixed Payments**: Fixed leg calculations
- **Floating Payments**: Floating leg with forward rates
- **Net Payments**: Net cash flows

**Review Checklist**:
- [ ] Payment dates are correct
- [ ] Day count fractions are accurate
- [ ] Fixed payments are calculated correctly
- [ ] Floating payments use appropriate forward rates
- [ ] Net payments sum correctly

### 6. Results Sheet
**Purpose**: Present value breakdown and metrics
**Key Fields to Review**:
- **Total PV**: Overall present value
- **Fixed Leg PV**: Fixed leg present value
- **Floating Leg PV**: Floating leg present value
- **Currency**: Reporting currency
- **Discount Factors**: Applied discount factors

**Review Checklist**:
- [ ] Total PV is reasonable
- [ ] Leg PVs are calculated correctly
- [ ] Currency conversion is appropriate
- [ ] Discount factors are applied correctly

### 7. Sensitivities Sheet
**Purpose**: Risk analysis and stress tests
**Key Fields to Review**:
- **PV01**: Present value of 1 basis point
- **Parallel Shocks**: ±1bp, ±10bp curve shifts
- **Curve Twists**: Short/long end differential shocks
- **FX Shocks**: Currency rate movements
- **Custom Scenarios**: User-defined stress tests

**Review Checklist**:
- [ ] PV01 is reasonable for instrument type
- [ ] Parallel shocks show expected behavior
- [ ] Curve twists are properly implemented
- [ ] FX shocks are appropriate for CCS
- [ ] Custom scenarios are well-defined

### 8. IFRS13_Assessment Sheet
**Purpose**: Compliance and governance
**Key Fields to Review**:
- **Fair Value Hierarchy**: Level 1/2/3 determination
- **Data Observability**: Input classification
- **Principal Market**: Market selection rationale
- **Day-1 P&L**: Initial profit/loss check
- **Review Status**: Compliance validation

**Review Checklist**:
- [ ] Hierarchy level is appropriate
- [ ] Data observability is correctly assessed
- [ ] Principal market selection is documented
- [ ] Day-1 P&L is within tolerance
- [ ] Review status is complete

### 9. Assumptions_Judgements Sheet
**Purpose**: Key assumptions and rationale
**Key Fields to Review**:
- **Model Assumptions**: Pricing model parameters
- **Data Assumptions**: Market data choices
- **Methodology Choices**: Calculation approaches
- **Proxy Usage**: When proxies are used
- **Rationale**: Justification for assumptions

**Review Checklist**:
- [ ] Model assumptions are documented
- [ ] Data assumptions are reasonable
- [ ] Methodology choices are appropriate
- [ ] Proxy usage is justified
- [ ] Rationale is clear and complete

### 10. Audit_Log Sheet
**Purpose**: Complete calculation lineage
**Key Fields to Review**:
- **Calculation Steps**: Detailed calculation process
- **Model Versions**: Software and model versions
- **Data Sources**: Input data provenance
- **Validation Checks**: Quality assurance steps
- **Review History**: Review and approval trail

**Review Checklist**:
- [ ] Calculation steps are complete
- [ ] Model versions are current
- [ ] Data sources are documented
- [ ] Validation checks are performed
- [ ] Review history is complete

### 11. Appendix_Docs Sheet
**Purpose**: Model documentation and parameters
**Key Fields to Review**:
- **Model Documentation**: Pricing model descriptions
- **Parameter Values**: Model parameters used
- **Calibration Results**: Model calibration details
- **Validation Results**: Model validation outcomes
- **References**: Technical documentation

**Review Checklist**:
- [ ] Model documentation is complete
- [ ] Parameter values are reasonable
- [ ] Calibration results are documented
- [ ] Validation results are satisfactory
- [ ] References are current

## 🔍 Review Process

### Step 1: Initial Review
1. **Open Excel file** and verify all sheets are present
2. **Check Cover sheet** for basic information accuracy
3. **Review Instrument_Summary** for trade details
4. **Validate Data_Sources** for market data quality

### Step 2: Technical Review
1. **Examine Curves sheet** for curve construction
2. **Review Cashflows sheet** for payment calculations
3. **Analyze Results sheet** for present value accuracy
4. **Check Sensitivities sheet** for risk metrics

### Step 3: Compliance Review
1. **Review IFRS13_Assessment** for compliance status
2. **Examine Assumptions_Judgements** for key assumptions
3. **Check Audit_Log** for calculation lineage
4. **Validate Appendix_Docs** for model documentation

### Step 4: Final Validation
1. **Cross-check** results between sheets
2. **Verify** calculation consistency
3. **Confirm** compliance requirements
4. **Approve** for final use

## ⚠️ Common Issues to Watch For

### Data Quality Issues
- **Stale Data**: Market data older than 1 day
- **Missing Data**: Incomplete curve information
- **Inconsistent Data**: Mismatched timestamps
- **Proxy Data**: Unvalidated proxy usage

### Calculation Issues
- **Day Count Errors**: Incorrect day count fractions
- **Schedule Errors**: Wrong payment dates
- **Rate Errors**: Incorrect rate applications
- **Currency Errors**: Wrong currency conversions

### Compliance Issues
- **Hierarchy Errors**: Incorrect Level 1/2/3 classification
- **Market Errors**: Wrong principal market selection
- **P&L Errors**: Day-1 P&L outside tolerance
- **Documentation Errors**: Missing rationale

### Model Issues
- **Version Errors**: Outdated model versions
- **Parameter Errors**: Incorrect model parameters
- **Calibration Errors**: Failed model calibration
- **Validation Errors**: Model validation failures

## 📋 Review Checklist Template

### Pre-Review Setup
- [ ] Excel file opens without errors
- [ ] All sheets are present and accessible
- [ ] File is from trusted source
- [ ] Review environment is secure

### Data Review
- [ ] Market data is current and complete
- [ ] Curve construction is reasonable
- [ ] Data sources are documented
- [ ] Data quality is acceptable

### Calculation Review
- [ ] Payment schedules are correct
- [ ] Day count conventions are applied
- [ ] Present value calculations are accurate
- [ ] Risk metrics are reasonable

### Compliance Review
- [ ] IFRS-13 requirements are met
- [ ] Fair value hierarchy is correct
- [ ] Principal market is appropriate
- [ ] Day-1 P&L is within tolerance

### Documentation Review
- [ ] Assumptions are documented
- [ ] Rationale is provided
- [ ] Audit trail is complete
- [ ] Model documentation is current

### Final Approval
- [ ] All issues are resolved
- [ ] Results are validated
- [ ] Compliance is confirmed
- [ ] Documentation is complete

## 🚨 Escalation Criteria

### Immediate Escalation
- **Data Integrity Issues**: Suspected data manipulation
- **Model Failures**: Model calibration or validation failures
- **Compliance Violations**: IFRS-13 requirements not met
- **Security Breaches**: Unauthorized access or data exposure

### Management Review
- **Large P&L Movements**: Significant valuation changes
- **Model Changes**: New model implementations
- **Data Quality Issues**: Persistent data problems
- **Process Violations**: Workflow non-compliance

### Technical Review
- **Calculation Errors**: Mathematical errors in results
- **System Failures**: Technical system issues
- **Performance Issues**: Slow or failed calculations
- **Integration Issues**: System integration problems

## 📞 Support Contacts

### Technical Support
- **System Issues**: IT Support Team
- **Calculation Problems**: Quant Team
- **Data Issues**: Market Data Team
- **Model Issues**: Model Risk Team

### Compliance Support
- **IFRS-13 Questions**: Accounting Team
- **Regulatory Issues**: Compliance Team
- **Audit Support**: Internal Audit Team
- **Documentation**: Risk Management Team

---

**Note**: This guide should be used in conjunction with internal policies and procedures. Always consult with appropriate subject matter experts for complex or unusual situations.

