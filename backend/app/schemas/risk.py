"""
Pydantic contracts for Vehicle Risk & Trust Intelligence Engine (Phase 12).
Defines strongly-typed schemas for risk factors, evidence summaries,
individual and batch risk analysis responses.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.valuation import ValuationRequestSchema


class RiskFactor(BaseModel):
    """
    Individual risk dimension assessment with weight, score, and mathematical evidence.
    """
    key: str = Field(..., description="Unique key for the risk factor (e.g. 'price_anomaly')")
    name: str = Field(..., description="Human-readable factor title (e.g. 'Price Anomaly')")
    score: int = Field(..., ge=0, le=100, description="Factor risk score from 0 (very low risk) to 100 (very high risk)")
    severity: str = Field(..., description="'VERY_LOW', 'LOW', 'MODERATE', 'HIGH', or 'VERY_HIGH'")
    weight: float = Field(..., ge=0.0, le=1.0, description="Relative weight in overall risk calculation")
    weighted_contribution: float = Field(..., ge=0.0, le=100.0, description="Weighted points contribution to overall score")
    confidence: str = Field(..., description="'HIGH', 'MEDIUM', 'LOW', or 'INSUFFICIENT'")
    evidence: List[str] = Field(default_factory=list, description="Factual supporting observations")
    interpretation: str = Field(..., description="Plain-language explanation of this factor's risk implication")


class RiskEvidenceSummary(BaseModel):
    """
    High-level snapshot of the underlying marketplace and dataset evidence.
    """
    comparables_count: int = Field(..., ge=0)
    market_evidence_density: str = Field(..., description="'HIGH', 'MEDIUM', 'LOW', or 'INSUFFICIENT'")
    data_completeness: float = Field(..., ge=0.0, le=1.0)
    source_diversity: str = Field(..., description="'HIGH', 'MEDIUM', 'LOW', or 'SINGLE_SOURCE'")
    sources_count: int = Field(..., ge=0)
    price_dispersion_pct: Optional[float] = None
    uncertainty_width_pct: Optional[float] = None


class RiskAnalysisResponse(BaseModel):
    """
    Comprehensive risk and trust assessment response.
    """
    risk_score: int = Field(..., ge=0, le=100, description="Composite market & evidence risk score (0-100)")
    risk_level: str = Field(
        ...,
        description="'VERY_LOW', 'LOW', 'MODERATE', 'HIGH', 'VERY_HIGH', or 'INSUFFICIENT_EVIDENCE'"
    )
    confidence: str = Field(..., description="'HIGH', 'MEDIUM', 'LOW', or 'INSUFFICIENT'")
    summary: str = Field(..., description="Executive summary of observable risk profile")
    recommendation: str = Field(..., description="Evidence-grounded next step advisory")
    factors: List[RiskFactor] = Field(..., description="All evaluated risk dimensions")
    positive_signals: List[str] = Field(default_factory=list, description="Favourable market and evidence indicators")
    risk_signals: List[str] = Field(default_factory=list, description="Elevated observable risk indicators")
    unknowns: List[str] = Field(..., description="Mandatory list of unverified physical condition factors")
    evidence_summary: RiskEvidenceSummary
    disclaimer: str = Field(
        default="This score reflects observable market, pricing, usage, and data evidence risks only. "
                "It is NOT a mechanical inspection, fraud probability, or guarantee of physical vehicle condition."
    )
    weights_used: Dict[str, float] = Field(..., description="Weights applied in composite score calculation")


class BatchRiskItem(BaseModel):
    """
    Individual vehicle risk summary in a batch evaluation.
    """
    vehicle_identifier: str = Field(..., description="Vehicle label or index")
    brand: str
    model: str
    year: int
    km_driven: int
    city: str
    estimated_value: float
    asking_price: Optional[float] = None
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    confidence: str
    top_risks: List[str] = Field(default_factory=list)
    top_positive_signals: List[str] = Field(default_factory=list)


class BatchRiskRequest(BaseModel):
    """
    Batch risk evaluation request for candidate vehicles (bounded to 10 vehicles max).
    """
    vehicles: List[ValuationRequestSchema] = Field(..., min_length=1, max_length=10)


class BatchRiskResponse(BaseModel):
    """
    Batch risk evaluation response.
    """
    total_vehicles: int
    results: List[BatchRiskItem]
    disclaimer: str = Field(
        default="Batch risk scores evaluate observable marketplace and data signals. Physical condition remains uninspected."
    )
