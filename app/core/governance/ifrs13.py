"""
IFRS-13 governance module for fair value hierarchy and compliance
"""
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum

from ...schemas.instrument import IRSSpec, CCSSpec
from ...schemas.run import PVBreakdown

class FairValueLevel(Enum):
    """IFRS-13 Fair Value Hierarchy Levels"""
    LEVEL_1 = "Level 1"  # Quoted prices in active markets
    LEVEL_2 = "Level 2"  # Observable inputs other than quoted prices
    LEVEL_3 = "Level 3"  # Unobservable inputs

class DataObservability(Enum):
    """Data observability classification"""
    OBSERVABLE = "observable"
    UNOBSERVABLE = "unobservable"
    PROXY = "proxy"

@dataclass
class DataSource:
    """Data source with observability classification"""
    name: str
    observability: DataObservability
    level: FairValueLevel
    description: str
    rationale: Optional[str] = None

@dataclass
class IFRS13Assessment:
    """IFRS-13 compliance assessment"""
    fair_value_level: FairValueLevel
    data_sources: List[DataSource]
    day1_pnl: float
    day1_pnl_tolerance: float
    day1_pnl_within_tolerance: bool
    principal_market: str
    valuation_technique: str
    key_inputs: List[str]
    unobservable_inputs: List[str]
    needs_review: bool
    review_reason: Optional[str] = None
    reviewer_rationale: Optional[str] = None
    ready_for_export: bool = False
    assessed_at: datetime = None

    def __post_init__(self):
        if self.assessed_at is None:
            self.assessed_at = datetime.utcnow()

class IFRS13Governance:
    """IFRS-13 governance and compliance checker"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default governance configuration"""
        return {
            "day1_pnl_tolerance": 0.01,  # 1% tolerance for day-1 P&L
            "principal_market": "USD",
            "level2_threshold": 0.05,  # 5% threshold for Level 2 classification
            "level3_threshold": 0.10,  # 10% threshold for Level 3 classification
        }
    
    def assess_fair_value_level(self, pv_breakdown: PVBreakdown, spec: Any) -> FairValueLevel:
        """
        Determine fair value hierarchy level based on data observability
        
        Args:
            pv_breakdown: Present value breakdown
            spec: Instrument specification
            
        Returns:
            Fair value hierarchy level
        """
        # Analyze data sources and their observability
        data_sources = self._analyze_data_sources(pv_breakdown, spec)
        
        # Check for Level 1 (quoted prices in active markets)
        if self._has_level1_data(data_sources):
            return FairValueLevel.LEVEL_1
        
        # Check for Level 3 (unobservable inputs)
        if self._has_unobservable_inputs(data_sources):
            return FairValueLevel.LEVEL_3
        
        # Default to Level 2 (observable inputs other than quoted prices)
        return FairValueLevel.LEVEL_2
    
    def _analyze_data_sources(self, pv_breakdown: PVBreakdown, spec: Any) -> List[DataSource]:
        """Analyze data sources and their observability"""
        data_sources = []
        
        # Market data sources
        if "usd_ois_quotes" in pv_breakdown.market_data_hash.lower():
            data_sources.append(DataSource(
                name="USD OIS Quotes",
                observability=DataObservability.OBSERVABLE,
                level=FairValueLevel.LEVEL_2,
                description="USD OIS swap quotes from market data providers"
            ))
        
        if "fx_quotes" in pv_breakdown.market_data_hash.lower():
            data_sources.append(DataSource(
                name="USD/EUR FX Quotes",
                observability=DataObservability.OBSERVABLE,
                level=FairValueLevel.LEVEL_2,
                description="USD/EUR spot and forward quotes"
            ))
        
        # Model inputs
        if "dcf" in pv_breakdown.model_hash.lower():
            data_sources.append(DataSource(
                name="DCF Model",
                observability=DataObservability.OBSERVABLE,
                level=FairValueLevel.LEVEL_2,
                description="Discounted cash flow pricing model"
            ))
        
        # Check for unobservable inputs
        if hasattr(spec, 'fixedRate') and spec.fixedRate is None:
            data_sources.append(DataSource(
                name="Fixed Rate",
                observability=DataObservability.UNOBSERVABLE,
                level=FairValueLevel.LEVEL_3,
                description="Fixed rate not provided - requires market rate",
                rationale="Market rate required for pricing"
            ))
        
        return data_sources
    
    def _has_level1_data(self, data_sources: List[DataSource]) -> bool:
        """Check if any data sources are Level 1"""
        return any(source.level == FairValueLevel.LEVEL_1 for source in data_sources)
    
    def _has_unobservable_inputs(self, data_sources: List[DataSource]) -> bool:
        """Check if any data sources are unobservable"""
        return any(source.observability == DataObservability.UNOBSERVABLE for source in data_sources)
    
    def calculate_day1_pnl(self, pv_breakdown: PVBreakdown, spec: Any) -> float:
        """
        Calculate day-1 P&L vs par quotes
        
        Args:
            pv_breakdown: Present value breakdown
            spec: Instrument specification
            
        Returns:
            Day-1 P&L as a percentage
        """
        # For a par swap, PV should be close to zero
        # Day-1 P&L is the deviation from par
        total_pv = pv_breakdown.total_pv
        
        # Get notional for percentage calculation
        notional = getattr(spec, 'notional', 1.0)
        
        # Calculate day-1 P&L as percentage of notional
        day1_pnl = abs(total_pv) / notional if notional > 0 else 0.0
        
        return day1_pnl
    
    def check_day1_pnl_tolerance(self, day1_pnl: float) -> bool:
        """
        Check if day-1 P&L is within tolerance
        
        Args:
            day1_pnl: Day-1 P&L as percentage
            
        Returns:
            True if within tolerance
        """
        tolerance = self.config.get("day1_pnl_tolerance", 0.01)
        return day1_pnl <= tolerance
    
    def determine_principal_market(self, spec: Any) -> str:
        """
        Determine principal market for the instrument
        
        Args:
            spec: Instrument specification
            
        Returns:
            Principal market identifier
        """
        # Default to configured principal market
        principal_market = self.config.get("principal_market", "USD")
        
        # Override based on instrument currency
        if hasattr(spec, 'ccy'):
            if spec.ccy == "EUR":
                principal_market = "EUR"
            elif spec.ccy == "USD":
                principal_market = "USD"
        
        return principal_market
    
    def assess_compliance(self, pv_breakdown: PVBreakdown, spec: Any) -> IFRS13Assessment:
        """
        Perform complete IFRS-13 compliance assessment
        
        Args:
            pv_breakdown: Present value breakdown
            spec: Instrument specification
            
        Returns:
            IFRS-13 assessment
        """
        # Determine fair value level
        fair_value_level = self.assess_fair_value_level(pv_breakdown, spec)
        
        # Analyze data sources
        data_sources = self._analyze_data_sources(pv_breakdown, spec)
        
        # Calculate day-1 P&L
        day1_pnl = self.calculate_day1_pnl(pv_breakdown, spec)
        day1_pnl_tolerance = self.config.get("day1_pnl_tolerance", 0.01)
        day1_pnl_within_tolerance = self.check_day1_pnl_tolerance(day1_pnl)
        
        # Determine principal market
        principal_market = self.determine_principal_market(spec)
        
        # Determine valuation technique
        valuation_technique = "Discounted Cash Flow"
        
        # Identify key inputs
        key_inputs = [
            "Market interest rates",
            "FX forward rates",
            "Payment schedules",
            "Day count conventions"
        ]
        
        # Identify unobservable inputs
        unobservable_inputs = []
        for source in data_sources:
            if source.observability == DataObservability.UNOBSERVABLE:
                unobservable_inputs.append(source.name)
        
        # Determine if review is needed
        needs_review = False
        review_reason = None
        
        if fair_value_level == FairValueLevel.LEVEL_3:
            needs_review = True
            review_reason = "Level 3 fair value - unobservable inputs require rationale"
        elif not day1_pnl_within_tolerance:
            needs_review = True
            review_reason = f"Day-1 P&L {day1_pnl:.2%} exceeds tolerance {day1_pnl_tolerance:.2%}"
        elif unobservable_inputs:
            needs_review = True
            review_reason = "Unobservable inputs require rationale"
        
        return IFRS13Assessment(
            fair_value_level=fair_value_level,
            data_sources=data_sources,
            day1_pnl=day1_pnl,
            day1_pnl_tolerance=day1_pnl_tolerance,
            day1_pnl_within_tolerance=day1_pnl_within_tolerance,
            principal_market=principal_market,
            valuation_technique=valuation_technique,
            key_inputs=key_inputs,
            unobservable_inputs=unobservable_inputs,
            needs_review=needs_review,
            review_reason=review_reason,
            ready_for_export=not needs_review
        )
    
    def update_assessment_with_rationale(self, assessment: IFRS13Assessment, rationale: str) -> IFRS13Assessment:
        """
        Update assessment with reviewer rationale
        
        Args:
            assessment: Current assessment
            rationale: Reviewer rationale
            
        Returns:
            Updated assessment
        """
        assessment.reviewer_rationale = rationale
        assessment.ready_for_export = True
        assessment.needs_review = False
        
        return assessment

