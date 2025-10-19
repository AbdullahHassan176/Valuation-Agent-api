"""
Simple XVA (CVA/DVA/FVA) computation module with proxy credit curves and CSA inputs.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import date, datetime
import math


@dataclass
class EEPoint:
    """Expected Exposure point in time."""
    date: date
    expected_exposure: float
    expected_positive_exposure: float
    expected_negative_exposure: float


@dataclass
class EEGrid:
    """Expected Exposure grid for XVA calculations."""
    points: List[EEPoint]
    currency: str
    calculation_date: date


@dataclass
class CreditCurve:
    """Proxy credit curve for CVA/DVA calculations."""
    name: str
    currency: str
    tenors: List[str]  # e.g., ["1Y", "2Y", "5Y", "10Y"]
    spreads: List[float]  # Credit spreads in basis points
    recovery_rate: float = 0.4  # Default recovery rate


@dataclass
class CSAConfig:
    """Credit Support Annex configuration."""
    threshold: float = 0.0  # Threshold amount
    minimum_transfer_amount: float = 0.0  # MTA
    rounding: float = 0.0  # Rounding amount
    collateral_currency: str = "USD"
    interest_rate: float = 0.0  # Interest rate on posted collateral
    posting_frequency: str = "daily"  # daily, weekly, monthly


@dataclass
class XVAConfig:
    """XVA calculation configuration."""
    compute_cva: bool = True
    compute_dva: bool = True
    compute_fva: bool = True
    counterparty_credit_curve: Optional[CreditCurve] = None
    own_credit_curve: Optional[CreditCurve] = None
    funding_curve: Optional[CreditCurve] = None
    csa_config: Optional[CSAConfig] = None


@dataclass
class XVAResults:
    """XVA calculation results."""
    cva: float = 0.0
    dva: float = 0.0
    fva: float = 0.0
    total_xva: float = 0.0
    currency: str = "USD"
    calculation_date: date = None
    details: Dict[str, Any] = None


def compute_cva(
    ee_grid: EEGrid,
    credit_curve: CreditCurve,
    recovery_rate: float = 0.4
) -> float:
    """
    Compute Credit Value Adjustment (CVA).
    
    CVA = (1 - R) * Σ[EE(t) * PD(t-1,t) * DF(t)]
    
    Args:
        ee_grid: Expected exposure grid
        credit_curve: Counterparty credit curve
        recovery_rate: Recovery rate (default 0.4)
        
    Returns:
        CVA amount
    """
    if not ee_grid.points or not credit_curve.tenors:
        return 0.0
    
    cva = 0.0
    lgd = 1.0 - recovery_rate  # Loss Given Default
    
    # Convert credit spreads to hazard rates
    hazard_rates = _spreads_to_hazard_rates(credit_curve.spreads)
    
    for i, point in enumerate(ee_grid.points):
        if i == 0:
            continue  # Skip first point (no previous period)
            
        # Get time to maturity
        t_prev = (ee_grid.points[i-1].date - ee_grid.calculation_date).days / 365.25
        t_curr = (point.date - ee_grid.calculation_date).days / 365.25
        
        # Interpolate hazard rate
        hazard_rate = _interpolate_hazard_rate(t_curr, credit_curve.tenors, hazard_rates)
        
        # Probability of default in period [t_prev, t_curr]
        pd_period = 1.0 - math.exp(-hazard_rate * (t_curr - t_prev))
        
        # Discount factor (simplified - would use risk-free curve in practice)
        df = math.exp(-0.05 * t_curr)  # 5% risk-free rate assumption
        
        # CVA contribution
        cva += point.expected_positive_exposure * pd_period * df
    
    return lgd * cva


def compute_dva(
    ee_grid: EEGrid,
    own_credit_curve: CreditCurve,
    recovery_rate: float = 0.4
) -> float:
    """
    Compute Debit Value Adjustment (DVA).
    
    DVA = (1 - R) * Σ[ENE(t) * PD_own(t-1,t) * DF(t)]
    
    Args:
        ee_grid: Expected exposure grid
        own_credit_curve: Own credit curve
        recovery_rate: Recovery rate (default 0.4)
        
    Returns:
        DVA amount
    """
    if not ee_grid.points or not own_credit_curve.tenors:
        return 0.0
    
    dva = 0.0
    lgd = 1.0 - recovery_rate
    
    # Convert credit spreads to hazard rates
    hazard_rates = _spreads_to_hazard_rates(own_credit_curve.spreads)
    
    for i, point in enumerate(ee_grid.points):
        if i == 0:
            continue
            
        t_prev = (ee_grid.points[i-1].date - ee_grid.calculation_date).days / 365.25
        t_curr = (point.date - ee_grid.calculation_date).days / 365.25
        
        # Interpolate hazard rate
        hazard_rate = _interpolate_hazard_rate(t_curr, own_credit_curve.tenors, hazard_rates)
        
        # Probability of default in period
        pd_period = 1.0 - math.exp(-hazard_rate * (t_curr - t_prev))
        
        # Discount factor
        df = math.exp(-0.05 * t_curr)
        
        # DVA contribution (using negative exposure)
        dva += abs(point.expected_negative_exposure) * pd_period * df
    
    return lgd * dva


def compute_fva(
    ee_grid: EEGrid,
    funding_curve: CreditCurve,
    csa_config: Optional[CSAConfig] = None
) -> float:
    """
    Compute Funding Value Adjustment (FVA).
    
    FVA = Σ[E(E(t)) * Funding_Spread(t) * DF(t)]
    
    Args:
        ee_grid: Expected exposure grid
        funding_curve: Funding curve
        csa_config: CSA configuration for collateral benefits
        
    Returns:
        FVA amount
    """
    if not ee_grid.points or not funding_curve.tenors:
        return 0.0
    
    fva = 0.0
    
    # Convert funding spreads to rates
    funding_rates = [s / 10000.0 for s in funding_curve.spreads]  # Convert bp to decimal
    
    for i, point in enumerate(ee_grid.points):
        if i == 0:
            continue
            
        t_prev = (ee_grid.points[i-1].date - ee_grid.calculation_date).days / 365.25
        t_curr = (point.date - ee_grid.calculation_date).days / 365.25
        
        # Interpolate funding rate
        funding_rate = _interpolate_rate(t_curr, funding_curve.tenors, funding_rates)
        
        # Apply CSA benefits if available
        if csa_config and csa_config.interest_rate > 0:
            # Collateral reduces funding cost only for exposures above threshold
            if abs(point.expected_exposure) > csa_config.threshold:
                # Only the excess above threshold is subject to funding cost
                excess_exposure = abs(point.expected_exposure) - csa_config.threshold
                funding_rate = funding_rate * (excess_exposure / abs(point.expected_exposure))
            else:
                # Below threshold, no funding cost
                funding_rate = 0
        
        # Discount factor
        df = math.exp(-0.05 * t_curr)
        
        # FVA contribution
        fva += abs(point.expected_exposure) * funding_rate * df * (t_curr - t_prev)
    
    return fva


def compute_xva(
    ee_grid: EEGrid,
    xva_config: XVAConfig
) -> XVAResults:
    """
    Compute comprehensive XVA (CVA + DVA + FVA).
    
    Args:
        ee_grid: Expected exposure grid
        xva_config: XVA configuration
        
    Returns:
        Complete XVA results
    """
    results = XVAResults(
        currency=ee_grid.currency,
        calculation_date=ee_grid.calculation_date,
        details={}
    )
    
    # Compute CVA
    if xva_config.compute_cva and xva_config.counterparty_credit_curve:
        results.cva = compute_cva(
            ee_grid,
            xva_config.counterparty_credit_curve,
            xva_config.counterparty_credit_curve.recovery_rate
        )
        results.details['cva'] = {
            'counterparty_curve': xva_config.counterparty_credit_curve.name,
            'recovery_rate': xva_config.counterparty_credit_curve.recovery_rate
        }
    
    # Compute DVA
    if xva_config.compute_dva and xva_config.own_credit_curve:
        results.dva = compute_dva(
            ee_grid,
            xva_config.own_credit_curve,
            xva_config.own_credit_curve.recovery_rate
        )
        results.details['dva'] = {
            'own_curve': xva_config.own_credit_curve.name,
            'recovery_rate': xva_config.own_credit_curve.recovery_rate
        }
    
    # Compute FVA
    if xva_config.compute_fva and xva_config.funding_curve:
        results.fva = compute_fva(
            ee_grid,
            xva_config.funding_curve,
            xva_config.csa_config
        )
        results.details['fva'] = {
            'funding_curve': xva_config.funding_curve.name,
            'csa_applied': xva_config.csa_config is not None
        }
    
    # Total XVA
    results.total_xva = results.cva + results.dva + results.fva
    
    return results


def create_synthetic_ee_grid(
    start_date: date,
    end_date: date,
    frequency: str = "monthly",
    peak_exposure: float = 1000000.0,
    currency: str = "USD"
) -> EEGrid:
    """
    Create a synthetic expected exposure grid for testing.
    
    Args:
        start_date: Start date
        end_date: End date
        frequency: Grid frequency (monthly, quarterly, yearly)
        peak_exposure: Peak exposure amount
        currency: Currency
        
    Returns:
        Synthetic EE grid
    """
    points = []
    current_date = start_date
    
    # Determine date increment
    if frequency == "monthly":
        from dateutil.relativedelta import relativedelta
        delta = relativedelta(months=1)
    elif frequency == "quarterly":
        from dateutil.relativedelta import relativedelta
        delta = relativedelta(months=3)
    elif frequency == "yearly":
        from dateutil.relativedelta import relativedelta
        delta = relativedelta(years=1)
    else:
        from dateutil.relativedelta import relativedelta
        delta = relativedelta(months=1)
    
    # Create monotonic exposure profile (peak in middle)
    total_days = (end_date - start_date).days
    mid_point = total_days / 2
    
    while current_date <= end_date:
        days_from_start = (current_date - start_date).days
        
        # Create bell curve exposure profile
        if days_from_start <= mid_point:
            # Rising phase
            exposure_factor = days_from_start / mid_point
        else:
            # Declining phase
            exposure_factor = (total_days - days_from_start) / mid_point
        
        # Add some randomness
        import random
        noise = random.uniform(0.8, 1.2)
        exposure = peak_exposure * exposure_factor * noise
        
        # Split into positive and negative
        # For testing, create some negative exposures
        if exposure >= 0:
            ee_pos = exposure
            ee_neg = -exposure * 0.3  # 30% negative exposure for testing
        else:
            ee_pos = -exposure * 0.3  # 30% positive exposure for testing
            ee_neg = exposure
        
        points.append(EEPoint(
            date=current_date,
            expected_exposure=exposure,
            expected_positive_exposure=ee_pos,
            expected_negative_exposure=ee_neg
        ))
        
        current_date += delta
    
    return EEGrid(
        points=points,
        currency=currency,
        calculation_date=start_date
    )


def create_proxy_credit_curve(
    name: str,
    currency: str,
    base_spread: float = 100.0,  # Base spread in bp
    curve_shape: str = "flat"  # flat, upward, downward
) -> CreditCurve:
    """
    Create a proxy credit curve for testing.
    
    Args:
        name: Curve name
        currency: Currency
        base_spread: Base credit spread in bp
        curve_shape: Curve shape (flat, upward, downward)
        
    Returns:
        Proxy credit curve
    """
    tenors = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y"]
    spreads = []
    
    for i, tenor in enumerate(tenors):
        if curve_shape == "flat":
            spread = base_spread
        elif curve_shape == "upward":
            # Upward sloping curve
            spread = base_spread + (i * 10)  # +10bp per tenor
        elif curve_shape == "downward":
            # Downward sloping curve
            spread = base_spread - (i * 5)  # -5bp per tenor
        else:
            spread = base_spread
        
        spreads.append(max(10.0, spread))  # Minimum 10bp
    
    return CreditCurve(
        name=name,
        currency=currency,
        tenors=tenors,
        spreads=spreads,
        recovery_rate=0.4
    )


def _spreads_to_hazard_rates(spreads: List[float]) -> List[float]:
    """Convert credit spreads to hazard rates."""
    return [s / 10000.0 for s in spreads]  # Convert bp to decimal


def _interpolate_hazard_rate(
    time: float,
    tenors: List[str],
    hazard_rates: List[float]
) -> float:
    """Interpolate hazard rate for given time."""
    # Convert tenors to years
    tenor_years = [_tenor_to_years(t) for t in tenors]
    
    if time <= tenor_years[0]:
        return hazard_rates[0]
    elif time >= tenor_years[-1]:
        return hazard_rates[-1]
    else:
        # Linear interpolation
        for i in range(len(tenor_years) - 1):
            if tenor_years[i] <= time <= tenor_years[i + 1]:
                weight = (time - tenor_years[i]) / (tenor_years[i + 1] - tenor_years[i])
                return hazard_rates[i] + weight * (hazard_rates[i + 1] - hazard_rates[i])
    
    return hazard_rates[-1]


def _interpolate_rate(
    time: float,
    tenors: List[str],
    rates: List[float]
) -> float:
    """Interpolate rate for given time."""
    # Convert tenors to years
    tenor_years = [_tenor_to_years(t) for t in tenors]
    
    if time <= tenor_years[0]:
        return rates[0]
    elif time >= tenor_years[-1]:
        return rates[-1]
    else:
        # Linear interpolation
        for i in range(len(tenor_years) - 1):
            if tenor_years[i] <= time <= tenor_years[i + 1]:
                weight = (time - tenor_years[i]) / (tenor_years[i + 1] - tenor_years[i])
                return rates[i] + weight * (rates[i + 1] - rates[i])
    
    return rates[-1]


def _tenor_to_years(tenor: str) -> float:
    """Convert tenor string to years."""
    if tenor.endswith("M"):
        return float(tenor[:-1]) / 12.0
    elif tenor.endswith("Y"):
        return float(tenor[:-1])
    else:
        return 0.0
