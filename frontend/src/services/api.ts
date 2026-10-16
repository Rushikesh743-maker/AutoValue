/**
 * AutoValue Centralized API Client
 *
 * Provides typed, timeout-protected HTTP operations against the AutoValue backend,
 * supporting credentials (session cookies), bearer headers, request correlation IDs,
 * user authentication, valuation history snapshots, saved vehicle bookmarks,
 * report sharing, and vehicle comparisons.
 */

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ValuationRequest {
  brand: string;
  model: string;
  variant?: string;
  year: number;
  fuel_type?: string;
  transmission?: string;
  km_driven?: number;
  engine_cc?: number;
  mileage?: number;
  owner_count?: number;
  city?: string;
  state?: string;
  seller_type?: string;
  asking_price?: number;
}

export interface ModelInterval {
  interval_low: number;
  interval_high: number;
  interval_low_formatted: string;
  interval_high_formatted: string;
  confidence_level: number;
  method: string;
}

export interface ValuationData {
  estimated_value: number;
  estimated_value_formatted: string;
  range_low?: number;
  range_high?: number;
  range_low_formatted?: string;
  range_high_formatted?: string;
  range_method: string;
  combination_method: string;
  model_interval?: ModelInterval;
}

export interface MarketStats {
  median?: number;
  mean?: number;
  min?: number;
  max?: number;
  p25?: number;
  p75?: number;
  comparable_count: number;
  price_dispersion_std?: number;
}

export interface ModelEvidence {
  selected_model: string;
  dataset_records: number;
  test_mae?: number;
  test_r2?: number;
  evaluation_strategy: string;
}

export interface ComparableItem {
  listing_id: string;
  brand: string;
  model: string;
  variant?: string;
  year: number;
  fuel_type?: string;
  transmission?: string;
  km_driven?: number;
  city?: string;
  state?: string;
  listed_price: number;
  listed_price_formatted: string;
  source: string;
  similarity_score: number;
  similarity_percentage: string;
  date_collected?: string;
}

export interface SourceAnalysisItem {
  source: string;
  listing_count: number;
  median_price: number;
  mean_price: number;
  min_price: number;
  max_price: number;
}

export interface ExplanationItem {
  feature: string;
  impact_inr: number;
  direction: string;
  human_readable_text: string;
}

export interface MarketPosition {
  asking_price: number;
  position: string;
  difference_from_median: number;
  percentage_difference_from_median: number;
}

export interface ValuationResponse {
  model_version: string;
  dataset_version: string;
  valuation: ValuationData;
  market: MarketStats;
  model_evidence?: ModelEvidence;
  comparables: ComparableItem[];
  source_analysis: SourceAnalysisItem[];
  explanation: ExplanationItem[];
  market_position?: MarketPosition;
  transparency_notice: string;
  request_id?: string;
  latency_ms?: number;
}

export interface SavedValuationSummary {
  id: string;
  request_id?: string;
  created_at: string;
  brand: string;
  model: string;
  variant?: string;
  year: number;
  fuel_type?: string;
  transmission?: string;
  km_driven: number;
  city: string;
  engine_cc?: number;
  mileage?: number;
  owner_count?: number;
  seller_type?: string;
  asking_price?: number;
  estimated_value: number;
  range_low?: number;
  range_high?: number;
  model_interval_low?: number;
  model_interval_high?: number;
  market_median?: number;
  comparable_count: number;
  model_version: string;
  dataset_version: string;
  notes?: string;
  is_shared: boolean;
  share_token?: string;
}

export interface SavedValuationDetail extends SavedValuationSummary {
  payload?: ValuationResponse;
}

export interface ValuationHistoryResponse {
  items: SavedValuationSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SavedVehicle {
  id: string;
  brand: string;
  model: string;
  variant?: string;
  year: number;
  fuel_type?: string;
  transmission?: string;
  km_driven: number;
  city: string;
  notes?: string;
  created_at: string;
}

export interface SavedVehicleListResponse {
  items: SavedVehicle[];
  total: number;
}

export interface ShareTokenResponse {
  share_token: string;
  share_url: string;
  is_active: boolean;
  created_at: string;
  view_count: number;
}

export interface SharedValuationResponse {
  share_token: string;
  created_at: string;
  brand: string;
  model: string;
  variant?: string;
  year: number;
  fuel_type?: string;
  transmission?: string;
  km_driven: number;
  city: string;
  asking_price?: number;
  estimated_value: number;
  range_low?: number;
  range_high?: number;
  model_interval_low?: number;
  model_interval_high?: number;
  market_median?: number;
  comparable_count: number;
  model_version: string;
  dataset_version: string;
  payload?: ValuationResponse;
  disclaimer: string;
}

export interface VehicleComparisonItem {
  id: string;
  source_type: string;
  brand: string;
  model: string;
  variant?: string;
  year: number;
  km_driven: number;
  fuel_type?: string;
  transmission?: string;
  city: string;
  asking_price?: number;
  estimated_value?: number;
  range_low?: number;
  range_high?: number;
  market_median?: number;
  model_version?: string;
  dataset_version?: string;
}

export interface EmpiricalDeltaItem {
  metric: string;
  description: string;
  baseline_vehicle_id: string;
  target_vehicle_id: string;
  numerical_delta?: number;
}

export interface ComparisonResponse {
  vehicles: VehicleComparisonItem[];
  empirical_differences: EmpiricalDeltaItem[];
  factual_summary: string;
}

export interface HistoricalMarketPeriod {
  period: string;
  listing_count: number;
  median_price: number;
  mean_price: number;
  p25: number;
  p75: number;
}

export interface HistoricalMarketResponse {
  status: string;
  message?: string;
  time_period: string;
  total_listings_analyzed: number;
  history: HistoricalMarketPeriod[];
  observed_change?: {
    initial_period: string;
    latest_period: string;
    initial_median_price: number;
    latest_median_price: number;
    absolute_change: number;
    percentage_change: number;
    description: string;
  };
  disclaimer: string;
}

// ==================== Phase 11 Decision Intelligence Interfaces ====================

export interface DealAnalysis {
  asking_price?: number | null;
  estimated_value: number;
  market_median?: number | null;
  market_range?: {
    p25?: number | null;
    p75?: number | null;
  } | null;
  asking_price_vs_ml?: number | null;
  asking_price_vs_market_median?: number | null;
  asking_price_vs_p25?: number | null;
  asking_price_vs_p75?: number | null;
  percentage_difference_from_ml?: number | null;
  percentage_difference_from_market_median?: number | null;
  comparable_support_score: number;
  evidence_strength: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
  price_position: string;
  classification:
    | 'SIGNIFICANTLY_BELOW_MARKET'
    | 'BELOW_MARKET'
    | 'FAIRLY_PRICED'
    | 'ABOVE_MARKET'
    | 'SIGNIFICANTLY_ABOVE_MARKET'
    | 'INSUFFICIENT_EVIDENCE';
  explanation: string;
  thresholds_used: Record<string, any>;
}

export interface NegotiationAnalysis {
  observed_market_median?: number | null;
  observed_market_p25?: number | null;
  observed_market_p75?: number | null;
  model_estimate: number;
  model_interval_low?: number | null;
  model_interval_high?: number | null;
  asking_price?: number | null;
  negotiation_gap?: number | null;
  evidence_supported_target: number;
  conservative_target: number;
  aggressive_target: number;
  negotiation_range_formatted: string;
  buyer_leverage: string;
  talking_points: string[];
  disclaimer: string;
}

export interface ValueScore {
  price_value_score?: number | null;
  mileage_value_score: number;
  age_value_score: number;
  market_support_score: number;
  evidence_confidence: string;
  overall_value_score: number;
  rating_label: string;
  score_breakdown: Record<string, any>;
  disclaimer: string;
}

export interface DataConfidence {
  market_confidence: string;
  data_completeness: number;
  comparable_quality: string;
  model_confidence: string;
  condition_unknown_warning: boolean;
  unverified_factors: string[];
  disclaimer_text: string;
}

export interface ScenarioResponse {
  base_estimate: number;
  scenario_estimate: number;
  estimated_change: number;
  percentage_change: number;
  changed_features: string[];
  explanation: string[];
  simulation_note: string;
}

export interface AlternativeVehicleQuery {
  target_budget?: number;
  budget_min?: number;
  budget_max?: number;
  brand?: string;
  fuel_type?: string;
  transmission?: string;
  city?: string;
  min_year?: number;
  max_km?: number;
  limit?: number;
}

export interface AlternativeVehicleItem {
  listing_id: string;
  brand: string;
  model: string;
  variant?: string;
  year: number;
  km_driven: number;
  fuel_type?: string;
  transmission?: string;
  city?: string;
  listed_price: number;
  listed_price_formatted: string;
  estimated_value?: number;
  price_proximity_score: number;
  age_score: number;
  mileage_score: number;
  overall_match_score: number;
  match_reasons: string[];
}

export interface AlternativeVehicleResponse {
  query: Record<string, any>;
  count: number;
  results: AlternativeVehicleItem[];
  ranking_methodology: string;
  disclaimer: string;
}

export interface MarketTiming {
  brand: string;
  model: string;
  city?: string;
  recent_median?: number | null;
  previous_median?: number | null;
  percentage_movement?: number | null;
  direction: 'RISING' | 'STABLE' | 'DECLINING' | 'INSUFFICIENT_DATA';
  observation_count: number;
  evidence_strength: string;
  summary: string;
  disclaimer: string;
}

export interface WatchlistItem {
  id: string;
  user_id: string;
  brand: string;
  model: string;
  variant?: string;
  year: number;
  fuel_type?: string;
  transmission?: string;
  km_driven: number;
  city: string;
  notes?: string;
  watch_status?: string;
  last_checked_at?: string;
  last_estimated_value?: number;
  previous_estimated_value?: number;
  value_change?: number;
  value_change_percentage?: number;
  market_median?: number;
  created_at: string;
}

export interface DecisionIntelligenceResponse {
  request_id: string;
  vehicle: ValuationRequest;
  valuation: ValuationData;
  market_statistics: MarketStats;
  deal_analysis: DealAnalysis;
  negotiation: NegotiationAnalysis;
  value_score: ValueScore;
  confidence: DataConfidence;
  market_timing: MarketTiming;
  shap_explanations: ExplanationItem[];
  comparables: ComparableItem[];
  risk?: RiskAnalysisResponse;
  tco?: TCOResponse;
  forecast?: ForecastResponse | null;
}

// ==================== Phase 12 Risk & Trust Intelligence Interfaces ====================

export interface RiskFactor {
  key: string;
  name: string;
  score: number;
  severity: 'VERY_LOW' | 'LOW' | 'MODERATE' | 'HIGH' | 'VERY_HIGH';
  weight: number;
  weighted_contribution: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
  evidence: string[];
  interpretation: string;
}

export interface RiskEvidenceSummary {
  comparables_count: number;
  market_evidence_density: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
  data_completeness: number;
  source_diversity: 'HIGH' | 'MEDIUM' | 'LOW' | 'SINGLE_SOURCE';
  sources_count: number;
  price_dispersion_pct?: number | null;
  uncertainty_width_pct?: number | null;
}

export interface RiskAnalysisResponse {
  risk_score: number;
  risk_level: 'VERY_LOW' | 'LOW' | 'MODERATE' | 'HIGH' | 'VERY_HIGH' | 'INSUFFICIENT_EVIDENCE';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
  summary: string;
  recommendation: string;
  factors: RiskFactor[];
  positive_signals: string[];
  risk_signals: string[];
  unknowns: string[];
  evidence_summary: RiskEvidenceSummary;
  disclaimer: string;
  weights_used: Record<string, number>;
}

export interface BatchRiskItem {
  vehicle_identifier: string;
  brand: string;
  model: string;
  year: number;
  km_driven: number;
  city: string;
  estimated_value: number;
  asking_price?: number | null;
  risk_score: number;
  risk_level: string;
  confidence: string;
  top_risks: string[];
  top_positive_signals: string[];
}

export interface BatchRiskRequest {
  vehicles: ValuationRequest[];
}

export interface BatchRiskResponse {
  total_vehicles: number;
  results: BatchRiskItem[];
  disclaimer: string;
}

// ==================== Phase 13 TCO & Resale Intelligence Interfaces ====================

export interface TCOAssumptions {
  annual_km?: number;
  ownership_years?: number;
  fuel_price?: number;
  fuel_efficiency?: number;
  annual_insurance_rate?: number;
  custom_annual_insurance?: number;
  annual_maintenance?: number;
  other_annual_cost?: number;
  purchase_price_mode?: 'FAIR_VALUE' | 'ASKING_PRICE' | 'CUSTOM';
  custom_purchase_price?: number;
}

export interface TCOPurchaseInfo {
  mode: string;
  price: number;
  price_formatted: string;
  source: string;
}

export interface TCOCostBreakdown {
  purchase_cost: number;
  purchase_cost_formatted: string;
  fuel_cost: number;
  fuel_cost_formatted: string;
  insurance_cost: number;
  insurance_cost_formatted: string;
  maintenance_cost: number;
  maintenance_cost_formatted: string;
  other_costs: number;
  other_costs_formatted: string;
  gross_cost: number;
  gross_cost_formatted: string;
  estimated_resale: number;
  estimated_resale_formatted: string;
  net_tco: number;
  net_tco_formatted: string;
  annual_cost: number;
  annual_cost_formatted: string;
  cost_per_km: number;
  total_projected_km: number;
}

export interface ResaleProjection {
  estimated_resale_value: number;
  estimated_resale_formatted: string;
  lower_bound: number;
  lower_bound_formatted: string;
  upper_bound: number;
  upper_bound_formatted: string;
  confidence: 'VERY_LOW' | 'LOW' | 'MODERATE' | 'HIGH' | 'VERY_HIGH' | 'INSUFFICIENT_EVIDENCE';
  projected_retention_pct: number;
  annual_depreciation_rate: number;
  methodology: string;
}

export interface YearlyProjectionItem {
  year: number;
  vehicle_age: number;
  cumulative_km: number;
  annual_fuel_cost?: number;
  annual_insurance_cost?: number;
  annual_maintenance_cost?: number;
  annual_running_cost?: number;
  cumulative_expenditure?: number;
  projected_resale_value?: number;
  projected_resale_low?: number;
  projected_resale_high?: number;
  resale_value?: number;
  resale_value_formatted?: string;
  resale_low?: number;
  resale_low_formatted?: string;
  resale_high?: number;
  resale_high_formatted?: string;
  cumulative_fuel?: number;
  cumulative_insurance?: number;
  cumulative_maintenance?: number;
  cumulative_other?: number;
  cumulative_gross?: number;
  cumulative_gross_formatted?: string;
  net_cost_to_date: number;
  net_cost_to_date_formatted?: string;
  cost_per_km_to_date?: number;
}

export interface TCOSensitivityItem {
  variable: string;
  baseline_value: string;
  perturbation: string;
  new_net_tco: number;
  new_net_tco_formatted: string;
  absolute_impact_inr: number;
  impact_formatted: string;
  impact_percentage: number;
  direction: 'INCREASE' | 'DECREASE' | 'NEUTRAL';
}

export interface ScenarioSummary {
  name: string;
  description: string;
  multipliers_applied: Record<string, number>;
  net_tco: number;
  net_tco_formatted: string;
  annual_cost: number;
  annual_cost_formatted: string;
  cost_per_km: number;
  estimated_resale: number;
  estimated_resale_formatted: string;
}

export interface TCOResponse {
  vehicle: Record<string, any>;
  purchase: TCOPurchaseInfo;
  assumptions: Record<string, any>;
  assumption_provenance: Record<string, string>;
  ownership: TCOCostBreakdown;
  resale: ResaleProjection;
  yearly_projection: YearlyProjectionItem[];
  scenarios: Record<string, ScenarioSummary>;
  sensitivity: TCOSensitivityItem[];
  disclaimer: string;
}

export interface TCOScenarioRequest {
  vehicle_data: ValuationRequest;
  base_assumptions?: TCOAssumptions;
  scenario_overrides?: Record<string, any>;
}

export interface TCOCompareItem {
  identifier: string;
  brand: string;
  model: string;
  year: number;
  fuel_type?: string;
  purchase_price: number;
  purchase_price_formatted: string;
  ownership_years: number;
  total_km: number;
  gross_cost: number;
  gross_cost_formatted: string;
  estimated_resale: number;
  estimated_resale_formatted: string;
  net_tco: number;
  net_tco_formatted: string;
  annual_cost: number;
  annual_cost_formatted: string;
  cost_per_km: number;
  resale_retention_pct: number;
  confidence: string;
}

export interface TCOCompareRequest {
  vehicles: Array<{
    vehicle_data: ValuationRequest;
    assumptions?: TCOAssumptions;
  }>;
}

export interface TCOCompareResponse {
  total_vehicles: number;
  ownership_horizon_years: number;
  comparison_matrix: TCOCompareItem[];
  break_even_analysis?: Record<string, any>;
  factual_summary: string;
  disclaimer: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  active_model_version: string;
  dataset_version: string;
  timestamp: string;
}

export interface ReadinessResponse {
  status: string;
  ready: boolean;
  checks: {
    database: { status: string; latency_ms?: number; error?: string };
    model_artifact: { status: string; version?: string; checksum_verified?: boolean; error?: string };
    preprocessor_artifact: { status: string; checksum_verified?: boolean; error?: string };
    dataset_records: { status: string; record_count?: number; error?: string };
  };
  timestamp: string;
}

export interface DataQualityResponse {
  dataset_version: string;
  total_records: number;
  unique_records: number;
  duplicate_candidates_filtered: number;
  readiness_status: string;
  features_covered: string[];
  missingness_summary: Record<string, number>;
  source_distribution: Record<string, number>;
  last_transformation_timestamp?: string;
}

export interface DriftReportResponse {
  model_version: string;
  status: 'healthy' | 'warning' | 'insufficient_data';
  timestamp: string;
  baseline_samples: number;
  production_samples: number;
  features: Record<string, {
    psi?: number;
    ks_pvalue?: number;
    status: string;
    drift_detected: boolean;
  }>;
}

// ==================== Phase 14 Market Forecasting & Buy/Sell Timing Interfaces ====================

export type TrendDirection = 'RISING' | 'STABLE' | 'DECLINING' | 'INSUFFICIENT_EVIDENCE';
export type ForecastConfidenceLevel = 'HIGH' | 'MODERATE' | 'LOW' | 'INSUFFICIENT_EVIDENCE';
export type TimingSignal = 'FAVORABLE' | 'NEUTRAL' | 'UNFAVORABLE' | 'INSUFFICIENT_EVIDENCE';
export type ForecastScenarioType = 'CONSERVATIVE' | 'BASE' | 'OPTIMISTIC';
export type MarketVolatilityLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'INSUFFICIENT_EVIDENCE';
export type DemandSignalLevel = 'STRONG' | 'MODERATE' | 'WEAK' | 'INSUFFICIENT_EVIDENCE';

export interface HistoricalMarketPoint {
  period_start: string;
  period_end: string;
  period_label: string;
  observation_count: number;
  median_price: number;
  mean_price: number;
  p25_price: number;
  p75_price: number;
  min_price: number;
  max_price: number;
  dispersion_cv: number;
  median_formatted: string;
}

export interface TrendMetrics {
  period: string;
  period_days: number;
  observation_count: number;
  historical_median?: number | null;
  current_median?: number | null;
  absolute_change?: number | null;
  price_change_pct?: number | null;
  annualized_change_pct?: number | null;
  direction: TrendDirection;
  description: string;
}

export interface MarketMomentum {
  m30d: TrendMetrics;
  m90d: TrendMetrics;
  m180d: TrendMetrics;
  m365d: TrendMetrics;
  overall_direction: TrendDirection;
  velocity_summary: string;
}

export interface MarketVolatility {
  level: MarketVolatilityLevel;
  coefficient_of_variation?: number | null;
  interquartile_range?: number | null;
  price_spread?: number | null;
  rolling_std?: number | null;
  explanation: string;
}

export interface DemandSignal {
  level: DemandSignalLevel;
  signal_name: string;
  listing_count_growth_pct?: number | null;
  listing_density_score?: number | null;
  price_consistency_score?: number | null;
  basis_explanation: string;
}

export interface DepreciationTrajectory {
  historical_observed_annual_pct?: number | null;
  forecast_annual_pct?: number | null;
  phase13_baseline_annual_pct: number;
  methodology_comparison: string;
}

export interface MarketPositionComparison {
  current_market_median?: number | null;
  current_price_vs_30d_pct?: number | null;
  current_price_vs_90d_pct?: number | null;
  current_price_vs_180d_pct?: number | null;
  current_price_vs_365d_pct?: number | null;
  historical_percentile_position?: number | null;
  position_summary: string;
}

export interface ForecastScenario {
  scenario_type: ForecastScenarioType;
  horizon_days: number;
  projected_value: number;
  projected_value_formatted: string;
  change_from_current_pct: number;
  change_from_current_amount: number;
  annual_depreciation_rate_pct: number;
  lower_bound: number;
  upper_bound: number;
  lower_bound_formatted: string;
  upper_bound_formatted: string;
}

export interface ForecastPoint {
  horizon_days: number;
  horizon_label: string;
  base_price: number;
  lower_bound: number;
  upper_bound: number;
  base_formatted: string;
  lower_formatted: string;
  upper_formatted: string;
  change_pct: number;
  change_amount: number;
  confidence: ForecastConfidenceLevel;
  supporting_observations: number;
  scenarios: Record<string, ForecastScenario>;
}

export interface TimingFactor {
  factor_type: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  title: string;
  description: string;
  impact_weight: number;
}

export interface TimingScore {
  score?: number | null;
  signal: TimingSignal;
  rating_label: string;
  factors: TimingFactor[];
  positive_factors: string[];
  negative_factors: string[];
  methodology_summary: string;
  disclaimer: string;
}

export interface ForecastEvidence {
  observation_count: number;
  history_days: number;
  earliest_observation_date?: string | null;
  latest_observation_date?: string | null;
  segment_level: string;
  segment_hierarchy_used: string;
  segment_fallback_applied: boolean;
  forecast_model_version: string;
  forecast_method: string;
  source: string;
  data_density_score: number;
  temporal_coverage_score: number;
  dispersion_score: number;
  confidence_reasons: string[];
  missing_evidence_reasons: string[];
}

export interface ForecastAlert {
  alert_type: string;
  title: string;
  description: string;
  previous_value?: string | null;
  current_value?: string | null;
  severity: string;
  triggered_at: string;
}

export interface ForecastResponse {
  status: 'AVAILABLE' | 'INSUFFICIENT_EVIDENCE';
  brand: string;
  model: string;
  variant?: string | null;
  year: number;
  city?: string | null;
  fuel_type?: string | null;
  transmission?: string | null;
  current_market_median?: number | null;
  current_market_median_formatted?: string | null;
  trend_summary: string;
  overall_trend: TrendDirection;
  momentum: MarketMomentum;
  volatility: MarketVolatility;
  demand_proxy: DemandSignal;
  depreciation: DepreciationTrajectory;
  market_position: MarketPositionComparison;
  forecast_points: ForecastPoint[];
  scenarios: Record<string, ForecastScenario[]>;
  buy_timing: TimingScore;
  sell_timing: TimingScore;
  forecast_confidence: ForecastConfidenceLevel;
  forecast_confidence_score: number;
  evidence: ForecastEvidence;
  historical_points: HistoricalMarketPoint[];
  alerts: ForecastAlert[];
  limitations: string[];
  disclaimer: string;
  request_id?: string | null;
  latency_ms?: number | null;
}

export interface BatchForecastResponse {
  items: ForecastResponse[];
  count: number;
  processing_time_ms: number;
}

// ==================== Phase 15 Vehicle Lifecycle & Ownership Decision Interfaces ====================

export type LifecycleAction = 'BUY' | 'KEEP' | 'SELL_NOW' | 'WAIT' | 'REPLACE' | 'INSUFFICIENT_EVIDENCE';
export type DecisionConfidence = 'HIGH' | 'MODERATE' | 'LOW' | 'INSUFFICIENT_EVIDENCE';
export type FactorDirection = 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
export type LifecycleScenarioType = 'CONSERVATIVE' | 'BASE' | 'OPTIMISTIC';
export type DataIntegrityType = 'OBSERVED' | 'DERIVED' | 'USER_DEFINED' | 'DEFAULT_ASSUMPTION' | 'FORECAST';
export type DecisionMode = 'BUY' | 'OWNER';

export interface LifecycleDecisionRequest {
  mode?: DecisionMode;
  brand: string;
  model: string;
  variant?: string | null;
  year: number;
  fuel_type?: string | null;
  transmission?: string | null;
  km_driven?: number | null;
  city?: string | null;
  asking_price?: number | null;
  current_market_value?: number | null;
  purchase_price?: number | null;
  ownership_years?: number | null;
  annual_km?: number | null;
  horizon_years?: number | null;
  scenario?: LifecycleScenarioType | null;
  fuel_price_override?: number | null;
  include_alternatives?: boolean | null;
}

export interface DecisionFactor {
  category: string;
  factor_text: string;
  direction: FactorDirection;
  metric_name: string;
  metric_value?: any;
  impact_weight: number;
  source_type: DataIntegrityType;
}

export interface DecisionCategoryScore {
  category_name: string;
  score: number;
  weight: number;
  contribution: number;
  reasoning: string;
}

export interface DecisionScore {
  overall_score: number;
  category_breakdown: DecisionCategoryScore[];
  decision_margin: number;
  winning_action: LifecycleAction;
  secondary_action?: LifecycleAction | null;
  action_scores: Record<string, number>;
}

export interface LifecycleHorizonOutlook {
  horizon_years: number;
  projected_resale_value: number;
  projected_resale_formatted: string;
  cumulative_depreciation: number;
  cumulative_depreciation_formatted: string;
  cumulative_ownership_cost: number;
  cumulative_ownership_formatted: string;
  total_cost_of_ownership: number;
  total_cost_of_ownership_formatted: string;
  cost_per_km: number;
  cost_per_km_formatted: string;
  replacement_advantage?: number | null;
}

export interface ReplacementCandidate {
  id: string;
  brand: string;
  model: string;
  variant?: string | null;
  year: number;
  fuel_type?: string | null;
  transmission?: string | null;
  estimated_purchase_price: number;
  estimated_purchase_price_formatted: string;
  fair_value: number;
  five_year_tco: number;
  five_year_tco_formatted: string;
  cost_per_km: number;
  projected_resale: number;
  projected_resale_formatted: string;
  risk_level: string;
  risk_score: number;
  buy_timing_score: number;
  forecast_direction: string;
  tco_savings_5y: number;
  tco_savings_5y_formatted: string;
  resale_advantage: number;
  replacement_advantage_score: number;
  break_even_months?: number | null;
  recommendation_reason: string;
}

export interface LifecycleScenario {
  scenario_type: LifecycleScenarioType;
  action: LifecycleAction;
  decision_score: number;
  five_year_tco: number;
  five_year_tco_formatted: string;
  projected_resale: number;
  projected_resale_formatted: string;
  key_assumption: string;
}

export interface DecisionSensitivity {
  variable_name: string;
  current_value: any;
  threshold_value: any;
  action_before: LifecycleAction;
  action_after: LifecycleAction;
  sensitivity_description: string;
}

export interface LifecycleDecision {
  decision_version: string;
  timestamp: string;
  mode: string;
  vehicle_summary: Record<string, any>;
  recommended_action: LifecycleAction;
  decision_score: DecisionScore;
  confidence: DecisionConfidence;
  confidence_score: number;
  confidence_reasons: string[];
  alternative_actions: Array<{ action: string; score: number; score_diff: number }>;
  positive_factors: DecisionFactor[];
  negative_factors: DecisionFactor[];
  economic_reasoning: string;
  market_reasoning: string;
  ownership_reasoning: string;
  risk_considerations: string[];
  forecast_considerations: string[];
  resale_considerations: string[];
  tco_considerations: string[];
  horizon_outlooks: LifecycleHorizonOutlook[];
  scenarios: LifecycleScenario[];
  replacement_candidates: ReplacementCandidate[];
  best_replacement_candidate?: ReplacementCandidate | null;
  decision_sensitivities: DecisionSensitivity[];
  missing_data: string[];
  assumptions: string[];
  limitations: string[];
  audit_trail: Record<string, any>;
}

export interface LifecycleScenarioRequest {
  base_request: LifecycleDecisionRequest;
  annual_km_override?: number | null;
  wait_months?: number | null;
  purchase_price_override?: number | null;
  market_shift_pct?: number | null;
  replacement_candidate_id?: string | null;
}

export interface LifecycleCompareRequest {
  current_vehicle: LifecycleDecisionRequest;
  replacement_vehicles: LifecycleDecisionRequest[];
}

export interface LifecycleCompareItem {
  vehicle_label: string;
  brand: string;
  model: string;
  year: number;
  fuel_type?: string | null;
  purchase_price?: number | null;
  purchase_price_formatted: string;
  fair_value: number;
  fair_value_formatted: string;
  five_year_tco: number;
  five_year_tco_formatted: string;
  cost_per_km: number;
  cost_per_km_formatted: string;
  projected_resale: number;
  projected_resale_formatted: string;
  risk_score: number;
  risk_level: string;
  buy_timing_score: number;
  sell_timing_score: number;
  market_forecast: string;
  replacement_advantage?: number | null;
  lifecycle_action: LifecycleAction;
  decision_score: number;
}

export interface LifecycleCompareResponse {
  items: LifecycleCompareItem[];
  best_overall_vehicle: string;
  comparison_matrix: Record<string, any>;
  summary_reasoning: string;
}

export interface BatchLifecycleRequest {
  vehicles: LifecycleDecisionRequest[];
}

export interface BatchLifecycleResponse {
  total_vehicles: number;
  results: LifecycleDecision[];
}

// ==================== Phase 16 Garage & Portfolio Intelligence Interfaces ====================

export type OwnershipStatus = 'OWNED' | 'CONSIDERING' | 'SOLD' | 'WATCHING';
export type UtilizationClass = 'HIGH' | 'MODERATE' | 'LOW' | 'INSUFFICIENT_EVIDENCE';
export type PortfolioAction = 'KEEP_GARAGE' | 'SELL_VEHICLE' | 'REPLACE_VEHICLE' | 'CONSOLIDATE' | 'INSUFFICIENT_EVIDENCE';
export type PortfolioConfidence = 'HIGH' | 'MODERATE' | 'LOW' | 'INSUFFICIENT_EVIDENCE';
export type GarageScenarioActionType = 'SELL' | 'KEEP' | 'REPLACE' | 'UPDATE_MILEAGE' | 'ADD';

export interface GarageVehicle {
  id: string;
  user_id: string;
  valuation_id?: string | null;
  brand: string;
  model: string;
  variant?: string | null;
  year: number;
  fuel_type?: string | null;
  transmission?: string | null;
  city?: string | null;
  nickname?: string | null;
  ownership_status: OwnershipStatus;
  purchase_price?: number | null;
  purchase_date?: string | null;
  current_odometer?: number | null;
  annual_km?: number | null;
  ownership_purpose?: string | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface GarageVehicleCreate {
  brand: string;
  model: string;
  variant?: string | null;
  year: number;
  fuel_type?: string | null;
  transmission?: string | null;
  city?: string | null;
  nickname?: string | null;
  ownership_status?: OwnershipStatus;
  purchase_price?: number | null;
  purchase_date?: string | null;
  current_odometer?: number | null;
  annual_km?: number | null;
  ownership_purpose?: string | null;
  notes?: string | null;
  valuation_id?: string | null;
}

export interface GarageVehicleUpdate {
  brand?: string | null;
  model?: string | null;
  variant?: string | null;
  year?: number | null;
  fuel_type?: string | null;
  transmission?: string | null;
  city?: string | null;
  nickname?: string | null;
  ownership_status?: OwnershipStatus | null;
  purchase_price?: number | null;
  purchase_date?: string | null;
  current_odometer?: number | null;
  annual_km?: number | null;
  ownership_purpose?: string | null;
  notes?: string | null;
  valuation_id?: string | null;
}

export interface GarageVehicleSnapshot {
  vehicle: GarageVehicle;
  current_estimated_value?: number | null;
  current_estimated_value_formatted: string;
  market_median?: number | null;
  five_year_tco?: number | null;
  five_year_tco_formatted: string;
  annual_ownership_cost?: number | null;
  annual_ownership_cost_formatted: string;
  cost_per_km?: number | null;
  cost_per_km_formatted: string;
  projected_resale_5y?: number | null;
  projected_resale_formatted?: string;
  projected_5y_resale?: number | null;
  projected_5y_resale_formatted?: string;
  five_year_depreciation?: number | null;
  five_year_depreciation_formatted?: string;
  annual_depreciation_rate?: number | null;
  risk_score: number;
  risk_level: string;
  market_trend: string;
  market_momentum_90d?: string;
  momentum_90d?: number;
  buy_timing_score: number;
  sell_timing_score: number;
  lifecycle_action: string;
  lifecycle_score: number;
  confidence: string;
  utilization_class: UtilizationClass;
  monthly_km?: number;
  data_provenance?: Record<string, string>;
}

export interface GarageSummary {
  total_vehicles: number;
  owned_vehicles?: number;
  owned_vehicles_count?: number;
  considering_vehicles?: number;
  considering_vehicles_count?: number;
  watching_vehicles?: number;
  sold_vehicles?: number;
  total_current_value: number;
  total_current_value_formatted: string;
  total_annual_cost: number;
  total_annual_cost_formatted: string;
  total_5y_tco: number;
  total_5y_tco_formatted: string;
  total_projected_5y_resale: number;
  total_projected_5y_resale_formatted: string;
  average_cost_per_km: number;
  average_cost_per_km_formatted: string;
  weighted_average_risk: number;
  risk_level_label?: string;
  overall_market_direction: string;
  weighted_market_momentum?: number | string;
  aggregation_provenance?: Record<string, string>;
  excluded_vehicles_count?: number;
  excluded_vehicle_reasons?: string[];
}

export interface GarageEfficiencyCategory {
  category_name: string;
  score: number;
  weight: number;
  contribution: number;
  reasoning: string;
}

export interface GarageEfficiencyComponent {
  component_name: string;
  score: number;
  weight: number;
  contribution: number;
  reason: string;
}

export interface GarageEfficiencyScore {
  overall_score: number;
  rating_label?: string;
  categories?: GarageEfficiencyCategory[];
  components?: GarageEfficiencyComponent[];
  summary?: string;
  summary_reasoning?: string;
}

export interface VehicleRankingItem {
  vehicle_id: string;
  vehicle_label: string;
  metric_value: number;
  metric_formatted: string;
  rank: number;
}

export interface VehicleRankings {
  most_expensive_annual?: VehicleRankingItem[] | string[];
  highest_5y_tco?: VehicleRankingItem[] | string[];
  highest_cost_per_km?: VehicleRankingItem[] | string[];
  highest_depreciation?: VehicleRankingItem[] | string[];
  highest_depreciation_exposure?: string[];
  highest_risk?: VehicleRankingItem[] | string[];
  highest_projected_resale_loss?: string[];
}

export interface SellFirstItem {
  vehicle_id: string;
  vehicle_label?: string;
  vehicle_display_name?: string;
  sell_priority_score: number;
  current_value?: number | null;
  current_value_formatted: string;
  sell_timing_score: number;
  depreciation_rate?: number | null;
  projected_resale_decline_pct?: number | null;
  annual_cost?: number | null;
  annual_cost_formatted?: string;
  annual_ownership_cost?: number | null;
  annual_ownership_cost_formatted?: string;
  lifecycle_signal?: string;
  factors?: string[];
  reasons?: string[];
  negatives?: string[];
  recommendation?: string;
}

export interface KeepFirstItem {
  vehicle_id: string;
  vehicle_label?: string;
  vehicle_display_name?: string;
  keep_priority_score: number;
  five_year_tco?: number | null;
  five_year_tco_formatted: string;
  cost_per_km?: number | null;
  cost_per_km_formatted: string;
  risk_score: number;
  risk_level?: string;
  market_trend: string;
  factors?: string[];
  reasons?: string[];
}

export interface ReplacementOpportunityItem {
  current_vehicle_id: string;
  current_vehicle_label?: string;
  current_vehicle_name?: string;
  candidate_brand?: string;
  candidate_model?: string;
  candidate_year?: number;
  candidate_replacement_name?: string;
  candidate_replacement_brand?: string;
  candidate_replacement_model?: string;
  estimated_purchase_diff?: number;
  purchase_difference?: number;
  purchase_difference_formatted?: string;
  tco_savings_5y?: number;
  tco_savings_5y_formatted?: string;
  tco_difference?: number;
  tco_difference_formatted?: string;
  cost_per_km_difference?: number;
  resale_advantage?: number;
  resale_difference?: number;
  resale_difference_formatted?: string;
  risk_difference?: number;
  market_timing_advantage?: string;
  lifecycle_advantage?: string;
  replacement_score?: number;
  replacement_opportunity_score?: number;
  break_even_months?: number | null;
  recommendation_reason?: string;
  recommendation_rationale?: string;
}

export interface VehicleRedundancyItem {
  vehicle_a_id: string;
  vehicle_a_label?: string;
  vehicle_a_name?: string;
  vehicle_b_id: string;
  vehicle_b_label?: string;
  vehicle_b_name?: string;
  redundancy_level: 'HIGH' | 'MODERATE' | 'LOW' | 'INSUFFICIENT_EVIDENCE' | 'NONE';
  overlap_reasons?: string[];
  overlap_factors: string[];
  potential_annual_savings?: number;
  potential_annual_savings_formatted?: string;
  recommendation?: string;
}

export interface GarageRecommendation {
  action: PortfolioAction;
  portfolio_action_score?: number;
  confidence: PortfolioConfidence;
  confidence_score: number;
  confidence_factors?: string[];
  reasons?: string[];
  economic_impact_summary?: string;
  headline?: string;
  primary_reasons?: string[];
  caution_factors?: string[];
  suggested_next_steps?: string[];
}

export interface GarageIntelligenceResponse {
  engine_version?: string;
  user_id?: string;
  evaluated_at?: string;
  summary: GarageSummary;
  snapshots: GarageVehicleSnapshot[];
  vehicle_snapshots?: GarageVehicleSnapshot[];
  efficiency?: GarageEfficiencyScore;
  efficiency_score?: GarageEfficiencyScore;
  rankings?: VehicleRankings;
  vehicle_rankings?: VehicleRankings;
  sell_first_ranking: SellFirstItem[];
  keep_first_ranking: KeepFirstItem[];
  replacement_opportunities: ReplacementOpportunityItem[];
  redundancies?: VehicleRedundancyItem[];
  redundancy_analysis: VehicleRedundancyItem[];
  recommendation: GarageRecommendation;
  limitations: string[];
  disclaimer?: string;
}

export interface GarageScenarioVehicleAction {
  vehicle_id: string;
  action_type: GarageScenarioActionType;
  replacement_vehicle?: {
    brand: string;
    model: string;
    variant?: string | null;
    year: number;
    fuel_type?: string | null;
    transmission?: string | null;
    city?: string | null;
    purchase_price?: number | null;
    annual_km?: number | null;
    current_odometer?: number | null;
  } | null;
  annual_km_override?: number | null;
}

export interface GarageScenarioRequest {
  actions: GarageScenarioVehicleAction[];
  ownership_horizon_years?: number;
}

export interface GarageScenarioResponse {
  scenario_version: string;
  simulated_at: string;
  baseline_summary: GarageSummary;
  scenario_summary: GarageSummary;
  baseline_efficiency: GarageEfficiencyScore;
  scenario_efficiency: GarageEfficiencyScore;
  delta_current_value: number;
  delta_current_value_formatted: string;
  delta_annual_cost: number;
  delta_annual_cost_formatted: string;
  delta_5y_tco: number;
  delta_5y_tco_formatted: string;
  delta_efficiency_score: number;
  break_even_months?: number | null;
  portfolio_impact_summary: string;
  baseline_snapshots: GarageVehicleSnapshot[];
  scenario_snapshots: GarageVehicleSnapshot[];
}

export interface GarageCompareRequest {
  vehicle_ids: string[];
}

export interface GarageCompareResponse {
  total_compared: number;
  vehicles: GarageVehicleSnapshot[];
  lowest_tco_vehicle_id?: string | null;
  lowest_cost_km_vehicle_id?: string | null;
  lowest_risk_vehicle_id?: string | null;
  best_market_trend_vehicle_id?: string | null;
  comparison_notes: string[];
}

export class ApiError extends Error {
  code: string;
  status: number;
  requestId?: string;

  constructor(message: string, code: string = 'API_ERROR', status: number = 500, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

const envApiUrl = (import.meta as any).env?.VITE_API_BASE_URL || (import.meta as any).env?.VITE_API_URL;
const API_BASE_URL = (envApiUrl !== undefined && envApiUrl !== null && envApiUrl !== '')
  ? String(envApiUrl).replace(/\/+$/, '')
  : (typeof window !== 'undefined'
      ? ''
      : 'http://127.0.0.1:8000');
const DEFAULT_TIMEOUT_MS = 15000;

function generateRequestId(): string {
  return 'req-' + Math.random().toString(36).substring(2, 11) + '-' + Date.now().toString(36);
}

const TOKEN_STORAGE_KEY = 'autovalue_token';

// Dual-layer token cache: memory variable + localStorage persistence
let memoryToken: string | null = (typeof window !== 'undefined' && window.localStorage)
  ? window.localStorage.getItem(TOKEN_STORAGE_KEY)
  : null;

export function getAuthToken(): string | null {
  if (memoryToken) return memoryToken;
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      memoryToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      // localStorage restricted
    }
  }
  return memoryToken;
}

export function setAuthToken(token: string | null) {
  memoryToken = token;
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      if (token) {
        window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
      } else {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
    } catch {
      // localStorage restricted
    }
  }
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const headers = new Headers(options.headers || {});
  if (!headers.has('X-Request-ID')) {
    headers.set('X-Request-ID', generateRequestId());
  }
  const token = getAuthToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // Automatically sends HTTP-only session cookie
      headers,
      signal: controller.signal
    });
    return response;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out. Please verify your connection or try again.', 'TIMEOUT_ERROR', 408);
    }
    throw new ApiError(err.message || 'Network connection failed. Backend service may be unreachable.', 'NETWORK_ERROR', 0);
  } finally {
    clearTimeout(timeoutId);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  const requestId = response.headers.get('X-Request-ID') || undefined;

  if (!response.ok) {
    let errorMessage = `Server returned HTTP ${response.status}`;
    let errorCode = 'HTTP_' + response.status;

    try {
      const errorJson = await response.json();
      if (errorJson.error) {
        errorCode = errorJson.error.code || errorCode;
        errorMessage = errorJson.error.message || errorMessage;
      } else if (errorJson.detail) {
        if (typeof errorJson.detail === 'string') {
          errorMessage = errorJson.detail;
        } else if (Array.isArray(errorJson.detail)) {
          errorMessage = errorJson.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
        }
      }
    } catch {
      // Non-JSON response body
    }

    throw new ApiError(errorMessage, errorCode, response.status, requestId);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // ==================== Public Valuation ====================
  async getValuation(payload: ValuationRequest, requestId?: string): Promise<ValuationResponse> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    if (requestId) {
      headers['X-Request-ID'] = requestId;
    }

    const response = await fetchWithTimeout(`${API_BASE_URL}/api/valuation`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });

    return handleResponse<ValuationResponse>(response);
  },

  async getMarketHistory(brand: string, model: string, timePeriod: string = 'all', city?: string): Promise<HistoricalMarketResponse> {
    const params = new URLSearchParams({ brand, model, time_period: timePeriod });
    if (city) params.set('city', city);
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/market/history?${params.toString()}`);
    return handleResponse<HistoricalMarketResponse>(response);
  },

  // ==================== Authentication ====================
  async register(email: string, password: string, full_name?: string): Promise<AuthResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name })
    });
    const data = await handleResponse<AuthResponse>(response);
    setAuthToken(data.access_token);
    return data;
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await handleResponse<AuthResponse>(response);
    setAuthToken(data.access_token);
    return data;
  },

  async logout(): Promise<{ message: string }> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/auth/logout`, {
      method: 'POST'
    });
    setAuthToken(null);
    return handleResponse<{ message: string }>(response);
  },

  async getCurrentUser(): Promise<User | null> {
    const token = getAuthToken();
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/auth/me`);
      if (response.status === 401) {
        if (token) {
          // Token expired or invalidated
          setAuthToken(null);
        }
        return null;
      }
      return await handleResponse<User>(response);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 401) {
        setAuthToken(null);
        return null;
      }
      throw err;
    }
  },

  async updateProfile(full_name: string): Promise<User> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/auth/me`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name })
    });
    return handleResponse<User>(response);
  },

  async deleteAccount(): Promise<{ message: string }> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/auth/me`, {
      method: 'DELETE'
    });
    setAuthToken(null);
    return handleResponse<{ message: string }>(response);
  },

  // ==================== Saved Valuations ====================
  async saveValuation(vehicle: ValuationRequest, valuation_result: ValuationResponse, notes?: string): Promise<SavedValuationSummary> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/valuations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle, valuation_result, notes })
    });
    return handleResponse<SavedValuationSummary>(response);
  },

  async getValuationHistory(page: number = 1, pageSize: number = 10, brand?: string, model?: string): Promise<ValuationHistoryResponse> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (brand) params.set('brand', brand);
    if (model) params.set('model', model);

    const response = await fetchWithTimeout(`${API_BASE_URL}/api/valuations?${params.toString()}`);
    return handleResponse<ValuationHistoryResponse>(response);
  },

  async getSavedValuationById(id: string): Promise<SavedValuationDetail> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/valuations/${id}`);
    return handleResponse<SavedValuationDetail>(response);
  },

  async deleteSavedValuation(id: string): Promise<{ message: string }> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/valuations/${id}`, {
      method: 'DELETE'
    });
    return handleResponse<{ message: string }>(response);
  },

  async shareValuation(id: string): Promise<ShareTokenResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/valuations/${id}/share`, {
      method: 'POST'
    });
    return handleResponse<ShareTokenResponse>(response);
  },

  async revokeValuationShare(id: string): Promise<{ message: string }> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/valuations/${id}/share`, {
      method: 'DELETE'
    });
    return handleResponse<{ message: string }>(response);
  },

  // ==================== Saved Vehicles / Bookmarks ====================
  async getSavedVehicles(): Promise<SavedVehicleListResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/saved-vehicles`);
    return handleResponse<SavedVehicleListResponse>(response);
  },

  async saveVehicle(vehicle: {
    brand: string;
    model: string;
    variant?: string;
    year: number;
    fuel_type?: string;
    transmission?: string;
    km_driven: number;
    city: string;
    notes?: string;
  }): Promise<SavedVehicle> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/saved-vehicles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(vehicle)
    });
    return handleResponse<SavedVehicle>(response);
  },

  async deleteSavedVehicle(id: string): Promise<{ message: string }> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/saved-vehicles/${id}`, {
      method: 'DELETE'
    });
    return handleResponse<{ message: string }>(response);
  },

  // ==================== Vehicle Comparison ====================
  async compareVehicles(valuation_ids?: string[], vehicle_ids?: string[]): Promise<ComparisonResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ valuation_ids, vehicle_ids })
    });
    return handleResponse<ComparisonResponse>(response);
  },

  // ==================== Public Shared Report ====================
  async getSharedReport(token: string): Promise<SharedValuationResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/shared/${token}`);
    return handleResponse<SharedValuationResponse>(response);
  },

  // ==================== Telemetry & Quality ====================
  async getHealth(): Promise<HealthResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/health`, {}, 5000);
    return handleResponse<HealthResponse>(response);
  },

  async getReadiness(): Promise<ReadinessResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/ready`, {}, 5000);
    return handleResponse<ReadinessResponse>(response);
  },

  async getModels(): Promise<any> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/models`, {}, 5000);
    return handleResponse<any>(response);
  },

  async getDataQuality(): Promise<DataQualityResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/data-quality`, {}, 5000);
    return handleResponse<DataQualityResponse>(response);
  },

  async getModelDrift(): Promise<DriftReportResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/models/drift`, {}, 5000);
    return handleResponse<DriftReportResponse>(response);
  },

  // ==================== Phase 11 Decision Intelligence ====================
  async getIntelligence(request: ValuationRequest): Promise<DecisionIntelligenceResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/intelligence`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<DecisionIntelligenceResponse>(response);
  },

  async simulateScenario(
    baseVehicle: ValuationRequest,
    changes: Record<string, any>
  ): Promise<ScenarioResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_vehicle: baseVehicle, changes })
    });
    return handleResponse<ScenarioResponse>(response);
  },

  async getAlternatives(query: AlternativeVehicleQuery): Promise<AlternativeVehicleResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/alternatives`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(query)
    });
    return handleResponse<AlternativeVehicleResponse>(response);
  },

  async getMarketTiming(
    brand: string,
    model: string,
    city?: string,
    timePeriod: string = '6m'
  ): Promise<MarketTiming> {
    const params = new URLSearchParams({ brand, model, time_period: timePeriod });
    if (city) params.append('city', city);
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/market/timing?${params.toString()}`);
    return handleResponse<MarketTiming>(response);
  },

  async getWatchlist(): Promise<WatchlistItem[]> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/watchlist`);
    return handleResponse<WatchlistItem[]>(response);
  },

  async refreshWatchlistVehicle(id: string): Promise<WatchlistItem> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/watchlist/${id}/refresh`, {
      method: 'POST'
    });
    return handleResponse<WatchlistItem>(response);
  },

  async updateWatchlistStatus(id: string, watchStatus: string): Promise<WatchlistItem> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/watchlist/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ watch_status: watchStatus })
    });
    return handleResponse<WatchlistItem>(response);
  },

  // ==================== Phase 12 Risk & Trust Intelligence ====================
  async getRiskAnalysis(request: ValuationRequest): Promise<RiskAnalysisResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/risk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<RiskAnalysisResponse>(response);
  },

  async getSavedValuationRisk(valuationId: string, shareToken?: string): Promise<RiskAnalysisResponse> {
    const url = shareToken
      ? `${API_BASE_URL}/api/risk/${valuationId}?share_token=${encodeURIComponent(shareToken)}`
      : `${API_BASE_URL}/api/risk/${valuationId}`;
    const response = await fetchWithTimeout(url);
    return handleResponse<RiskAnalysisResponse>(response);
  },

  async getBatchRisk(request: BatchRiskRequest): Promise<BatchRiskResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/risk/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<BatchRiskResponse>(response);
  },

  // ==================== Phase 13 Total Cost of Ownership & Resale Intelligence ====================
  async getTCOAnalysis(vehicle: ValuationRequest, assumptions?: TCOAssumptions): Promise<TCOResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/tco`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle_data: vehicle, assumptions })
    });
    return handleResponse<TCOResponse>(response);
  },

  async getSavedValuationTCO(valuationId: string, shareToken?: string, assumptions?: TCOAssumptions): Promise<TCOResponse> {
    const params = new URLSearchParams();
    if (shareToken) params.append('share_token', shareToken);
    if (assumptions?.annual_km) params.append('annual_km', String(assumptions.annual_km));
    if (assumptions?.ownership_years) params.append('ownership_years', String(assumptions.ownership_years));
    if (assumptions?.fuel_price) params.append('fuel_price', String(assumptions.fuel_price));
    if (assumptions?.fuel_efficiency) params.append('fuel_efficiency', String(assumptions.fuel_efficiency));
    if (assumptions?.purchase_price_mode) params.append('purchase_price_mode', assumptions.purchase_price_mode);
    if (assumptions?.custom_purchase_price) params.append('custom_purchase_price', String(assumptions.custom_purchase_price));

    const qs = params.toString() ? `?${params.toString()}` : '';
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/tco/${valuationId}${qs}`);
    return handleResponse<TCOResponse>(response);
  },

  async simulateTCOScenario(request: TCOScenarioRequest): Promise<Record<string, ScenarioSummary>> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/tco/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<Record<string, ScenarioSummary>>(response);
  },

  async compareTCO(vehicles: Array<{ vehicle_data: ValuationRequest; assumptions?: TCOAssumptions }>): Promise<TCOCompareResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/tco/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicles })
    });
    return handleResponse<TCOCompareResponse>(response);
  },

  // ==================== Phase 14 Vehicle Market Forecasting & Buy/Sell Timing ====================
  async getMarketForecast(vehicle: ValuationRequest, horizonDays: number = 365, cutoffDate?: string): Promise<ForecastResponse> {
    const params = new URLSearchParams({
      brand: vehicle.brand,
      model: vehicle.model,
      year: String(vehicle.year),
      horizon_days: String(horizonDays)
    });
    if (vehicle.variant) params.append('variant', vehicle.variant);
    if (vehicle.fuel_type) params.append('fuel_type', vehicle.fuel_type);
    if (vehicle.transmission) params.append('transmission', vehicle.transmission);
    if (vehicle.km_driven) params.append('km_driven', String(vehicle.km_driven));
    if (vehicle.city) params.append('city', vehicle.city);
    if (vehicle.asking_price) params.append('asking_price', String(vehicle.asking_price));
    if (cutoffDate) params.append('cutoff_date', cutoffDate);

    const response = await fetchWithTimeout(`${API_BASE_URL}/api/market/forecast?${params.toString()}`);
    return handleResponse<ForecastResponse>(response);
  },

  async postMarketForecast(request: ValuationRequest & { horizon_days?: number; cutoff_date?: string }): Promise<ForecastResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/market/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<ForecastResponse>(response);
  },

  async getSavedValuationForecast(valuationId: string, shareToken?: string, horizonDays: number = 365): Promise<ForecastResponse> {
    const params = new URLSearchParams({ horizon_days: String(horizonDays) });
    if (shareToken) params.append('share_token', shareToken);

    const response = await fetchWithTimeout(`${API_BASE_URL}/api/market/forecast/${valuationId}?${params.toString()}`);
    return handleResponse<ForecastResponse>(response);
  },

  async batchMarketForecast(vehicles: ValuationRequest[]): Promise<BatchForecastResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/market/forecast/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicles })
    });
    return handleResponse<BatchForecastResponse>(response);
  },

  // ==================== Phase 15 Vehicle Lifecycle & Ownership Decision Intelligence ====================
  async getLifecycleDecision(vehicle: ValuationRequest & { mode?: DecisionMode; annual_km?: number; ownership_years?: number; current_market_value?: number }): Promise<LifecycleDecision> {
    return this.postLifecycleDecision(vehicle);
  },

  async postLifecycleDecision(request: LifecycleDecisionRequest): Promise<LifecycleDecision> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/lifecycle/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<LifecycleDecision>(response);
  },

  async getSavedValuationLifecycle(
    valuationId: string,
    shareToken?: string,
    annualKm?: number,
    horizonYears?: number,
    scenario?: LifecycleScenarioType
  ): Promise<LifecycleDecision> {
    const params = new URLSearchParams();
    if (shareToken) params.append('share_token', shareToken);
    if (annualKm !== undefined) params.append('annual_km', String(annualKm));
    if (horizonYears !== undefined) params.append('horizon_years', String(horizonYears));
    if (scenario) params.append('scenario', scenario);

    const qs = params.toString() ? `?${params.toString()}` : '';
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/lifecycle/${valuationId}${qs}`);
    return handleResponse<LifecycleDecision>(response);
  },

  async simulateLifecycleScenario(request: LifecycleScenarioRequest): Promise<LifecycleDecision> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/lifecycle/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<LifecycleDecision>(response);
  },

  async compareLifecycle(request: LifecycleCompareRequest): Promise<LifecycleCompareResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/lifecycle/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<LifecycleCompareResponse>(response);
  },

  async batchLifecycle(vehicles: LifecycleDecisionRequest[]): Promise<BatchLifecycleResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/lifecycle/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicles })
    });
    return handleResponse<BatchLifecycleResponse>(response);
  },

  // ==================== Phase 16 Garage & Portfolio Intelligence API Methods ====================
  async getGarage(statusFilter?: OwnershipStatus): Promise<GarageVehicle[]> {
    const params = new URLSearchParams();
    if (statusFilter) params.append('status_filter', statusFilter);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage${qs}`);
    return handleResponse<GarageVehicle[]>(response);
  },

  async createGarageVehicle(vehicle: GarageVehicleCreate): Promise<GarageVehicle> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(vehicle)
    });
    return handleResponse<GarageVehicle>(response);
  },

  async getGarageVehicle(id: string): Promise<GarageVehicle> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage/${id}`);
    return handleResponse<GarageVehicle>(response);
  },

  async updateGarageVehicle(id: string, updates: GarageVehicleUpdate): Promise<GarageVehicle> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    return handleResponse<GarageVehicle>(response);
  },

  async deleteGarageVehicle(id: string): Promise<{ success: boolean; message: string; deleted_id: string }> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage/${id}`, {
      method: 'DELETE'
    });
    return handleResponse<{ success: boolean; message: string; deleted_id: string }>(response);
  },

  async getGarageIntelligence(): Promise<GarageIntelligenceResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage/intelligence`);
    return handleResponse<GarageIntelligenceResponse>(response);
  },

  async getGarageVehicleIntelligence(id: string): Promise<GarageVehicleSnapshot> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage/${id}/intelligence`);
    return handleResponse<GarageVehicleSnapshot>(response);
  },

  async compareGarageVehicles(vehicleIds: string[]): Promise<GarageCompareResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle_ids: vehicleIds })
    });
    return handleResponse<GarageCompareResponse>(response);
  },

  async simulateGarageScenario(request: GarageScenarioRequest): Promise<GarageScenarioResponse> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/garage/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    return handleResponse<GarageScenarioResponse>(response);
  }
};



