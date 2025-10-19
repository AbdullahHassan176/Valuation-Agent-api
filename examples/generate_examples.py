"""
Generate example trades and Excel packs for reference
"""

import requests
import time
import json
from datetime import datetime
from pathlib import Path


def create_irs_example():
    """Create standard IRS example"""
    return {
        "spec": {
            "notional": 10000000,  # $10M
            "ccy": "USD",
            "payFixed": True,
            "fixedRate": 0.05,  # 5%
            "floatIndex": "SOFR",
            "effective": "2024-01-01",
            "maturity": "2026-01-01",  # 2-year tenor
            "dcFixed": "ACT/360",
            "dcFloat": "ACT/360",
            "freqFixed": "Q",  # Quarterly
            "freqFloat": "Q",
            "calendar": "USD",
            "bdc": "MODIFIED_FOLLOWING"
        },
        "asOf": "2024-01-01",
        "marketDataProfile": "default",
        "approach": ["discount_curve"]
    }


def create_ccs_example():
    """Create standard CCS example"""
    return {
        "spec": {
            "notionalCcy1": 10000000,  # $10M USD
            "notionalCcy2": 9000000,   # €9M EUR
            "ccy1": "USD",
            "ccy2": "EUR",
            "payFixedCcy1": True,
            "fixedRateCcy1": 0.05,  # 5% USD
            "floatIndexCcy1": "SOFR",
            "floatIndexCcy2": "EURIBOR",
            "effective": "2024-01-01",
            "maturity": "2026-01-01",
            "dcCcy1": "ACT/360",
            "dcCcy2": "ACT/360",
            "freqCcy1": "Q",
            "freqCcy2": "Q",
            "calendar": "USD_EUR",
            "bdc": "MODIFIED_FOLLOWING",
            "reportingCcy": "USD"
        },
        "asOf": "2024-01-01",
        "marketDataProfile": "default",
        "approach": ["discount_curve"]
    }


def create_irs_with_xva_example():
    """Create IRS with XVA example"""
    base_irs = create_irs_example()
    base_irs["xva_config"] = {
        "compute_cva": True,
        "compute_dva": True,
        "compute_fva": True,
        "counterparty_credit_curve": {
            "name": "Counterparty_AA",
            "currency": "USD",
            "tenors": ["1Y", "2Y", "5Y"],
            "spreads": [100.0, 120.0, 150.0],
            "recovery_rate": 0.4
        },
        "own_credit_curve": {
            "name": "Own_AA",
            "currency": "USD",
            "tenors": ["1Y", "2Y", "5Y"],
            "spreads": [80.0, 100.0, 120.0],
            "recovery_rate": 0.4
        },
        "funding_curve": {
            "name": "Funding_Curve",
            "currency": "USD",
            "tenors": ["1Y", "2Y", "5Y"],
            "spreads": [50.0, 60.0, 70.0],
            "recovery_rate": 0.0
        },
        "csa_config": {
            "threshold": 500000.0,
            "minimum_transfer_amount": 100000.0,
            "rounding": 1000.0,
            "collateral_currency": "USD",
            "interest_rate": 0.02,
            "posting_frequency": "daily"
        }
    }
    return base_irs


def create_hw1f_example():
    """Create IRS with HW1F model example"""
    base_irs = create_irs_example()
    base_irs["approach"] = ["discount_curve", "HW1F-variance-matching"]
    return base_irs


def run_example(example_data, name, api_url="http://127.0.0.1:9000", backend_url="http://127.0.0.1:8000"):
    """Run example and generate Excel pack"""
    print(f"Creating {name} example...")
    
    try:
        # Create run
        response = requests.post(f"{api_url}/runs/", json=example_data)
        if response.status_code != 201:
            print(f"Failed to create {name}: {response.text}")
            return None
        
        run_data = response.json()
        run_id = run_data["id"]
        print(f"Created run {run_id}")
        
        # Wait for completion
        max_wait = 30
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = requests.get(f"{api_url}/runs/{run_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] == "completed":
                    break
                elif status_data["status"] == "failed":
                    print(f"Run {name} failed: {status_data.get('error_message', 'Unknown error')}")
                    return None
            time.sleep(1)
        else:
            print(f"Run {name} did not complete within timeout")
            return None
        
        # Generate Excel export
        print(f"Generating Excel export for {name}...")
        export_response = requests.get(f"{backend_url}/exports/{run_id}/excel")
        
        if export_response.status_code == 200:
            # Save Excel file
            filename = f"{name.replace(' ', '_').lower()}_example.xlsx"
            with open(filename, 'wb') as f:
                f.write(export_response.content)
            print(f"Saved Excel file: {filename}")
            return filename
        else:
            print(f"Failed to export Excel for {name}: {export_response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error creating {name}: {e}")
        return None


def main():
    """Generate all examples"""
    print("=== Valuation Agent Examples Generator ===")
    print(f"Generated at: {datetime.now().isoformat()}")
    print()
    
    # Ensure output directory exists
    output_dir = Path("generated_examples")
    output_dir.mkdir(exist_ok=True)
    
    examples = [
        ("Standard IRS", create_irs_example()),
        ("Cross Currency Swap", create_ccs_example()),
        ("IRS with XVA", create_irs_with_xva_example()),
        ("IRS with HW1F Model", create_hw1f_example()),
    ]
    
    generated_files = []
    
    for name, example_data in examples:
        filename = run_example(example_data, name)
        if filename:
            generated_files.append(filename)
        print()
    
    # Create summary
    print("=== Generation Summary ===")
    print(f"Generated {len(generated_files)} example files:")
    for filename in generated_files:
        print(f"  - {filename}")
    
    # Create metadata file
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "examples": [
            {
                "name": name,
                "filename": filename,
                "description": f"Example {name} with complete Excel pack"
            }
            for name, _ in examples
            for filename in generated_files
            if name.lower().replace(' ', '_') in filename
        ]
    }
    
    with open("generated_examples/metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nMetadata saved to: generated_examples/metadata.json")
    print("\nExamples generation complete!")


if __name__ == "__main__":
    main()

