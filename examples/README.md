# Valuation Agent Examples

This directory contains sample trades and generated Excel packs for reference and testing.

## Sample Trades

### 1. Standard IRS (Interest Rate Swap)
- **Notional**: $10,000,000
- **Currency**: USD
- **Fixed Rate**: 5.00%
- **Floating Index**: SOFR
- **Tenor**: 2 years
- **Frequency**: Quarterly
- **Day Count**: ACT/360

### 2. Cross Currency Swap (CCS)
- **Notional USD**: $10,000,000
- **Notional EUR**: €9,000,000
- **Fixed Rate USD**: 5.00%
- **Floating Index USD**: SOFR
- **Floating Index EUR**: EURIBOR
- **Tenor**: 2 years
- **Frequency**: Quarterly
- **Day Count**: ACT/360

## Excel Pack Structure

Each example includes a complete Excel workbook with the following sheets:

1. **Cover**: Executive summary and metadata
2. **Instrument_Summary**: Trade details and parameters
3. **Data_Sources**: Market data and curve information
4. **Curves**: Discount and forward curve details
5. **Cashflows**: Payment schedule and calculations
6. **Results**: Present value breakdown and metrics
7. **Sensitivities**: Risk analysis and stress tests
8. **IFRS13_Assessment**: Compliance and governance
9. **Assumptions_Judgements**: Key assumptions and rationale
10. **Audit_Log**: Complete calculation lineage
11. **Appendix_Docs**: Model documentation and parameters

## Usage

### Generate Examples
```bash
cd api/examples
python generate_examples.py
```

### View Examples
- Open the generated Excel files in Microsoft Excel or compatible software
- Review the Quant Review Guide for detailed analysis instructions
- Use the examples as templates for your own valuations

## Quant Review Guide

See [Quant_Review_Guide.md](./Quant_Review_Guide.md) for detailed instructions on reviewing the Excel outputs.

