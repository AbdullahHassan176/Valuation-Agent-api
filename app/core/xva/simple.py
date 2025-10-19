from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import numpy as np
from ...schemas.instrument import IRSSpec, CCSSpec
from ...schemas.run import PVBreakdown, XVAConfig, CSA


def calculate_xva_light(
    base_pv: float,
    spec: IRSSpec | CCSSpec,
    xva_config: Optional[XVAConfig] = None,
    csa: Optional[CSA] = None
) -> Dict[str, float]:
    """
    Calculate CVA/DVA/FVA (light) using proxy credit curves and CSA inputs.
    
    Args:
        base_pv: Base present value from pricing engine
        spec: Instrument specification
        xva_config: XVA configuration parameters
        csa: Credit Support Annex details
        
    Returns:
        Dictionary with XVA components
    """
    if not xva_config:
        xva_config = XVAConfig()
    
    if not csa:
        raise ValueError("NEEDS_INPUT: CSA details required for XVA calculation")
    
    # Extract parameters
    notional = spec.notional if hasattr(spec, 'notional') else spec.notionalBase
    maturity_years = (spec.maturity - spec.effective).days / 365.25
    
    # Proxy credit curves (simplified)
    counterparty_pd = xva_config.counterparty_pd or 0.02  # 2% annual PD
    own_pd = xva_config.own_pd or 0.01  # 1% annual PD
    lgd = xva_config.lgd or 0.40  # 40% LGD
    funding_spread = xva_config.funding_spread or 0.005  # 50bp funding spread
    
    # Calculate expected exposure profile (simplified)
    ee_profile = calculate_ee_profile(notional, maturity_years, base_pv)
    
    # Calculate CVA
    cva = calculate_cva(ee_profile, counterparty_pd, lgd, maturity_years)
    
    # Calculate DVA
    dva = calculate_dva(ee_profile, own_pd, lgd, maturity_years)
    
    # Calculate FVA
    fva = calculate_fva(ee_profile, funding_spread, maturity_years)
    
    # Calculate KVA (simplified)
    kva = calculate_kva(notional, xva_config.kva_rate or 0.12, maturity_years)
    
    # Total XVA
    total_xva = cva + dva + fva + kva
    
    return {
        "cva": cva,
        "dva": dva,
        "fva": fva,
        "kva": kva,
        "total_xva": total_xva,
        "base_pv": base_pv,
        "adjusted_pv": base_pv + total_xva
    }


def calculate_ee_profile(notional: float, maturity_years: float, base_pv: float) -> List[float]:
    """
    Calculate expected exposure profile using simplified approach.
    
    Args:
        notional: Notional amount
        maturity_years: Maturity in years
        base_pv: Base present value
        
    Returns:
        List of expected exposures over time
    """
    # Simplified EE profile: starts at base PV, decays to zero
    time_points = np.linspace(0, maturity_years, int(maturity_years * 4) + 1)  # Quarterly
    ee_values = []
    
    for t in time_points:
        # Simple decay model: EE = base_pv * exp(-t/2)
        ee = abs(base_pv) * np.exp(-t / 2.0)
        ee_values.append(ee)
    
    return ee_values


def calculate_cva(ee_profile: List[float], pd: float, lgd: float, maturity_years: float) -> float:
    """
    Calculate Credit Value Adjustment.
    
    Args:
        ee_profile: Expected exposure profile
        pd: Probability of default
        lgd: Loss given default
        maturity_years: Maturity in years
        
    Returns:
        CVA value
    """
    if not ee_profile:
        return 0.0
    
    # Simplified CVA calculation
    # CVA = sum(EE(t) * PD(t) * LGD * discount_factor(t))
    cva = 0.0
    time_points = np.linspace(0, maturity_years, len(ee_profile))
    
    for i, ee in enumerate(ee_profile):
        if i == 0:
            continue
        
        t = time_points[i]
        dt = time_points[i] - time_points[i-1]
        
        # Simplified: constant PD and discount rate
        pd_increment = pd * dt
        discount_factor = np.exp(-0.05 * t)  # 5% discount rate
        
        cva += ee * pd_increment * lgd * discount_factor
    
    return cva


def calculate_dva(ee_profile: List[float], pd: float, lgd: float, maturity_years: float) -> float:
    """
    Calculate Debit Value Adjustment.
    
    Args:
        ee_profile: Expected exposure profile
        pd: Own probability of default
        lgd: Loss given default
        maturity_years: Maturity in years
        
    Returns:
        DVA value (typically negative)
    """
    # DVA is similar to CVA but with own credit risk
    # For simplicity, use same calculation as CVA but with opposite sign
    dva = -calculate_cva(ee_profile, pd, lgd, maturity_years)
    return dva


def calculate_fva(ee_profile: List[float], funding_spread: float, maturity_years: float) -> float:
    """
    Calculate Funding Value Adjustment.
    
    Args:
        ee_profile: Expected exposure profile
        funding_spread: Funding spread
        maturity_years: Maturity in years
        
    Returns:
        FVA value
    """
    if not ee_profile:
        return 0.0
    
    # Simplified FVA calculation
    # FVA = sum(EE(t) * funding_spread * discount_factor(t))
    fva = 0.0
    time_points = np.linspace(0, maturity_years, len(ee_profile))
    
    for i, ee in enumerate(ee_profile):
        if i == 0:
            continue
        
        t = time_points[i]
        dt = time_points[i] - time_points[i-1]
        
        discount_factor = np.exp(-0.05 * t)  # 5% discount rate
        fva += ee * funding_spread * dt * discount_factor
    
    return fva


def calculate_kva(notional: float, kva_rate: float, maturity_years: float) -> float:
    """
    Calculate Capital Value Adjustment.
    
    Args:
        notional: Notional amount
        kva_rate: KVA rate (capital cost)
        maturity_years: Maturity in years
        
    Returns:
        KVA value
    """
    # Simplified KVA: proportional to notional and time
    # KVA = notional * kva_rate * maturity_years * average_capital_ratio
    capital_ratio = 0.08  # 8% capital ratio
    kva = notional * kva_rate * maturity_years * capital_ratio
    return kva


def apply_csa_benefits(xva_components: Dict[str, float], csa: CSA) -> Dict[str, float]:
    """
    Apply CSA benefits to XVA calculations.
    
    Args:
        xva_components: XVA components before CSA
        csa: Credit Support Annex details
        
    Returns:
        XVA components after CSA benefits
    """
    # CSA reduces exposure through collateral
    collateral_threshold = csa.threshold or 0.0
    collateral_amount = csa.collateral_amount or 0.0
    
    # Simple CSA benefit: reduce exposure by collateral amount
    csa_benefit = min(collateral_amount, abs(xva_components["base_pv"]))
    
    # Apply benefit proportionally to CVA and FVA
    benefit_ratio = csa_benefit / abs(xva_components["base_pv"]) if xva_components["base_pv"] != 0 else 0
    
    adjusted_components = xva_components.copy()
    adjusted_components["cva"] *= (1 - benefit_ratio)
    adjusted_components["fva"] *= (1 - benefit_ratio)
    adjusted_components["total_xva"] = (
        adjusted_components["cva"] + 
        adjusted_components["dva"] + 
        adjusted_components["fva"] + 
        adjusted_components["kva"]
    )
    adjusted_components["adjusted_pv"] = adjusted_components["base_pv"] + adjusted_components["total_xva"]
    
    return adjusted_components
