"""
AutoValue Observability and Application Metrics Service.
Collects Prometheus-compatible metrics, request counters, execution histograms,
and decision intelligence telemetry without external heavyweight dependencies.
"""
from typing import Dict, Any, List, Optional
import time
from collections import defaultdict

from backend.app.core.config import settings


class MetricsCollector:
    """
    In-memory Prometheus-compatible metrics registry.
    """

    def __init__(self):
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.valuation_counts: Dict[str, int] = defaultdict(int)
        self.deal_analysis_counts: Dict[str, int] = defaultdict(int)
        self.scenario_requests_total: int = 0
        self.alternative_search_total: int = 0
        self.watchlist_refresh_total: int = 0
        self.risk_requests_total: int = 0
        self.risk_insufficient_evidence_total: int = 0
        self.tco_requests_total: int = 0
        self.tco_insufficient_evidence_total: int = 0
        self.resale_projection_requests_total: int = 0
        self.forecast_requests_total: int = 0
        self.forecast_insufficient_evidence_total: int = 0
        self.forecast_confidence_distribution: Dict[str, int] = defaultdict(int)
        self.timing_requests_total: int = 0
        self.lifecycle_requests_total: int = 0
        self.lifecycle_insufficient_evidence_total: int = 0
        self.lifecycle_action_distribution: Dict[str, int] = defaultdict(int)
        self.lifecycle_scenario_requests_total: int = 0
        self.garage_requests_total: int = 0
        self.garage_vehicle_count: int = 0
        self.garage_insufficient_evidence_total: int = 0
        self.garage_scenario_requests_total: int = 0
        self.garage_action_distribution: Dict[str, int] = defaultdict(int)
        self.latencies: Dict[str, List[float]] = defaultdict(list)
        self.valuation_latencies: List[float] = []
        self.intelligence_latencies: List[float] = []
        self.risk_latencies: List[float] = []
        self.tco_latencies: List[float] = []
        self.forecast_latencies: List[float] = []
        self.lifecycle_latencies: List[float] = []
        self.garage_latencies: List[float] = []
        self.comparable_counts: List[int] = []

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        norm_path = path
        if "/valuation" in path:
            norm_path = "/api/valuation"
        elif "/intelligence" in path:
            norm_path = "/api/intelligence"
        elif "/risk" in path:
            norm_path = "/api/risk"
        elif "/tco" in path:
            norm_path = "/api/tco"
        elif "/market/forecast" in path:
            norm_path = "/api/market/forecast"
        elif "/scenario" in path:
            norm_path = "/api/scenario"
        elif "/alternatives" in path:
            norm_path = "/api/alternatives"
        elif "/watchlist" in path:
            norm_path = "/api/watchlist"
        elif "/market/history" in path:
            norm_path = "/api/market/history"
        elif "/market/timing" in path:
            norm_path = "/api/market/timing"
        elif "/models" in path:
            norm_path = "/api/models"
        elif "/sources" in path:
            norm_path = "/api/sources"
        elif "/health" in path:
            norm_path = "/api/health"
        elif "/ready" in path:
            norm_path = "/api/ready"
        elif "/data-quality" in path:
            norm_path = "/api/data-quality"

        key = f'method="{method}",path="{norm_path}",status="{status_code}"'
        self.request_counts[key] += 1
        self.latencies[norm_path].append(duration_ms)
        if len(self.latencies[norm_path]) > 500:
            self.latencies[norm_path].pop(0)

    def record_valuation(self, status: str, duration_ms: float, comparables_found: int):
        self.valuation_counts[status] += 1
        self.valuation_latencies.append(duration_ms)
        self.comparable_counts.append(comparables_found)
        if len(self.valuation_latencies) > 500:
            self.valuation_latencies.pop(0)
        if len(self.comparable_counts) > 500:
            self.comparable_counts.pop(0)

    def record_deal_analysis(self, classification: str):
        self.deal_analysis_counts[classification] += 1

    def record_scenario_request(self):
        self.scenario_requests_total += 1

    def record_alternative_search(self):
        self.alternative_search_total += 1

    def record_watchlist_refresh(self):
        self.watchlist_refresh_total += 1

    def record_intelligence_latency(self, duration_ms: float):
        self.intelligence_latencies.append(duration_ms)
        if len(self.intelligence_latencies) > 500:
            self.intelligence_latencies.pop(0)

    def record_risk_request(self, insufficient_evidence: bool = False, duration_ms: float = 0.0):
        self.risk_requests_total += 1
        if insufficient_evidence:
            self.risk_insufficient_evidence_total += 1
        if duration_ms > 0:
            self.risk_latencies.append(duration_ms)
            if len(self.risk_latencies) > 500:
                self.risk_latencies.pop(0)

    def record_tco_request(self, insufficient_evidence: bool = False, duration_ms: float = 0.0):
        self.tco_requests_total += 1
        self.resale_projection_requests_total += 1
        if insufficient_evidence:
            self.tco_insufficient_evidence_total += 1
        if duration_ms > 0:
            self.tco_latencies.append(duration_ms)
            if len(self.tco_latencies) > 500:
                self.tco_latencies.pop(0)

    def record_forecast_request(self, insufficient_evidence: bool = False, confidence: str = "MODERATE", duration_ms: float = 0.0):
        self.forecast_requests_total += 1
        self.forecast_confidence_distribution[confidence] += 1
        if insufficient_evidence:
            self.forecast_insufficient_evidence_total += 1
        if duration_ms > 0:
            self.forecast_latencies.append(duration_ms)
            if len(self.forecast_latencies) > 500:
                self.forecast_latencies.pop(0)

    def record_timing_request(self):
        self.timing_requests_total += 1

    def record_lifecycle_request(self, action: str, confidence: str, duration_ms: float, is_insufficient: bool = False):
        self.lifecycle_requests_total += 1
        self.lifecycle_action_distribution[action] += 1
        if is_insufficient:
            self.lifecycle_insufficient_evidence_total += 1
        if duration_ms > 0:
            self.lifecycle_latencies.append(duration_ms)
            if len(self.lifecycle_latencies) > 500:
                self.lifecycle_latencies.pop(0)

    def record_lifecycle_scenario_request(self):
        self.lifecycle_scenario_requests_total += 1

    def record_garage_request(self, action: Optional[str] = None, vehicle_count: int = 0, duration_ms: float = 0.0, is_insufficient: bool = False):
        self.garage_requests_total += 1
        self.garage_vehicle_count = vehicle_count
        if action:
            self.garage_action_distribution[action] += 1
        if is_insufficient:
            self.garage_insufficient_evidence_total += 1
        if duration_ms > 0:
            self.garage_latencies.append(duration_ms)
            if len(self.garage_latencies) > 500:
                self.garage_latencies.pop(0)

    def record_garage_scenario_request(self):
        self.garage_scenario_requests_total += 1

    def generate_prometheus_text(self) -> str:
        """Renders collected metrics into Prometheus text format."""
        if not hasattr(self, "tco_requests_total"):
            self.tco_requests_total = 0
            self.tco_insufficient_evidence_total = 0
            self.resale_projection_requests_total = 0
            self.tco_latencies: List[float] = []
        if not hasattr(self, "lifecycle_requests_total"):
            self.lifecycle_requests_total = 0
            self.lifecycle_insufficient_evidence_total = 0
            self.lifecycle_action_distribution = defaultdict(int)
            self.lifecycle_scenario_requests_total = 0
            self.lifecycle_latencies = []

        lines = [
            "# HELP autovalue_http_requests_total Total number of HTTP requests processed.",
            "# TYPE autovalue_http_requests_total counter"
        ]
        for labels, count in sorted(self.request_counts.items()):
            lines.append(f"autovalue_http_requests_total{{{labels}}} {count}")

        lines.extend([
            "",
            "# HELP autovalue_valuation_requests_total Total vehicle valuation computations.",
            "# TYPE autovalue_valuation_requests_total counter"
        ])
        for status_val, count in sorted(self.valuation_counts.items()):
            lines.append(f'autovalue_valuation_requests_total{{status="{status_val}"}} {count}')

        lines.extend([
            "",
            "# HELP autovalue_deal_analysis_total Total smart deal analyses computed by classification category.",
            "# TYPE autovalue_deal_analysis_total counter"
        ])
        for classification, count in sorted(self.deal_analysis_counts.items()):
            lines.append(f'autovalue_deal_analysis_total{{classification="{classification}"}} {count}')

        lines.extend([
            "",
            "# HELP autovalue_scenario_requests_total Total What-If scenario simulations performed.",
            "# TYPE autovalue_scenario_requests_total counter",
            f"autovalue_scenario_requests_total {self.scenario_requests_total}",
            "",
            "# HELP autovalue_alternative_search_total Total alternative vehicle discovery queries executed.",
            "# TYPE autovalue_alternative_search_total counter",
            f"autovalue_alternative_search_total {self.alternative_search_total}",
            "",
            "# HELP autovalue_watchlist_refresh_total Total personal valuation watchlist refreshes performed.",
            "# TYPE autovalue_watchlist_refresh_total counter",
            f"autovalue_watchlist_refresh_total {self.watchlist_refresh_total}",
            "",
            "# HELP autovalue_risk_requests_total Total vehicle risk and trust intelligence assessments computed.",
            "# TYPE autovalue_risk_requests_total counter",
            f"autovalue_risk_requests_total {self.risk_requests_total}",
            "",
            "# HELP autovalue_risk_insufficient_evidence_total Total risk assessments returning insufficient evidence.",
            "# TYPE autovalue_risk_insufficient_evidence_total counter",
            f"autovalue_risk_insufficient_evidence_total {self.risk_insufficient_evidence_total}",
            "",
            "# HELP autovalue_tco_requests_total Total ownership economics assessments computed.",
            "# TYPE autovalue_tco_requests_total counter",
            f"autovalue_tco_requests_total {self.tco_requests_total}",
            "",
            "# HELP autovalue_tco_insufficient_evidence_total Total TCO assessments with sparse market evidence.",
            "# TYPE autovalue_tco_insufficient_evidence_total counter",
            f"autovalue_tco_insufficient_evidence_total {self.tco_insufficient_evidence_total}",
            "",
            "# HELP autovalue_resale_projection_requests_total Total resale value projections computed.",
            "# TYPE autovalue_resale_projection_requests_total counter",
            f"autovalue_resale_projection_requests_total {self.resale_projection_requests_total}",
            "",
            "# HELP autovalue_forecast_requests_total Total vehicle market forecasting requests computed.",
            "# TYPE autovalue_forecast_requests_total counter",
            f"autovalue_forecast_requests_total {self.forecast_requests_total}",
            "",
            "# HELP autovalue_forecast_insufficient_evidence_total Total market forecast requests returning insufficient evidence.",
            "# TYPE autovalue_forecast_insufficient_evidence_total counter",
            f"autovalue_forecast_insufficient_evidence_total {self.forecast_insufficient_evidence_total}",
            "",
            "# HELP autovalue_timing_requests_total Total buy and sell market timing requests computed.",
            "# TYPE autovalue_timing_requests_total counter",
            f"autovalue_timing_requests_total {self.timing_requests_total}",
            "",
            "# HELP autovalue_lifecycle_requests_total Total vehicle lifecycle and ownership decisions computed.",
            "# TYPE autovalue_lifecycle_requests_total counter",
            f"autovalue_lifecycle_requests_total {self.lifecycle_requests_total}",
            "",
            "# HELP autovalue_lifecycle_insufficient_evidence_total Total lifecycle queries returning insufficient evidence.",
            "# TYPE autovalue_lifecycle_insufficient_evidence_total counter",
            f"autovalue_lifecycle_insufficient_evidence_total {self.lifecycle_insufficient_evidence_total}",
            "",
            "# HELP autovalue_lifecycle_scenario_requests_total Total lifecycle scenario simulations.",
            "# TYPE autovalue_lifecycle_scenario_requests_total counter",
            f"autovalue_lifecycle_scenario_requests_total {self.lifecycle_scenario_requests_total}"
        ])

        for action_name, act_count in sorted(self.lifecycle_action_distribution.items()):
            lines.append(f'autovalue_lifecycle_action_distribution{{action="{action_name}"}} {act_count}')

        lines.extend([
            "",
            "# HELP autovalue_garage_requests_total Total garage and portfolio intelligence queries computed.",
            "# TYPE autovalue_garage_requests_total counter",
            f"autovalue_garage_requests_total {self.garage_requests_total}",
            "",
            "# HELP autovalue_garage_insufficient_evidence_total Total garage queries with insufficient evidence.",
            "# TYPE autovalue_garage_insufficient_evidence_total counter",
            f"autovalue_garage_insufficient_evidence_total {self.garage_insufficient_evidence_total}",
            "",
            "# HELP autovalue_garage_scenario_requests_total Total garage portfolio what-if scenario simulations.",
            "# TYPE autovalue_garage_scenario_requests_total counter",
            f"autovalue_garage_scenario_requests_total {self.garage_scenario_requests_total}",
            "",
            "# HELP autovalue_garage_vehicle_count Last observed vehicle count in user garage.",
            "# TYPE autovalue_garage_vehicle_count gauge",
            f"autovalue_garage_vehicle_count {self.garage_vehicle_count}"
        ])

        for action_name, act_count in sorted(self.garage_action_distribution.items()):
            lines.append(f'autovalue_garage_action_distribution{{action="{action_name}"}} {act_count}')

        lines.extend([
            "",
            "# HELP autovalue_active_model_info Active machine learning model version metadata.",
            "# TYPE autovalue_active_model_info gauge",
            f'autovalue_active_model_info{{model_version="{settings.AUTOVALUE_MODEL_VERSION}"}} 1.0'
        ])

        if self.valuation_latencies:
            avg_val_lat = sum(self.valuation_latencies) / len(self.valuation_latencies)
            lines.extend([
                "",
                "# HELP autovalue_valuation_latency_ms_avg Average valuation execution latency in milliseconds.",
                "# TYPE autovalue_valuation_latency_ms_avg gauge",
                f"autovalue_valuation_latency_ms_avg {avg_val_lat:.2f}"
            ])

        if self.intelligence_latencies:
            avg_intel_sec = (sum(self.intelligence_latencies) / len(self.intelligence_latencies)) / 1000.0
            lines.extend([
                "",
                "# HELP autovalue_intelligence_latency_seconds Average Decision Intelligence execution latency in seconds.",
                "# TYPE autovalue_intelligence_latency_seconds gauge",
                f"autovalue_intelligence_latency_seconds {avg_intel_sec:.4f}"
            ])

        if self.risk_latencies:
            avg_risk_sec = (sum(self.risk_latencies) / len(self.risk_latencies)) / 1000.0
            lines.extend([
                "",
                "# HELP autovalue_risk_latency_seconds Average Risk Engine execution latency in seconds.",
                "# TYPE autovalue_risk_latency_seconds gauge",
                f"autovalue_risk_latency_seconds {avg_risk_sec:.4f}"
            ])

        if self.tco_latencies:
            avg_tco_sec = (sum(self.tco_latencies) / len(self.tco_latencies)) / 1000.0
            lines.extend([
                "",
                "# HELP autovalue_tco_latency_seconds Average TCO Engine execution latency in seconds.",
                "# TYPE autovalue_tco_latency_seconds gauge",
                f"autovalue_tco_latency_seconds {avg_tco_sec:.4f}"
            ])

        if self.forecast_latencies:
            avg_fc_sec = (sum(self.forecast_latencies) / len(self.forecast_latencies)) / 1000.0
            lines.extend([
                "",
                "# HELP autovalue_forecast_latency_seconds Average Market Forecasting execution latency in seconds.",
                "# TYPE autovalue_forecast_latency_seconds gauge",
                f"autovalue_forecast_latency_seconds {avg_fc_sec:.4f}"
            ])

        if hasattr(self, "lifecycle_latencies") and self.lifecycle_latencies:
            avg_lc_sec = (sum(self.lifecycle_latencies) / len(self.lifecycle_latencies)) / 1000.0
            lines.extend([
                "",
                "# HELP autovalue_lifecycle_latency_seconds Average Lifecycle Decision Engine execution latency in seconds.",
                "# TYPE autovalue_lifecycle_latency_seconds gauge",
                f"autovalue_lifecycle_latency_seconds {avg_lc_sec:.4f}"
            ])

        if self.comparable_counts:
            avg_comps = sum(self.comparable_counts) / len(self.comparable_counts)
            lines.extend([
                "",
                "# HELP autovalue_comparables_matched_avg Average comparable vehicles found per valuation.",
                "# TYPE autovalue_comparables_matched_avg gauge",
                f"autovalue_comparables_matched_avg {avg_comps:.2f}"
            ])

        lines.append("")
        return "\n".join(lines)


# Global singleton metrics registry
metrics_collector = MetricsCollector()
