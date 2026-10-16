"""
AutoValue Vehicle Risk & Trust Intelligence Engine (Phase 12).
Computes deterministic, evidence-grounded observable market, pricing, usage,
and dataset risk scores across 9 transparent dimensions.
"""
from typing import Dict, Any, List, Optional
import statistics
import logging

from backend.app.schemas.risk import (
    RiskFactor,
    RiskEvidenceSummary,
    RiskAnalysisResponse,
    BatchRiskItem,
    BatchRiskResponse
)
from backend.app.schemas.valuation import ValuationRequestSchema, ValuationResponse
from backend.app.services.data_confidence_service import data_confidence_service
from backend.app.services.valuation_service import valuation_service

logger = logging.getLogger("autovalue.risk_service")


class RiskService:
    """
    Evaluates observable market, pricing, usage, and evidence risks without making
    unverified physical condition claims.
    """

    RISK_WEIGHTS: Dict[str, float] = {
        "price_anomaly": 0.20,
        "mileage_usage": 0.15,
        "vehicle_age": 0.10,
        "market_liquidity": 0.15,
        "data_quality": 0.10,
        "market_evidence": 0.10,
        "valuation_uncertainty": 0.10,
        "price_dispersion": 0.05,
        "source_concentration": 0.05,
    }

    UNVERIFIED_PHYSICAL_FACTORS: List[str] = [
        "Engine internal mechanical condition and compression",
        "Transmission, clutch, and gearbox health",
        "Structural chassis integrity and collision repair history",
        "Flood damage and water immersion history",
        "Odometer rollback and tampering verification",
        "Tyre tread depth, wheel alignment, and suspension wear",
        "Braking system and rotor/pad thickness",
        "High-voltage battery pack degradation (for EV/Hybrid)",
        "Authorized service and maintenance documentation"
    ]

    @staticmethod
    def _map_severity(score: int) -> str:
        if score <= 19:
            return "VERY_LOW"
        elif score <= 39:
            return "LOW"
        elif score <= 59:
            return "MODERATE"
        elif score <= 79:
            return "HIGH"
        else:
            return "VERY_HIGH"

    def evaluate_risk(
        self,
        vehicle_data: Any,
        valuation_response: ValuationResponse
    ) -> RiskAnalysisResponse:
        """
        Executes end-to-end deterministic risk evaluation across all 9 dimensions.
        """
        if hasattr(vehicle_data, "model_dump"):
            vehicle_data = vehicle_data.model_dump()
        elif not isinstance(vehicle_data, dict):
            vehicle_data = dict(vehicle_data)

        asking_price = vehicle_data.get("asking_price")
        if asking_price is not None:
            try:
                asking_price = float(asking_price)
                if asking_price <= 0:
                    asking_price = None
            except (ValueError, TypeError):
                asking_price = None

        year = int(vehicle_data.get("year", 2020))
        km_driven = int(vehicle_data.get("km_driven", 0))
        ref_year = 2024
        car_age = max(0, ref_year - year)
        km_per_year = km_driven / max(1, car_age)

        est_val = valuation_response.valuation.estimated_value
        m_interval = valuation_response.valuation.model_interval
        interval_low = m_interval.interval_low if m_interval else None
        interval_high = m_interval.interval_high if m_interval else None

        market_stats = valuation_response.market
        comparables = valuation_response.comparables or []
        comp_count = len(comparables)

        # Handle extreme sparse data edge case
        if comp_count == 0 and market_stats.median is None:
            return self._build_insufficient_evidence_response(vehicle_data, valuation_response)

        factors: List[RiskFactor] = []

        # 1. Price Anomaly Risk (20%)
        f_price = self._evaluate_price_anomaly(
            asking_price=asking_price,
            estimated_value=est_val,
            market_median=market_stats.median,
            market_p25=market_stats.p25,
            market_p75=market_stats.p75,
            interval_low=interval_low,
            interval_high=interval_high
        )
        factors.append(f_price)

        # 2. Mileage / Usage Risk (15%)
        comp_kms = [c.km_driven for c in comparables if getattr(c, "km_driven", None) is not None]
        comp_median_km = float(statistics.median(comp_kms)) if comp_kms else None
        f_mileage = self._evaluate_mileage_usage(
            km_driven=km_driven,
            car_age=car_age,
            km_per_year=km_per_year,
            comp_median_km=comp_median_km
        )
        factors.append(f_mileage)

        # 3. Vehicle Age / Depreciation Risk (10%)
        f_age = self._evaluate_vehicle_age(year=year, car_age=car_age)
        factors.append(f_age)

        # 4. Market Liquidity Risk (15%)
        f_liquidity = self._evaluate_market_liquidity(
            comparable_count=comp_count,
            city=vehicle_data.get("city", "National")
        )
        factors.append(f_liquidity)

        # 5. Data Quality Risk (10%)
        f_data = self._evaluate_data_quality(vehicle_data=vehicle_data)
        factors.append(f_data)

        # 6. Market Evidence Risk (10%)
        f_evidence = self._evaluate_market_evidence(
            comparable_count=comp_count,
            estimated_value=est_val,
            market_median=market_stats.median
        )
        factors.append(f_evidence)

        # 7. Valuation Uncertainty Risk (10%)
        f_uncertainty = self._evaluate_valuation_uncertainty(
            estimated_value=est_val,
            interval_low=interval_low,
            interval_high=interval_high
        )
        factors.append(f_uncertainty)

        # 8. Price Dispersion Risk (5%)
        comp_prices = [c.price for c in comparables if getattr(c, "price", None) is not None]
        f_dispersion = self._evaluate_price_dispersion(
            market_median=market_stats.median,
            market_p25=market_stats.p25,
            market_p75=market_stats.p75,
            comparable_prices=comp_prices
        )
        factors.append(f_dispersion)

        # 9. Source Concentration Risk (5%)
        comp_sources = [getattr(c, "source", "AutoValue Portal") for c in comparables]
        f_source = self._evaluate_source_concentration(
            comparable_sources=comp_sources,
            comparable_count=comp_count
        )
        factors.append(f_source)

        # Calculate composite risk score
        raw_score = sum(f.weighted_contribution for f in factors)
        composite_score = int(round(max(0.0, min(100.0, raw_score))))
        risk_level = self._map_severity(composite_score)

        # Determine overall confidence
        if comp_count >= 6 and f_data.score <= 30:
            overall_confidence = "HIGH"
        elif comp_count >= 2:
            overall_confidence = "MEDIUM"
        else:
            overall_confidence = "LOW"

        # Extract Positive Signals & Risk Signals
        positive_signals: List[str] = []
        risk_signals: List[str] = []

        for f in factors:
            if f.score <= 25 and f.evidence:
                positive_signals.append(f.evidence[0])
            elif f.score >= 60 and f.evidence:
                risk_signals.append(f.evidence[0])

        if not positive_signals:
            if comp_count >= 4:
                positive_signals.append(f"Supported by {comp_count} active marketplace comparable listings")
            else:
                positive_signals.append("Baseline pricing model calibration available")

        if not risk_signals:
            risk_signals.append("No critical pricing, usage, or evidence anomalies detected")

        # Executive Summary & Next Steps
        summary = self._build_executive_summary(composite_score, risk_level, positive_signals, risk_signals)
        recommendation = self._build_recommendation(composite_score, risk_level, factors)

        # Evidence Summary Snapshot
        evidence_summary = RiskEvidenceSummary(
            comparables_count=comp_count,
            market_evidence_density="HIGH" if comp_count >= 8 else ("MEDIUM" if comp_count >= 3 else "LOW"),
            data_completeness=1.0 - (f_data.score / 100.0),
            source_diversity="HIGH" if f_source.score <= 25 else ("MEDIUM" if f_source.score <= 50 else "SINGLE_SOURCE"),
            sources_count=len(set(comp_sources)) if comp_sources else 1,
            price_dispersion_pct=round(((market_stats.p75 - market_stats.p25) / market_stats.median * 100.0), 1) if (market_stats.median and market_stats.p25 and market_stats.p75) else None,
            uncertainty_width_pct=round(((interval_high - interval_low) / est_val * 100.0), 1) if (interval_low and interval_high and est_val > 0) else None
        )

        return RiskAnalysisResponse(
            risk_score=composite_score,
            risk_level=risk_level,
            confidence=overall_confidence,
            summary=summary,
            recommendation=recommendation,
            factors=factors,
            positive_signals=positive_signals[:4],
            risk_signals=risk_signals[:4],
            unknowns=self.UNVERIFIED_PHYSICAL_FACTORS,
            evidence_summary=evidence_summary,
            weights_used=self.RISK_WEIGHTS
        )

    def _evaluate_price_anomaly(
        self,
        asking_price: Optional[float],
        estimated_value: float,
        market_median: Optional[float],
        market_p25: Optional[float],
        market_p75: Optional[float],
        interval_low: Optional[float],
        interval_high: Optional[float]
    ) -> RiskFactor:
        weight = self.RISK_WEIGHTS["price_anomaly"]
        if asking_price is None or asking_price <= 0:
            score = 25
            evidence = ["Asking price not specified by seller; price anomaly evaluated against baseline market median."]
            interpretation = "Without a seller asking price, valuation risk is anchored to standard market variance."
            confidence = "LOW"
        else:
            diff_ml_pct = ((asking_price - estimated_value) / estimated_value) * 100.0
            abs_diff_ml = abs(diff_ml_pct)

            evidence = [
                f"Asking price (₹{asking_price:,.0f}) is {abs_diff_ml:.1f}% {'above' if diff_ml_pct > 0 else 'below'} estimated fair value (₹{estimated_value:,.0f})."
            ]

            if market_p25 and asking_price < market_p25:
                evidence.append(f"Asking price sits below the 25th percentile market bound (₹{market_p25:,.0f}).")
            elif market_p75 and asking_price > market_p75:
                evidence.append(f"Asking price exceeds the 75th percentile market bound (₹{market_p75:,.0f}).")

            if abs_diff_ml <= 4.0:
                score = 10
                interpretation = "Asking price aligns closely with calibrated fair market value."
            elif abs_diff_ml <= 8.0:
                score = 25
                interpretation = "Asking price reflects normal retail negotiation buffer."
            elif abs_diff_ml <= 15.0:
                score = 50
                interpretation = "Asking price shows moderate deviation from fair market consensus."
            elif abs_diff_ml <= 25.0:
                score = 75
                interpretation = "Asking price is materially disconnected from central market evidence."
            else:
                score = 90
                interpretation = "Extreme price anomaly detected relative to fair value and comparable listings."

            confidence = "HIGH"

        severity = self._map_severity(score)
        return RiskFactor(
            key="price_anomaly",
            name="Price Anomaly Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence=confidence,
            evidence=evidence,
            interpretation=interpretation
        )

    def _evaluate_mileage_usage(
        self,
        km_driven: int,
        car_age: int,
        km_per_year: float,
        comp_median_km: Optional[float]
    ) -> RiskFactor:
        weight = self.RISK_WEIGHTS["mileage_usage"]
        evidence = [
            f"Accumulated odometer: {km_driven:,} km across {car_age} years ({km_per_year:,.0f} km/year)."
        ]

        if km_per_year <= 8000:
            score = 15
            interpretation = "Light annual usage intensity indicates lower mechanical wear risk."
        elif km_per_year <= 14000:
            score = 30
            interpretation = "Usage intensity conforms to standard private passenger vehicle driving patterns."
        elif km_per_year <= 20000:
            score = 60
            interpretation = "Above-average annual mileage implies elevated component wear."
        else:
            score = 85
            interpretation = "Heavy usage intensity (>20,000 km/year) suggests potential fleet, commercial, or heavy highway usage."

        if comp_median_km and comp_median_km > 0:
            km_ratio = km_driven / comp_median_km
            if km_ratio > 1.3:
                score = min(100, score + 10)
                evidence.append(f"Odometer is {((km_ratio - 1.0)*100.0):.1f}% higher than comparable segment median ({comp_median_km:,.0f} km).")
            elif km_ratio < 0.7:
                score = max(5, score - 10)
                evidence.append(f"Odometer is {((1.0 - km_ratio)*100.0):.1f}% lower than comparable segment median ({comp_median_km:,.0f} km).")

        severity = self._map_severity(score)
        return RiskFactor(
            key="mileage_usage",
            name="Mileage & Usage Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence="HIGH",
            evidence=evidence,
            interpretation=interpretation
        )

    def _evaluate_vehicle_age(self, year: int, car_age: int) -> RiskFactor:
        weight = self.RISK_WEIGHTS["vehicle_age"]
        evidence = [f"Manufacturing year: {year} ({car_age} years old)."]

        if car_age <= 3:
            score = 15
            interpretation = "Recent model year with modern safety equipment and low lifecycle depreciation risk."
        elif car_age <= 7:
            score = 35
            interpretation = "Mature lifecycle phase with predictable replacement parts and service availability."
        elif car_age <= 11:
            score = 65
            interpretation = "Aging vehicle with accelerated depreciation and increased routine maintenance requirements."
        else:
            score = 85
            interpretation = "High age risk: vehicle approaches late lifecycle with higher likelihood of major component renewals."

        severity = self._map_severity(score)
        return RiskFactor(
            key="vehicle_age",
            name="Vehicle Age Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence="HIGH",
            evidence=evidence,
            interpretation=interpretation
        )

    def _evaluate_market_liquidity(self, comparable_count: int, city: str) -> RiskFactor:
        weight = self.RISK_WEIGHTS["market_liquidity"]
        evidence = [f"Found {comparable_count} active comparable listings in '{city}'."]

        if comparable_count >= 8:
            score = 15
            interpretation = "High market liquidity ensures strong resale demand and reliable pricing discovery."
            confidence = "HIGH"
        elif comparable_count >= 4:
            score = 35
            interpretation = "Moderate liquidity with sufficient active listings for valuation support."
            confidence = "HIGH"
        elif comparable_count >= 1:
            score = 70
            interpretation = "Sparse segment: limited active listings increase resale liquidity risk."
            confidence = "MEDIUM"
        else:
            score = 90
            interpretation = "Zero active comparable listings found; very high resale liquidity uncertainty."
            confidence = "LOW"

        severity = self._map_severity(score)
        return RiskFactor(
            key="market_liquidity",
            name="Market Liquidity Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence=confidence,
            evidence=evidence,
            interpretation=interpretation
        )

    def _evaluate_data_quality(self, vehicle_data: Dict[str, Any]) -> RiskFactor:
        weight = self.RISK_WEIGHTS["data_quality"]
        evaluated_fields = [
            "brand", "model", "year", "km_driven", "city",
            "fuel_type", "transmission", "variant", "engine_cc",
            "mileage", "owner_count", "seller_type"
        ]
        missing_fields = []
        for f in evaluated_fields:
            val = vehicle_data.get(f)
            if val is None or str(val).strip() == "" or str(val).lower() == "unspecified":
                missing_fields.append(f)

        completeness = round((len(evaluated_fields) - len(missing_fields)) / len(evaluated_fields), 2)
        evidence = [f"Vehicle specification completeness: {int(completeness * 100)}%."]
        if missing_fields:
            evidence.append(f"Missing attributes: {', '.join(missing_fields[:3])}{'...' if len(missing_fields)>3 else ''}.")

        if completeness >= 0.90:
            score = 10
            interpretation = "Rich vehicle specification provided, minimizing model inference error."
        elif completeness >= 0.75:
            score = 30
            interpretation = "Adequate specification with minor secondary parameters defaulted."
        elif completeness >= 0.50:
            score = 60
            interpretation = "Multiple vehicle attributes unspecified; model inference uncertainty is elevated."
        else:
            score = 85
            interpretation = "Sparse specification inputs undermine reliable valuation precision."

        severity = self._map_severity(score)
        return RiskFactor(
            key="data_quality",
            name="Data Quality Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence="HIGH",
            evidence=evidence,
            interpretation=interpretation
        )

    def _evaluate_market_evidence(
        self,
        comparable_count: int,
        estimated_value: float,
        market_median: Optional[float]
    ) -> RiskFactor:
        weight = self.RISK_WEIGHTS["market_evidence"]
        evidence = []

        if market_median and estimated_value > 0:
            divergence_pct = abs((estimated_value - market_median) / estimated_value) * 100.0
            evidence.append(f"Model fair value diverges by {divergence_pct:.1f}% from observed market median.")
        else:
            divergence_pct = None

        if comparable_count >= 6 and (divergence_pct is None or divergence_pct <= 6.0):
            score = 15
            interpretation = "Strong empirical consensus between model predictions and observed marketplace listings."
            confidence = "HIGH"
        elif comparable_count >= 3 and (divergence_pct is None or divergence_pct <= 12.0):
            score = 35
            interpretation = "Moderate evidence agreement across available marketplace observations."
            confidence = "MEDIUM"
        elif comparable_count >= 1:
            score = 65
            interpretation = "Weak evidence density with elevated variance between model and listings."
            confidence = "LOW"
        else:
            score = 85
            interpretation = "Insufficient empirical market evidence available to corroborate valuation."
            confidence = "INSUFFICIENT"

        severity = self._map_severity(score)
        return RiskFactor(
            key="market_evidence",
            name="Market Evidence Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence=confidence,
            evidence=evidence or ["Marketplace evidence density calculated from active inventory."],
            interpretation=interpretation
        )

    def _evaluate_valuation_uncertainty(
        self,
        estimated_value: float,
        interval_low: Optional[float],
        interval_high: Optional[float]
    ) -> RiskFactor:
        weight = self.RISK_WEIGHTS["valuation_uncertainty"]
        evidence = []

        if interval_low is not None and interval_high is not None and estimated_value > 0:
            width = interval_high - interval_low
            width_pct = (width / estimated_value) * 100.0
            evidence.append(f"80% conformal uncertainty interval spans ±{(width_pct/2.0):.1f}% (₹{interval_low:,.0f} to ₹{interval_high:,.0f}).")

            if width_pct <= 16.0:
                score = 15
                interpretation = "Tight conformal prediction interval reflects high statistical model confidence."
            elif width_pct <= 26.0:
                score = 35
                interpretation = "Standard uncertainty interval within expected parameters for used vehicles."
            elif width_pct <= 40.0:
                score = 65
                interpretation = "Wider prediction interval indicates higher variance in segment pricing."
            else:
                score = 85
                interpretation = "Wide uncertainty band reflects high feature dispersion or sparse training coverage."
            confidence = "HIGH"
        else:
            score = 60
            evidence.append("Conformal uncertainty interval is unavailable for this segment.")
            interpretation = "Model point prediction lacks calibrated residual uncertainty bounds."
            confidence = "LOW"

        severity = self._map_severity(score)
        return RiskFactor(
            key="valuation_uncertainty",
            name="Valuation Uncertainty Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence=confidence,
            evidence=evidence,
            interpretation=interpretation
        )

    def _evaluate_price_dispersion(
        self,
        market_median: Optional[float],
        market_p25: Optional[float],
        market_p75: Optional[float],
        comparable_prices: List[float]
    ) -> RiskFactor:
        weight = self.RISK_WEIGHTS["price_dispersion"]
        evidence = []

        if market_median and market_p25 and market_p75 and market_median > 0:
            iqr_spread_pct = ((market_p75 - market_p25) / market_median) * 100.0
            evidence.append(f"Interquartile price spread is {iqr_spread_pct:.1f}% of median (P25: ₹{market_p25:,.0f}, P75: ₹{market_p75:,.0f}).")

            if iqr_spread_pct <= 15.0:
                score = 15
                interpretation = "Tight price dispersion indicates strong seller consensus on fair pricing."
            elif iqr_spread_pct <= 30.0:
                score = 40
                interpretation = "Moderate price dispersion typical of used automotive markets."
            else:
                score = 75
                interpretation = "High price dispersion indicates wide disagreement among sellers regarding vehicle value."
            confidence = "HIGH"
        elif len(comparable_prices) >= 2:
            stdev = statistics.stdev(comparable_prices)
            mean_val = statistics.mean(comparable_prices)
            cv_pct = (stdev / mean_val) * 100.0 if mean_val > 0 else 0
            evidence.append(f"Comparable listings show a coefficient of price variation of {cv_pct:.1f}%.")
            score = 35 if cv_pct <= 20.0 else (60 if cv_pct <= 35.0 else 80)
            interpretation = "Price dispersion estimated from available sample variance."
            confidence = "MEDIUM"
        else:
            score = 50
            evidence.append("Insufficient comparable sample size to calculate price dispersion.")
            interpretation = "Price dispersion cannot be reliably measured due to limited sample size."
            confidence = "LOW"

        severity = self._map_severity(score)
        return RiskFactor(
            key="price_dispersion",
            name="Price Dispersion Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence=confidence,
            evidence=evidence,
            interpretation=interpretation
        )

    def _evaluate_source_concentration(
        self,
        comparable_sources: List[str],
        comparable_count: int
    ) -> RiskFactor:
        weight = self.RISK_WEIGHTS["source_concentration"]
        evidence = []

        if comparable_count == 0 or not comparable_sources:
            score = 60
            evidence.append("No active marketplace inventory sources detected.")
            interpretation = "Evidence relies entirely on model weights rather than multi-source listings."
            confidence = "LOW"
        else:
            source_counts = {}
            for s in comparable_sources:
                source_counts[s] = source_counts.get(s, 0) + 1

            unique_sources = len(source_counts)
            max_share = max(source_counts.values()) / comparable_count

            evidence.append(f"Observed {comparable_count} listings across {unique_sources} independent inventory source(s).")

            if unique_sources >= 3 and max_share <= 0.55:
                score = 15
                interpretation = "High source diversity protects against single-portal scraping or listing biases."
                confidence = "HIGH"
            elif unique_sources >= 2 and max_share <= 0.85:
                score = 35
                interpretation = "Balanced multi-source evidence distribution."
                confidence = "HIGH"
            elif unique_sources >= 2:
                score = 55
                interpretation = "Multi-source evidence present, but heavily concentrated on one primary portal."
                confidence = "MEDIUM"
            else:
                score = 70
                interpretation = "Evidence is 100% concentrated on a single source, increasing portal-specific pricing bias."
                confidence = "MEDIUM"

        severity = self._map_severity(score)
        return RiskFactor(
            key="source_concentration",
            name="Source Concentration Risk",
            score=score,
            severity=severity,
            weight=weight,
            weighted_contribution=round(score * weight, 2),
            confidence=confidence,
            evidence=evidence,
            interpretation=interpretation
        )

    def _build_insufficient_evidence_response(
        self,
        vehicle_data: Dict[str, Any],
        valuation_response: ValuationResponse
    ) -> RiskAnalysisResponse:
        """
        Builds a dedicated fallback response when evidence is too sparse for risk assessment.
        """
        evidence_summary = RiskEvidenceSummary(
            comparables_count=0,
            market_evidence_density="INSUFFICIENT",
            data_completeness=0.5,
            source_diversity="LOW",
            sources_count=0
        )
        return RiskAnalysisResponse(
            risk_score=50,
            risk_level="INSUFFICIENT_EVIDENCE",
            confidence="LOW",
            summary="Insufficient comparable-market evidence to calculate a reliable observable risk assessment.",
            recommendation="Gather additional comparable listings in adjacent cities or broader trim variants before relying on market risk signals.",
            factors=[],
            positive_signals=["Baseline model inference completed"],
            risk_signals=["No active comparable market listings found for this configuration"],
            unknowns=self.UNVERIFIED_PHYSICAL_FACTORS,
            evidence_summary=evidence_summary,
            weights_used=self.RISK_WEIGHTS
        )

    def _build_executive_summary(
        self,
        score: int,
        level: str,
        positive_signals: List[str],
        risk_signals: List[str]
    ) -> str:
        if level in ["VERY_LOW", "LOW"]:
            return f"Vehicle demonstrates low observable market and evidence risk ({score}/100) supported by consistent marketplace data."
        elif level == "MODERATE":
            return f"Vehicle presents moderate observable risk ({score}/100) with specific usage, pricing, or evidence factors requiring verification."
        else:
            return f"Vehicle displays elevated observable risk ({score}/100) driven by material pricing anomalies, usage intensity, or sparse market support."

    def _build_recommendation(
        self,
        score: int,
        level: str,
        factors: List[RiskFactor]
    ) -> str:
        top_risks = [f.name for f in sorted(factors, key=lambda x: x.score, reverse=True) if f.score >= 55]
        if level in ["VERY_LOW", "LOW"]:
            return "Available market evidence is consistent. Conduct standard physical and documentation verification before finalizing purchase."
        elif level == "MODERATE":
            if top_risks:
                return f"Compare against alternative listings and verify key risk drivers: {', '.join(top_risks[:2])}."
            return "Perform standard due diligence and cross-reference asking price with recommended negotiation corridors."
        else:
            if top_risks:
                return f"Perform comprehensive pre-purchase due diligence focusing on {', '.join(top_risks[:2])} before committing."
            return "Proceed with caution; substantial deviation from market consensus detected."

    def evaluate_batch(
        self,
        requests: List[ValuationRequestSchema]
    ) -> BatchRiskResponse:
        """
        Executes bounded batch risk evaluation across multiple vehicle requests.
        """
        results: List[BatchRiskItem] = []
        for idx, req in enumerate(requests):
            val_resp = valuation_service.evaluate_valuation(req, include_shap=False)
            risk_resp = self.evaluate_risk(req.model_dump(), val_resp)

            item = BatchRiskItem(
                vehicle_identifier=f"{req.brand} {req.model} ({req.year}) - #{idx+1}",
                brand=req.brand,
                model=req.model,
                year=req.year,
                km_driven=req.km_driven,
                city=req.city,
                estimated_value=val_resp.valuation.estimated_value,
                asking_price=req.asking_price,
                risk_score=risk_resp.risk_score,
                risk_level=risk_resp.risk_level,
                confidence=risk_resp.confidence,
                top_risks=risk_resp.risk_signals[:2],
                top_positive_signals=risk_resp.positive_signals[:2]
            )
            results.append(item)

        return BatchRiskResponse(
            total_vehicles=len(results),
            results=results
        )


risk_service = RiskService()
