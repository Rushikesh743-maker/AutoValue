import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  ChevronDown,
  ChevronUp,
  Car,
  Bookmark,
  Check,
  Compass,
  Gauge,
  ShieldCheck,
  AlertTriangle,
  Calculator,
  SlidersHorizontal,
  Sliders,
  Search,
  Sparkles,
  X,
  ArrowLeft,
  HelpCircle
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import { api } from '../services/api';
import type {
  DecisionIntelligenceResponse,
  ValuationRequest,
  ScenarioResponse,
  AlternativeVehicleItem,
  RiskFactor,
  TCOResponse,
  TCOAssumptions,
  ForecastResponse,
  LifecycleDecision
} from '../services/api';
import { LifecycleDecisionCard } from '../components/LifecycleDecisionCard';
import { useAuth } from '../context/AuthContext';

export const IntelligencePage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  // State from location or default vehicle input
  const initialVehicle: ValuationRequest = location.state?.vehicle || {
    brand: 'Hyundai',
    model: 'Creta',
    variant: '1.5 CRDi SX',
    year: 2021,
    km_driven: 38000,
    fuel_type: 'Diesel',
    transmission: 'Manual',
    city: 'Mumbai',
    asking_price: 1320000
  };

  const [vehicle] = useState<ValuationRequest>(initialVehicle);
  const [intelligence, setIntelligence] = useState<DecisionIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // TCO & Resale Intelligence state
  const [tcoData, setTcoData] = useState<TCOResponse | null>(null);
  const [tcoHorizon, setTcoHorizon] = useState<number>(5);
  const [tcoAnnualKm, setTcoAnnualKm] = useState<number>(12000);
  const [tcoFuelPrice, setTcoFuelPrice] = useState<number | ''>('');
  const [tcoEfficiency, setTcoEfficiency] = useState<number | ''>('');
  const [tcoMaintenance, setTcoMaintenance] = useState<number | ''>('');
  const [tcoPurchaseMode, setTcoPurchaseMode] = useState<'FAIR_VALUE' | 'ASKING_PRICE' | 'CUSTOM'>('FAIR_VALUE');
  const [tcoCustomPrice, setTcoCustomPrice] = useState<number | ''>('');
  const [tcoScenario, setTcoScenario] = useState<'BASE' | 'CONSERVATIVE' | 'OPTIMISTIC'>('BASE');
  const [tcoLoading, setTcoLoading] = useState<boolean>(false);
  const [showTCOAssumptions, setShowTCOAssumptions] = useState<boolean>(false);

  // Market Forecasting & Buy/Sell Timing state
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [forecastHorizon, setForecastHorizon] = useState<number>(365);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);
  const [showBuyFactors, setShowBuyFactors] = useState<boolean>(true);
  const [showSellFactors, setShowSellFactors] = useState<boolean>(true);
  const [showEvidenceAudit, setShowEvidenceAudit] = useState<boolean>(false);

  // Vehicle Lifecycle Decision Intelligence state
  const [lifecycleData, setLifecycleData] = useState<LifecycleDecision | null>(null);
  const [lifecycleLoading, setLifecycleLoading] = useState<boolean>(false);
  const [lifecycleSimulating, setLifecycleSimulating] = useState<boolean>(false);

  // Scenario Simulator state
  const [scenarioKm, setScenarioKm] = useState<number>(initialVehicle.km_driven || 40000);
  const [scenarioYear, setScenarioYear] = useState<number>(initialVehicle.year);
  const [scenarioCity, setScenarioCity] = useState<string>(initialVehicle.city || 'Mumbai');
  const [scenarioFuel, setScenarioFuel] = useState<string>(initialVehicle.fuel_type || 'Diesel');
  const [scenarioResult, setScenarioResult] = useState<ScenarioResponse | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);

  // Alternative discovery state
  const [altBudget, setAltBudget] = useState<number>(initialVehicle.asking_price || 1200000);
  const [alternatives, setAlternatives] = useState<AlternativeVehicleItem[]>([]);
  const [loadingAlts, setLoadingAlts] = useState<boolean>(false);

  // Watchlist state
  const [isSaved, setIsSaved] = useState<boolean>(false);
  const [savingWatchlist, setSavingWatchlist] = useState<boolean>(false);

  // Modal / Tab states
  const [showFormulaModal, setShowFormulaModal] = useState<boolean>(false);
  const [selectedRiskFactor, setSelectedRiskFactor] = useState<RiskFactor | null>(null);

  // Fetch complete intelligence packet
  useEffect(() => {
    fetchIntelligence(vehicle);
  }, []);

  const fetchIntelligence = async (req: ValuationRequest) => {
    setLoading(true);
    setLifecycleLoading(true);
    setError(null);
    try {
      const data = await api.getIntelligence(req);
      setIntelligence(data);
      if (data.tco) {
        setTcoData(data.tco as unknown as TCOResponse);
      }
      if (data.forecast) {
        setForecastData(data.forecast as unknown as ForecastResponse);
      } else {
        try {
          const fc = await api.getMarketForecast(req, forecastHorizon);
          setForecastData(fc);
        } catch {
          // Ignored
        }
      }

      // Fetch Lifecycle Decision
      try {
        const lc = await api.postLifecycleDecision({
          brand: req.brand,
          model: req.model,
          variant: req.variant,
          year: req.year,
          fuel_type: req.fuel_type,
          transmission: req.transmission,
          km_driven: req.km_driven,
          city: req.city,
          asking_price: req.asking_price
        });
        setLifecycleData(lc);
      } catch (lcErr) {
        console.error('Lifecycle decision error:', lcErr);
      }

      // Auto-load alternatives near asking price or estimated value
      const targetBgt = req.asking_price || data.valuation.estimated_value;
      setAltBudget(targetBgt);
      loadAlternatives(targetBgt, req.fuel_type);
    } catch (err: any) {
      setError(err.message || 'Failed to compute vehicle intelligence.');
    } finally {
      setLoading(false);
      setLifecycleLoading(false);
    }
  };

  const handleLifecycleSimulate = async (annualKm?: number, priceOverride?: number, marketShift?: number) => {
    if (!lifecycleData) return;
    setLifecycleSimulating(true);
    try {
      const res = await api.simulateLifecycleScenario({
        base_request: {
          brand: vehicle.brand,
          model: vehicle.model,
          variant: vehicle.variant,
          year: vehicle.year,
          fuel_type: vehicle.fuel_type,
          transmission: vehicle.transmission,
          km_driven: vehicle.km_driven,
          city: vehicle.city,
          asking_price: vehicle.asking_price
        },
        annual_km_override: annualKm,
        purchase_price_override: priceOverride,
        market_shift_pct: marketShift
      });
      setLifecycleData(res);
    } catch (err: any) {
      console.error('Lifecycle simulation error:', err);
    } finally {
      setLifecycleSimulating(false);
    }
  };

  const handleForecastHorizonChange = async (days: number) => {
    setForecastHorizon(days);
    setForecastLoading(true);
    try {
      const res = await api.getMarketForecast(vehicle, days);
      setForecastData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setForecastLoading(false);
    }
  };

  const handleRecalculateTCO = async (overrideHorizon?: number) => {
    setTcoLoading(true);
    try {
      const horizon = overrideHorizon !== undefined ? overrideHorizon : tcoHorizon;
      const assumptions: TCOAssumptions = {
        ownership_years: horizon,
        annual_km: tcoAnnualKm,
        purchase_price_mode: tcoPurchaseMode,
      };
      if (tcoFuelPrice !== '') assumptions.fuel_price = Number(tcoFuelPrice);
      if (tcoEfficiency !== '') assumptions.fuel_efficiency = Number(tcoEfficiency);
      if (tcoMaintenance !== '') assumptions.annual_maintenance = Number(tcoMaintenance);
      if (tcoPurchaseMode === 'CUSTOM' && tcoCustomPrice !== '') {
        assumptions.custom_purchase_price = Number(tcoCustomPrice);
      }

      const res = await api.getTCOAnalysis(vehicle, assumptions);
      setTcoData(res);
      if (overrideHorizon !== undefined) {
        setTcoHorizon(overrideHorizon);
      }
    } catch (err: any) {
      console.error('TCO calculation error:', err);
    } finally {
      setTcoLoading(false);
    }
  };

  const runScenarioSimulation = async () => {
    if (!intelligence) return;
    setSimulating(true);
    try {
      const res = await api.simulateScenario(vehicle, {
        km_driven: scenarioKm,
        year: scenarioYear,
        city: scenarioCity,
        fuel_type: scenarioFuel
      });
      setScenarioResult(res);
    } catch (err: any) {
      console.error('Simulation error:', err);
    } finally {
      setSimulating(false);
    }
  };

  const loadAlternatives = async (budget: number, fuel?: string) => {
    setLoadingAlts(true);
    try {
      const res = await api.getAlternatives({
        target_budget: budget,
        fuel_type: fuel,
        limit: 4
      });
      setAlternatives(res.results);
    } catch (err: any) {
      console.error('Alternatives error:', err);
    } finally {
      setLoadingAlts(false);
    }
  };

  const handleSaveToWatchlist = async () => {
    if (!user) {
      navigate('/login', { state: { from: '/intelligence' } });
      return;
    }
    setSavingWatchlist(true);
    try {
      await api.saveVehicle({
        brand: vehicle.brand,
        model: vehicle.model,
        variant: vehicle.variant,
        year: vehicle.year,
        fuel_type: vehicle.fuel_type,
        transmission: vehicle.transmission,
        km_driven: vehicle.km_driven || 0,
        city: vehicle.city || 'National',
        notes: `Tracked via Intelligence Terminal (Est: ₹${intelligence?.valuation.estimated_value.toLocaleString('en-IN')})`
      });
      setIsSaved(true);
    } catch (err: any) {
      console.error('Watchlist save error:', err);
    } finally {
      setSavingWatchlist(false);
    }
  };

  const formatLakhs = (val?: number | null) => {
    if (val === undefined || val === null || isNaN(val)) return '—';
    if (Math.abs(val) >= 10000000) {
      return `₹ ${(val / 10000000).toFixed(2)} Cr`;
    }
    const lakhs = val / 100000;
    return `₹ ${lakhs.toFixed(2)} Lakh`;
  };

  // Color helper for Deal Classification badge
  const getDealBadgeStyle = (classification: string) => {
    switch (classification) {
      case 'SIGNIFICANTLY_BELOW_MARKET':
        return 'badge-positive';
      case 'BELOW_MARKET':
        return 'badge-positive';
      case 'FAIRLY_PRICED':
        return 'badge-info';
      case 'ABOVE_MARKET':
        return 'badge-warning';
      case 'SIGNIFICANTLY_ABOVE_MARKET':
        return 'badge-danger';
      default:
        return 'badge-neutral';
    }
  };

  const getRiskBadgeStyle = (level: string) => {
    switch (level) {
      case 'VERY_LOW':
      case 'LOW':
        return 'badge-positive';
      case 'MODERATE':
        return 'badge-warning';
      case 'HIGH':
      case 'VERY_HIGH':
        return 'badge-danger';
      default:
        return 'badge-neutral';
    }
  };

  const getTrendBadgeStyle = (direction: string) => {
    switch (direction) {
      case 'RISING':
        return 'badge-positive';
      case 'DECLINING':
        return 'badge-danger';
      case 'STABLE':
        return 'badge-info';
      default:
        return 'badge-neutral';
    }
  };

  const getTimingBadgeStyle = (signal: string) => {
    switch (signal) {
      case 'FAVORABLE':
        return 'badge-positive';
      case 'NEUTRAL':
        return 'badge-info';
      case 'UNFAVORABLE':
        return 'badge-warning';
      default:
        return 'badge-neutral';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-surface-border gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-mono font-medium uppercase tracking-wider text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20">
              Terminal Analytics
            </span>
            <span className="text-xs text-slate-500">AutoValue Decision Intelligence</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-slate-100 tracking-tight">
            Automotive Decision Intelligence
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Evidence-grounded deal evaluation, counterfactual simulation, negotiation corridors, and multi-factor scoring.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => navigate('/valuation')}
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> New Valuation
          </button>
          <button
            onClick={handleSaveToWatchlist}
            disabled={isSaved || savingWatchlist}
            className={`text-xs px-3.5 py-2 rounded-lg font-medium transition flex items-center gap-1.5 ${
              isSaved
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 cursor-default'
                : 'btn-primary'
            }`}
          >
            {isSaved ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" /> Saved to Watchlist
              </>
            ) : savingWatchlist ? (
              'Saving...'
            ) : (
              <>
                <Bookmark className="w-3.5 h-3.5" /> Save Vehicle
              </>
            )}
          </button>
        </div>
      </div>

      {/* Garage Portfolio Entry Point */}
      <div className="card-surface p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-l-2 border-l-brand-500">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-surface-canvas border border-surface-border flex items-center justify-center text-brand-400 shrink-0">
            <Car className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                Garage Portfolio Intelligence
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-border text-slate-400">
                Multi-Asset
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Analyze your full garage holdings, multi-vehicle TCO, sell-first rankings, and consolidation scenarios.
            </p>
          </div>
        </div>
        <button
          onClick={() => navigate('/garage')}
          className="btn-secondary text-xs whitespace-nowrap self-start sm:self-auto"
        >
          Open Garage Terminal →
        </button>
      </div>

      {loading ? (
        <div className="py-24 text-center card-surface">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-2 border-brand-500 border-t-transparent mb-4"></div>
          <h3 className="text-base font-semibold text-slate-200">Synthesizing Decision Intelligence</h3>
          <p className="text-xs text-slate-400 mt-1">
            Running XGBoost inference, comparable distance ranking, and conformal calibration...
          </p>
        </div>
      ) : error || !intelligence ? (
        <div className="py-12 text-center max-w-lg mx-auto card-surface p-8 border-rose-500/30">
          <div className="w-10 h-10 rounded-full bg-rose-500/15 text-rose-400 flex items-center justify-center mx-auto mb-3">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <h3 className="text-base font-semibold text-slate-100">Intelligence Synthesis Failed</h3>
          <p className="text-xs text-slate-400 mt-2">{error}</p>
          <button
            onClick={() => fetchIntelligence(vehicle)}
            className="mt-5 btn-secondary text-xs"
          >
            Retry Computation
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Unified Vehicle Lifecycle Decision Intelligence */}
          <LifecycleDecisionCard
            decision={lifecycleData}
            loading={lifecycleLoading}
            onSimulateScenario={handleLifecycleSimulate}
            simulating={lifecycleSimulating}
          />

          {/* Top Row: Snapshot, Primary Fair Value & Deal Assessment */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* 1. Vehicle Snapshot */}
            <div className="card-surface p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                    Vehicle Profile
                  </span>
                  <span className="text-[11px] font-mono text-slate-400 bg-surface-canvas px-2 py-0.5 rounded border border-surface-border">
                    {intelligence.vehicle.city || 'India'}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-slate-100">
                  {intelligence.vehicle.year} {intelligence.vehicle.brand} {intelligence.vehicle.model}
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">{intelligence.vehicle.variant || 'Standard Variant'}</p>

                <div className="grid grid-cols-2 gap-2.5 mt-5 text-xs">
                  <div className="bg-surface-canvas/60 p-2.5 rounded border border-surface-border">
                    <span className="text-[10px] text-slate-500 block uppercase">Odometer</span>
                    <span className="font-semibold text-slate-200 num-tabular">
                      {intelligence.vehicle.km_driven?.toLocaleString('en-IN')} km
                    </span>
                  </div>
                  <div className="bg-surface-canvas/60 p-2.5 rounded border border-surface-border">
                    <span className="text-[10px] text-slate-500 block uppercase">Powertrain</span>
                    <span className="font-semibold text-slate-200">
                      {intelligence.vehicle.fuel_type} • {intelligence.vehicle.transmission}
                    </span>
                  </div>
                </div>
              </div>

              {intelligence.deal_analysis.asking_price && (
                <div className="mt-5 pt-3 border-t border-surface-border flex justify-between items-center text-xs">
                  <span className="text-slate-400">Advertised Asking Price:</span>
                  <span className="font-bold text-slate-200 num-tabular">
                    ₹{intelligence.deal_analysis.asking_price.toLocaleString('en-IN')}
                  </span>
                </div>
              )}
            </div>

            {/* 2. Estimated Value & Conformal Range */}
            <div className="card-surface p-5 flex flex-col justify-between relative">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-brand-400">
                    Statistical Fair Value
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">v002 Model</span>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight num-tabular">
                  ₹{intelligence.valuation.estimated_value.toLocaleString('en-IN')}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Point prediction from calibrated gradient boosted regressor.
                </p>

                {intelligence.valuation.model_interval && (
                  <div className="mt-4 bg-surface-canvas/60 p-3 rounded border border-surface-border">
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>Conformal Uncertainty (80% Confidence)</span>
                      <span className="text-brand-400 font-mono num-tabular">
                        ±{Math.round(((intelligence.valuation.model_interval.interval_high - intelligence.valuation.model_interval.interval_low) / (2 * intelligence.valuation.estimated_value)) * 100)}%
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-slate-200 num-tabular">
                      {intelligence.valuation.model_interval.interval_low_formatted} – {intelligence.valuation.model_interval.interval_high_formatted}
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-surface-border flex items-center justify-between text-xs text-slate-500">
                <span>Observed Market Median:</span>
                <span className="font-medium text-slate-300 num-tabular">
                  {intelligence.market_statistics.median
                    ? `₹${intelligence.market_statistics.median.toLocaleString('en-IN')}`
                    : 'Sparse Segment'}
                </span>
              </div>
            </div>

            {/* 3. Deal Analysis Card */}
            <div className="card-surface p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                    Deal Assessment
                  </span>
                  <span className={getDealBadgeStyle(intelligence.deal_analysis.classification)}>
                    {intelligence.deal_analysis.classification.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="mt-2">
                  <div className="text-xl font-bold text-slate-100 num-tabular">
                    {intelligence.deal_analysis.percentage_difference_from_ml !== null && intelligence.deal_analysis.percentage_difference_from_ml !== undefined ? (
                      <span>
                        {intelligence.deal_analysis.percentage_difference_from_ml > 0 ? '+' : ''}
                        {intelligence.deal_analysis.percentage_difference_from_ml.toFixed(1)}%
                      </span>
                    ) : (
                      'N/A'
                    )}
                    <span className="text-xs font-normal text-slate-400 ml-2">vs Model Fair Value</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                    {intelligence.deal_analysis.explanation}
                  </p>
                </div>
              </div>

              <div className="mt-4 bg-surface-canvas/60 p-2.5 rounded border border-surface-border text-xs flex justify-between items-center">
                <span className="text-slate-400">Evidence Depth:</span>
                <span className="font-semibold text-brand-400 num-tabular">
                  {intelligence.deal_analysis.evidence_strength} ({intelligence.market_statistics.comparable_count} Listings)
                </span>
              </div>
            </div>
          </div>

          {/* Row 2: Negotiation Intelligence & Value Score */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Negotiation Intelligence */}
            <div className="card-surface p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                <div className="flex items-center gap-2">
                  <Compass className="w-4 h-4 text-brand-400" />
                  <h3 className="text-sm font-semibold text-slate-100">
                    Negotiation Corridor & Strategy
                  </h3>
                </div>
                <span className="badge-info text-[10px]">
                  {intelligence.negotiation.buyer_leverage.replace(/_/g, ' ')}
                </span>
              </div>

              <p className="text-xs text-slate-400">
                Evidence-supported targets calculated from central market quartiles and model prediction intervals.
              </p>

              {/* 3 Targets Corridor */}
              <div className="grid grid-cols-3 gap-2.5">
                <div className="bg-surface-canvas/60 p-3 rounded border border-surface-border text-center">
                  <span className="text-[10px] font-mono text-emerald-400 block uppercase">
                    Aggressive Offer
                  </span>
                  <span className="text-sm sm:text-base font-bold text-white mt-1 block num-tabular">
                    ₹{intelligence.negotiation.aggressive_target.toLocaleString('en-IN')}
                  </span>
                  <span className="text-[10px] text-slate-500 mt-0.5 block">P25 Anchor</span>
                </div>

                <div className="bg-surface-canvas/80 p-3 rounded border border-brand-500/40 text-center relative">
                  <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-brand-500 text-[9px] font-bold text-white px-1.5 py-0.2 rounded">
                    FAIR
                  </div>
                  <span className="text-[10px] font-mono text-brand-400 block uppercase">
                    Evidence Target
                  </span>
                  <span className="text-sm sm:text-base font-bold text-white mt-1 block num-tabular">
                    ₹{intelligence.negotiation.evidence_supported_target.toLocaleString('en-IN')}
                  </span>
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Model Median</span>
                </div>

                <div className="bg-surface-canvas/60 p-3 rounded border border-surface-border text-center">
                  <span className="text-[10px] font-mono text-amber-400 block uppercase">
                    Conservative Cap
                  </span>
                  <span className="text-sm sm:text-base font-bold text-white mt-1 block num-tabular">
                    ₹{intelligence.negotiation.conservative_target.toLocaleString('en-IN')}
                  </span>
                  <span className="text-[10px] text-slate-500 mt-0.5 block">P75 Bound</span>
                </div>
              </div>

              {/* Talking Points */}
              <div className="space-y-2 pt-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                  Evidence-Backed Talking Points
                </span>
                {intelligence.negotiation.talking_points.map((tp, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-slate-300 bg-surface-canvas/40 p-2.5 rounded border border-surface-border">
                    <span className="text-brand-400 font-bold">•</span>
                    <span>{tp}</span>
                  </div>
                ))}
              </div>

              <p className="text-[11px] text-slate-500 italic pt-2 border-t border-surface-border">
                {intelligence.negotiation.disclaimer}
              </p>
            </div>

            {/* Value-for-Money Score */}
            <div className="card-surface p-5 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                  <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-teal-400" />
                    <h3 className="text-sm font-semibold text-slate-100">
                      Value-for-Money Score
                    </h3>
                  </div>
                  <button
                    onClick={() => setShowFormulaModal(true)}
                    className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 font-medium"
                  >
                    <HelpCircle className="w-3.5 h-3.5" /> Methodology
                  </button>
                </div>

                <div className="flex items-center gap-5 my-4 bg-surface-canvas/60 p-4 rounded border border-surface-border">
                  <div className="w-16 h-16 rounded-full border-2 border-teal-500/40 bg-teal-500/10 flex flex-col items-center justify-center shrink-0">
                    <span className="text-xl font-bold text-teal-300 num-tabular">
                      {intelligence.value_score.overall_value_score}
                    </span>
                    <span className="text-[9px] text-slate-500 font-mono">/ 100</span>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-teal-400 tracking-wider uppercase">
                      {intelligence.value_score.rating_label.replace(/_/g, ' ')}
                    </span>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                      Multi-attribute rating combining price advantage, mileage intensity, and market density.
                    </p>
                  </div>
                </div>

                {/* Sub-Score Bars */}
                <div className="space-y-3 mt-4">
                  {intelligence.value_score.price_value_score !== null && (
                    <div>
                      <div className="flex justify-between text-xs text-slate-300 mb-1">
                        <span>Price Competitiveness (40%)</span>
                        <span className="font-semibold text-brand-400 num-tabular">
                          {intelligence.value_score.price_value_score}/100
                        </span>
                      </div>
                      <div className="w-full bg-surface-canvas h-1.5 rounded overflow-hidden border border-surface-border">
                        <div
                          className="bg-brand-500 h-full rounded transition-all"
                          style={{ width: `${intelligence.value_score.price_value_score}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Usage & Mileage Advantage (25%)</span>
                      <span className="font-semibold text-teal-400 num-tabular">
                        {intelligence.value_score.mileage_value_score}/100
                      </span>
                    </div>
                    <div className="w-full bg-surface-canvas h-1.5 rounded overflow-hidden border border-surface-border">
                      <div
                        className="bg-teal-500 h-full rounded transition-all"
                        style={{ width: `${intelligence.value_score.mileage_value_score}%` }}
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Vehicle Lifecycle & Age (15%)</span>
                      <span className="font-semibold text-indigo-400 num-tabular">
                        {intelligence.value_score.age_value_score}/100
                      </span>
                    </div>
                    <div className="w-full bg-surface-canvas h-1.5 rounded overflow-hidden border border-surface-border">
                      <div
                        className="bg-indigo-500 h-full rounded transition-all"
                        style={{ width: `${intelligence.value_score.age_value_score}%` }}
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Marketplace Evidence Density (20%)</span>
                      <span className="font-semibold text-purple-400 num-tabular">
                        {intelligence.value_score.market_support_score}/100
                      </span>
                    </div>
                    <div className="w-full bg-surface-canvas h-1.5 rounded overflow-hidden border border-surface-border">
                      <div
                        className="bg-purple-500 h-full rounded transition-all"
                        style={{ width: `${intelligence.value_score.market_support_score}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-[11px] text-slate-500 italic pt-2 border-t border-surface-border">
                {intelligence.value_score.disclaimer}
              </p>
            </div>
          </div>

          {/* Row 3: Vehicle Risk & Trust Intelligence */}
          {intelligence.risk && (
            <div className="card-surface p-5 space-y-5">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                      Evidence Risk Engine
                    </span>
                    <span className="badge-info text-[10px]">
                      Observable Signals
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-brand-400" />
                    Market & Evidence Risk Intelligence
                  </h3>
                </div>

                <div className="flex items-center gap-2.5">
                  <div className="bg-surface-canvas/60 px-3 py-1 rounded border border-surface-border text-right text-xs">
                    <span className="text-[10px] text-slate-400 block uppercase">Confidence</span>
                    <span className="font-bold text-brand-400">{intelligence.risk.confidence}</span>
                  </div>
                  <span className={getRiskBadgeStyle(intelligence.risk.risk_level)}>
                    {intelligence.risk.risk_level.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>

              {/* Risk Score & Signals Overview */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Score Dial */}
                <div className="bg-surface-canvas/60 p-4 rounded border border-surface-border flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full border-2 border-surface-border bg-surface-canvas flex flex-col items-center justify-center shrink-0">
                    <span className={`text-xl font-bold num-tabular ${
                      intelligence.risk.risk_score <= 39 ? 'text-emerald-400' :
                      intelligence.risk.risk_score <= 59 ? 'text-amber-400' : 'text-rose-400'
                    }`}>
                      {intelligence.risk.risk_score}
                    </span>
                    <span className="text-[9px] text-slate-500 font-mono">/ 100</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 block uppercase">
                      Observable Risk Index
                    </span>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                      {intelligence.risk.summary}
                    </p>
                  </div>
                </div>

                {/* Positive Signals Card */}
                <div className="bg-surface-canvas/60 p-4 rounded border border-surface-border">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 flex items-center gap-1.5 mb-2">
                    <Check className="w-3.5 h-3.5" /> Positive Indicators
                  </span>
                  <ul className="space-y-1.5">
                    {intelligence.risk.positive_signals.map((sig, idx) => (
                      <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                        <span className="text-emerald-400 font-bold shrink-0">•</span>
                        <span>{sig}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Risk Signals Card */}
                <div className="bg-surface-canvas/60 p-4 rounded border border-surface-border">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 flex items-center gap-1.5 mb-2">
                    <AlertTriangle className="w-3.5 h-3.5" /> Observable Caveats
                  </span>
                  <ul className="space-y-1.5">
                    {intelligence.risk.risk_signals.map((sig, idx) => (
                      <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                        <span className="text-amber-400 font-bold shrink-0">•</span>
                        <span>{sig}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Segmented Risk Meter */}
              <div className="bg-surface-canvas/40 p-4 rounded border border-surface-border">
                <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1.5">
                  <span className="text-emerald-400">VERY LOW (0–19)</span>
                  <span className="text-teal-400">LOW (20–39)</span>
                  <span className="text-amber-400">MODERATE (40–59)</span>
                  <span className="text-orange-400">HIGH (60–79)</span>
                  <span className="text-rose-400">VERY HIGH (80–100)</span>
                </div>
                <div className="w-full bg-surface-canvas h-2.5 rounded overflow-hidden flex p-0.5 gap-0.5 border border-surface-border">
                  <div className="bg-emerald-500/50 h-full w-[20%] rounded-l"></div>
                  <div className="bg-teal-500/50 h-full w-[20%]"></div>
                  <div className="bg-amber-500/50 h-full w-[20%]"></div>
                  <div className="bg-orange-500/50 h-full w-[20%]"></div>
                  <div className="bg-rose-500/50 h-full w-[20%] rounded-r"></div>
                </div>
                <div className="relative mt-1">
                  <div
                    className="absolute transform -translate-x-1/2 flex flex-col items-center"
                    style={{ left: `${Math.min(98, Math.max(2, intelligence.risk.risk_score))}%` }}
                  >
                    <span className="text-[11px] font-mono font-bold text-slate-200 bg-surface-canvas px-1.5 py-0.2 rounded border border-surface-border num-tabular">
                      ▲ {intelligence.risk.risk_score}
                    </span>
                  </div>
                </div>
                <div className="h-4"></div>
              </div>

              {/* 9 Risk Factors Grid */}
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                    Evaluated Risk Dimensions (Select to inspect mathematical evidence)
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">9 Dimensions • 100% Weight</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                  {intelligence.risk.factors.map((f) => (
                    <div
                      key={f.key}
                      onClick={() => setSelectedRiskFactor(f)}
                      className="bg-surface-canvas/60 hover:bg-surface-canvas p-3 rounded border border-surface-border hover:border-slate-700 cursor-pointer transition flex flex-col justify-between group"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-semibold text-xs text-slate-200 group-hover:text-brand-300 transition">
                            {f.name}
                          </span>
                          <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold border ${getRiskBadgeStyle(f.severity)}`}>
                            {f.severity.replace(/_/g, ' ')}
                          </span>
                        </div>

                        <div className="flex items-baseline justify-between mt-2">
                          <span className="text-base font-bold text-white num-tabular">
                            {f.score}<span className="text-xs text-slate-500">/100</span>
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono num-tabular">
                            {f.weighted_contribution !== undefined && f.weighted_contribution !== null
                              ? f.weighted_contribution.toFixed(1)
                              : f.weight !== undefined && f.score !== undefined
                              ? (f.score * f.weight).toFixed(1)
                              : '0.0'}{' '}
                            pts ({f.weight !== undefined ? (f.weight * 100).toFixed(0) : '0'}%)
                          </span>
                        </div>
                      </div>

                      <div className="mt-2 pt-2 border-t border-surface-border flex items-center justify-between text-[11px]">
                        <span className="text-slate-500 truncate max-w-[180px]">{f.interpretation}</span>
                        <span className="text-brand-400 group-hover:underline text-[10px] font-medium shrink-0 ml-2">Evidence ⓘ</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommendation Box */}
              <div className="bg-surface-canvas/80 p-3.5 rounded border border-brand-500/20 text-xs">
                <span className="font-semibold text-brand-400 uppercase tracking-wider block mb-1 text-[11px]">
                  Next Step Recommendation
                </span>
                <p className="text-slate-300 leading-relaxed">{intelligence.risk.recommendation}</p>
              </div>

              <p className="text-[11px] text-slate-500 italic pt-2 border-t border-surface-border">
                {intelligence.risk.disclaimer}
              </p>
            </div>
          )}

          {/* Row 4: Total Cost of Ownership & Resale Intelligence */}
          {tcoData && (
            <div className="card-surface p-5 sm:p-6 space-y-5">
              {/* Section Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-surface-border">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                      Ownership Economics
                    </span>
                    <span className="badge-info text-[10px]">
                      Multi-Year TCO
                    </span>
                  </div>
                  <h3 className="text-base sm:text-lg font-semibold text-slate-100 flex items-center gap-2">
                    <Calculator className="w-4 h-4 text-teal-400" />
                    Total Cost of Ownership & Resale Projection
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Depreciation curves, fuel and maintenance modeling, and empirical resale uncertainty corridors.
                  </p>
                </div>

                {/* Horizon Quick Buttons */}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-slate-400 font-medium mr-1">Horizon:</span>
                  {[1, 3, 5, 7, 10].map((yr) => (
                    <button
                      key={yr}
                      onClick={() => handleRecalculateTCO(yr)}
                      disabled={tcoLoading}
                      className={`px-2.5 py-1 rounded text-xs font-mono font-semibold transition border ${
                        tcoHorizon === yr
                          ? 'bg-brand-600 text-white border-brand-500'
                          : 'bg-surface-canvas text-slate-400 border-surface-border hover:text-slate-200'
                      }`}
                    >
                      {yr}Y
                    </button>
                  ))}
                  <button
                    onClick={() => setShowTCOAssumptions(!showTCOAssumptions)}
                    className="ml-2 btn-secondary text-xs flex items-center gap-1.5 py-1 px-2.5"
                  >
                    <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
                    <span>{showTCOAssumptions ? 'Hide Parameters' : 'Adjust Assumptions'}</span>
                  </button>
                </div>
              </div>

              {/* Interactive Assumptions Editor (Collapsible Drawer) */}
              {showTCOAssumptions && (
                <div className="bg-surface-canvas/80 p-4 rounded border border-surface-border space-y-4">
                  <div className="flex justify-between items-center pb-2 border-b border-surface-border">
                    <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider">
                      Underlying Ownership Assumptions
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Transparent defaults with verified dataset provenance
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                    <div>
                      <label className="text-slate-400 block mb-1 font-medium">Purchase Price Mode</label>
                      <select
                        value={tcoPurchaseMode}
                        onChange={(e) => setTcoPurchaseMode(e.target.value as any)}
                        className="input-field text-xs py-1.5"
                      >
                        <option value="FAIR_VALUE">AutoValue Fair Value (₹{intelligence.valuation.estimated_value.toLocaleString('en-IN')})</option>
                        {intelligence.deal_analysis.asking_price && (
                          <option value="ASKING_PRICE">Seller Asking Price (₹{intelligence.deal_analysis.asking_price.toLocaleString('en-IN')})</option>
                        )}
                        <option value="CUSTOM">Custom Negotiated Price</option>
                      </select>
                    </div>

                    {tcoPurchaseMode === 'CUSTOM' && (
                      <div>
                        <label className="text-slate-400 block mb-1 font-medium">Negotiated Price (₹)</label>
                        <input
                          type="number"
                          step="10000"
                          placeholder={String(intelligence.valuation.estimated_value)}
                          value={tcoCustomPrice}
                          onChange={(e) => setTcoCustomPrice(e.target.value === '' ? '' : Number(e.target.value))}
                          className="input-field text-xs py-1.5"
                        />
                      </div>
                    )}

                    <div>
                      <label className="text-slate-400 block mb-1 font-medium">Annual Usage (km/year)</label>
                      <input
                        type="number"
                        step="1000"
                        value={tcoAnnualKm}
                        onChange={(e) => setTcoAnnualKm(Number(e.target.value))}
                        className="input-field text-xs py-1.5"
                      />
                    </div>

                    <div>
                      <label className="text-slate-400 block mb-1 font-medium">
                        {vehicle.fuel_type?.toLowerCase() === 'electric' ? 'Electricity (₹/kWh)' : 'Fuel Price (₹/L)'}
                      </label>
                      <input
                        type="number"
                        step="0.5"
                        placeholder={String(tcoData.assumptions.fuel_price)}
                        value={tcoFuelPrice}
                        onChange={(e) => setTcoFuelPrice(e.target.value === '' ? '' : Number(e.target.value))}
                        className="input-field text-xs py-1.5"
                      />
                    </div>

                    <div>
                      <label className="text-slate-400 block mb-1 font-medium">
                        {vehicle.fuel_type?.toLowerCase() === 'electric' ? 'Efficiency (kWh/100km)' : 'Efficiency (km/L)'}
                      </label>
                      <input
                        type="number"
                        step="0.5"
                        placeholder={String(tcoData.assumptions.fuel_efficiency)}
                        value={tcoEfficiency}
                        onChange={(e) => setTcoEfficiency(e.target.value === '' ? '' : Number(e.target.value))}
                        className="input-field text-xs py-1.5"
                      />
                    </div>

                    <div>
                      <label className="text-slate-400 block mb-1 font-medium">Annual Maintenance (₹/yr)</label>
                      <input
                        type="number"
                        step="2000"
                        placeholder={String(tcoData.assumptions.annual_maintenance)}
                        value={tcoMaintenance}
                        onChange={(e) => setTcoMaintenance(e.target.value === '' ? '' : Number(e.target.value))}
                        className="input-field text-xs py-1.5"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      onClick={() => handleRecalculateTCO()}
                      disabled={tcoLoading}
                      className="btn-primary text-xs"
                    >
                      {tcoLoading ? 'Recomputing Economics...' : 'Apply & Recalculate TCO'}
                    </button>
                  </div>
                </div>
              )}

              {/* Scenario Toggle Tabs */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-canvas/60 p-2 rounded border border-surface-border">
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="text-slate-400 font-semibold px-2">Scenario:</span>
                  {(['BASE', 'CONSERVATIVE', 'OPTIMISTIC'] as const).map((scKey) => (
                    <button
                      key={scKey}
                      onClick={() => setTcoScenario(scKey)}
                      className={`px-3 py-1 rounded text-xs font-medium transition ${
                        tcoScenario === scKey
                          ? scKey === 'CONSERVATIVE'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : scKey === 'OPTIMISTIC'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : 'bg-brand-500/20 text-brand-300 border border-brand-500/40'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {scKey === 'BASE' ? 'Base Assumptions' : scKey === 'CONSERVATIVE' ? 'Conservative' : 'Optimistic'}
                    </button>
                  ))}
                </div>

                <div className="text-[11px] text-slate-500 italic pr-2 font-mono">
                  {tcoScenario === 'BASE' && 'Central assumptions & historical market trend'}
                  {tcoScenario === 'CONSERVATIVE' && '+10% Fuel, +25% Maint, -8% Resale'}
                  {tcoScenario === 'OPTIMISTIC' && '-8% Fuel, -15% Maint, +6% Resale'}
                </div>
              </div>

              {/* Economic Summary Cards */}
              {(() => {
                const activeSc = tcoScenario === 'BASE'
                  ? null
                  : (tcoData.scenarios ? tcoData.scenarios[tcoScenario] : null);

                const displayNetTco = activeSc?.net_tco_formatted || (activeSc?.net_tco !== undefined ? formatLakhs(activeSc.net_tco) : tcoData.ownership?.net_tco_formatted || formatLakhs(tcoData.ownership?.net_tco));
                const displayAnnual = activeSc?.annual_cost_formatted || (activeSc?.annual_cost !== undefined ? formatLakhs(activeSc.annual_cost) : tcoData.ownership?.annual_cost_formatted || formatLakhs(tcoData.ownership?.annual_cost));
                const displayCostKm = activeSc?.cost_per_km !== undefined ? activeSc.cost_per_km.toFixed(2) : (tcoData.ownership?.cost_per_km !== undefined ? tcoData.ownership.cost_per_km.toFixed(2) : '0.00');
                const displayResale = activeSc?.estimated_resale_formatted || (activeSc?.estimated_resale !== undefined ? formatLakhs(activeSc.estimated_resale) : tcoData.resale?.estimated_resale_formatted || formatLakhs(tcoData.resale?.estimated_resale_value));

                return (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* 1. Net TCO Hero Card */}
                    <div className="bg-surface-canvas/80 p-5 rounded border-l-2 border-l-brand-500 border-t border-r border-b border-surface-border flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-brand-400">
                            {tcoHorizon}-Year Net Cost
                          </span>
                          <span className="text-[10px] font-mono text-slate-400 bg-surface-canvas px-1.5 py-0.2 rounded border border-surface-border">
                            Net TCO
                          </span>
                        </div>
                        <div className="text-2xl sm:text-3xl font-bold text-white tracking-tight num-tabular">
                          {displayNetTco}
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          True economic cost after future resale realization.
                        </p>
                      </div>

                      <div className="mt-5 pt-3 border-t border-surface-border grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-surface-canvas p-2 rounded border border-surface-border">
                          <span className="text-slate-500 block text-[9px] uppercase font-mono">Annual</span>
                          <span className="font-semibold text-slate-200 num-tabular">{displayAnnual}/yr</span>
                        </div>
                        <div className="bg-surface-canvas p-2 rounded border border-surface-border">
                          <span className="text-slate-500 block text-[9px] uppercase font-mono">Per Km</span>
                          <span className="font-semibold text-brand-300 num-tabular">₹{displayCostKm}/km</span>
                        </div>
                      </div>
                    </div>

                    {/* 2. Gross Outflow Breakdown */}
                    <div className="bg-surface-canvas/60 p-5 rounded border border-surface-border flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                            Gross Outflow
                          </span>
                          <span className="text-xs font-bold text-slate-200 num-tabular">
                            {tcoData.ownership?.gross_cost_formatted || formatLakhs(tcoData.ownership?.gross_cost)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mb-3">
                          Total cumulative cash spent over {tcoHorizon} years.
                        </p>

                        <div className="space-y-1.5 text-xs">
                          <div className="flex justify-between items-center py-1 border-b border-surface-border">
                            <span className="text-slate-400">Purchase Outlay:</span>
                            <span className="font-semibold text-slate-200 num-tabular">{tcoData.ownership?.purchase_cost_formatted || formatLakhs(tcoData.ownership?.purchase_cost)}</span>
                          </div>
                          <div className="flex justify-between items-center py-1 border-b border-surface-border">
                            <span className="text-slate-400">Fuel / Energy:</span>
                            <span className="font-semibold text-slate-200 num-tabular">{tcoData.ownership?.fuel_cost_formatted || formatLakhs(tcoData.ownership?.fuel_cost)}</span>
                          </div>
                          <div className="flex justify-between items-center py-1 border-b border-surface-border">
                            <span className="text-slate-400">Insurance:</span>
                            <span className="font-semibold text-slate-200 num-tabular">{tcoData.ownership?.insurance_cost_formatted || formatLakhs(tcoData.ownership?.insurance_cost)}</span>
                          </div>
                          <div className="flex justify-between items-center py-1 border-b border-surface-border">
                            <span className="text-slate-400">Maintenance:</span>
                            <span className="font-semibold text-slate-200 num-tabular">{tcoData.ownership?.maintenance_cost_formatted || formatLakhs(tcoData.ownership?.maintenance_cost)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-[10px] font-mono text-slate-500 mt-3 pt-2 border-t border-surface-border">
                        Projected Usage: {tcoData.ownership?.total_projected_km?.toLocaleString('en-IN') || 0} km
                      </div>
                    </div>

                    {/* 3. Resale Projection & Uncertainty */}
                    <div className="bg-surface-canvas/60 p-5 rounded border border-surface-border flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400">
                            {tcoHorizon}-Year Resale
                          </span>
                          <span className={getRiskBadgeStyle(tcoData.resale?.confidence === 'HIGH' ? 'LOW' : 'MODERATE')}>
                            {tcoData.resale?.confidence || 'MODERATE'} EVIDENCE
                          </span>
                        </div>
                        <div className="text-xl sm:text-2xl font-bold text-emerald-400 num-tabular">
                          {displayResale}
                        </div>
                        <div className="text-xs text-slate-300 font-medium mt-1 num-tabular">
                          Bound: {tcoData.resale?.lower_bound_formatted || formatLakhs(tcoData.resale?.lower_bound)} – {tcoData.resale?.upper_bound_formatted || formatLakhs(tcoData.resale?.upper_bound)}
                        </div>
                        <p className="text-xs text-slate-400 mt-2">
                          Retention: <strong className="text-white num-tabular">{tcoData.resale?.projected_retention_pct ?? 0}%</strong> of purchase price (~{tcoData.resale?.annual_depreciation_rate ?? 0}%/yr)
                        </p>
                      </div>

                      <div className="bg-surface-canvas p-2.5 rounded border border-surface-border text-[11px] text-slate-400 mt-4 leading-relaxed">
                        <span className="text-slate-300 font-semibold block mb-0.5">Methodology:</span>
                        {tcoData.resale?.methodology || 'Market-anchored geometric depreciation.'}
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Year-by-Year Resale & Cost Progression Table */}
              <div className="bg-surface-canvas/60 p-4 rounded border border-surface-border">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-2 border-b border-surface-border">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Year-by-Year Cost & Resale Progression
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Model pattern: {tcoAnnualKm.toLocaleString('en-IN')} km/year
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-surface-canvas text-[10px] font-mono uppercase tracking-wider text-slate-400 border-b border-surface-border">
                      <tr>
                        <th className="py-2 px-3">Horizon</th>
                        <th className="py-2 px-3">Age</th>
                        <th className="py-2 px-3">Projected Resale</th>
                        <th className="py-2 px-3">Resale Range (80%)</th>
                        <th className="py-2 px-3">Cumulative Outflow</th>
                        <th className="py-2 px-3">Net Cost</th>
                        <th className="py-2 px-3">Cost / km</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border num-tabular">
                      {(tcoData.yearly_projection || []).map((item) => {
                        const resaleVal = item.resale_value_formatted || (item.projected_resale_value !== undefined ? formatLakhs(item.projected_resale_value) : item.resale_value !== undefined ? formatLakhs(item.resale_value) : '—');
                        const resaleLow = item.resale_low_formatted || (item.projected_resale_low !== undefined ? formatLakhs(item.projected_resale_low) : item.resale_low !== undefined ? formatLakhs(item.resale_low) : '—');
                        const resaleHigh = item.resale_high_formatted || (item.projected_resale_high !== undefined ? formatLakhs(item.projected_resale_high) : item.resale_high !== undefined ? formatLakhs(item.resale_high) : '—');
                        const cumGross = item.cumulative_gross_formatted || (item.cumulative_expenditure !== undefined ? formatLakhs(item.cumulative_expenditure) : item.cumulative_gross !== undefined ? formatLakhs(item.cumulative_gross) : '—');
                        const netCost = item.net_cost_to_date_formatted || (item.net_cost_to_date !== undefined ? formatLakhs(item.net_cost_to_date) : '—');
                        const costPerKm = item.cost_per_km_to_date !== undefined && item.cost_per_km_to_date !== null
                          ? `₹${item.cost_per_km_to_date.toFixed(2)}/km`
                          : (item.cumulative_km && item.cumulative_km > 0 && item.net_cost_to_date !== undefined)
                          ? `₹${(item.net_cost_to_date / item.cumulative_km).toFixed(2)}/km`
                          : '—';

                        return (
                          <tr key={item.year} className="hover:bg-surface-canvas/40 transition">
                            <td className="py-2 px-3 font-semibold text-white">Year {item.year}</td>
                            <td className="py-2 px-3 text-slate-400">{item.vehicle_age} yrs</td>
                            <td className="py-2 px-3 font-semibold text-emerald-400">{resaleVal}</td>
                            <td className="py-2 px-3 text-slate-400 text-[11px]">{resaleLow} – {resaleHigh}</td>
                            <td className="py-2 px-3 text-slate-300">{cumGross}</td>
                            <td className="py-2 px-3 font-semibold text-brand-300">{netCost}</td>
                            <td className="py-2 px-3 text-amber-300">{costPerKm}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Sensitivity Analysis Grid */}
              <div className="bg-surface-canvas/60 p-4 rounded border border-surface-border">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-surface-border">
                  <div>
                    <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider block">
                      Deterministic Sensitivity Analysis
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Marginal impact of individual variable perturbations on net expenditure:
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">± Perturbations</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
                  {tcoData.sensitivity.map((sens, idx) => (
                    <div
                      key={idx}
                      className="bg-surface-canvas p-3 rounded border border-surface-border flex flex-col justify-between"
                    >
                      <div>
                        <span className="text-[11px] font-semibold text-slate-200 block truncate">
                          {sens.variable}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">
                          {sens.perturbation}
                        </span>
                      </div>

                      <div className="mt-2.5 pt-2 border-t border-surface-border">
                        <div className="flex items-center justify-between num-tabular">
                          <span className={`text-xs font-mono font-bold ${
                            sens.direction === 'DECREASE' ? 'text-emerald-400' : 'text-rose-400'
                          }`}>
                            {sens.impact_formatted}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {sens.impact_percentage > 0 ? '+' : ''}{sens.impact_percentage}%
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 block mt-0.5 num-tabular">
                          New: {sens.new_net_tco_formatted}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Disclaimers */}
              <div className="bg-surface-canvas/40 p-3 rounded border border-surface-border text-xs text-slate-400 italic">
                <p>
                  * {tcoData.disclaimer} Resale projections are calibrated to historical market trajectories and age decay curves, not guaranteed transactions.
                </p>
              </div>
            </div>
          )}

          {/* Row 4.5: Market Forecasting & Timing */}
          {forecastData && (
            <div className="card-surface p-5 space-y-5">
              {/* Header Banner */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-surface-border">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                      Forecast Analytics
                    </span>
                    <span className="badge-info text-[10px]">
                      Temporal Trajectory
                    </span>
                  </div>
                  <h3 className="text-base sm:text-lg font-semibold text-slate-100 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-brand-400" />
                    Market Forecasting & Timing Signals
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {forecastData.trend_summary}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="flex items-center gap-1.5 bg-surface-canvas px-3 py-1 rounded border border-surface-border text-xs">
                    <span className="text-slate-400">Confidence:</span>
                    <span className={`font-bold num-tabular ${
                      forecastData.forecast_confidence === 'HIGH' ? 'text-emerald-400' :
                      forecastData.forecast_confidence === 'MODERATE' ? 'text-brand-400' : 'text-amber-400'
                    }`}>
                      {forecastData.forecast_confidence} ({Math.round(forecastData.forecast_confidence_score)}/100)
                    </span>
                  </div>

                  <span className={getTrendBadgeStyle(forecastData.overall_trend)}>
                    {forecastData.overall_trend === 'RISING' && <TrendingUp className="w-3 h-3 inline mr-1" />}
                    {forecastData.overall_trend === 'DECLINING' && <TrendingDown className="w-3 h-3 inline mr-1" />}
                    {forecastData.overall_trend === 'STABLE' && <Activity className="w-3 h-3 inline mr-1" />}
                    {forecastData.overall_trend.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>

              {forecastData.status === 'INSUFFICIENT_EVIDENCE' ? (
                <div className="bg-surface-canvas/60 p-6 rounded border border-amber-500/30 text-center max-w-2xl mx-auto space-y-3">
                  <div className="w-10 h-10 rounded-full bg-amber-500/15 text-amber-400 flex items-center justify-center mx-auto">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-100">Insufficient Marketplace Evidence for Forecasting</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    AutoValue refuses to manufacture synthetic price forecasts without sufficient historical depth in this specific segment.
                  </p>
                  <div className="bg-surface-canvas p-3 rounded border border-surface-border text-left text-xs space-y-1.5">
                    <span className="text-slate-300 font-semibold block">Missing Evidence Audit:</span>
                    <ul className="list-disc list-inside space-y-1 text-slate-400">
                      {forecastData.evidence.missing_evidence_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <>
                  {/* Momentum Cards Grid */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {[
                      { label: '30-Day Momentum', data: forecastData.momentum?.m30d },
                      { label: '90-Day Momentum', data: forecastData.momentum?.m90d },
                      { label: '180-Day Momentum', data: forecastData.momentum?.m180d },
                      { label: '1-Year Direction', data: forecastData.momentum?.m365d },
                    ].map((m, idx) => (
                      <div key={idx} className="bg-surface-canvas/60 p-3.5 rounded border border-surface-border flex flex-col justify-between">
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">{m.label}</span>
                            <span className={getTrendBadgeStyle(m.data?.direction || 'INSUFFICIENT_EVIDENCE')}>
                              {m.data?.direction || 'N/A'}
                            </span>
                          </div>
                          <div className="text-lg font-bold text-slate-100 mt-1 num-tabular">
                            {m.data?.price_change_pct !== null && m.data?.price_change_pct !== undefined ? (
                              <span className={m.data.price_change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                                {m.data.price_change_pct >= 0 ? '+' : ''}{m.data.price_change_pct.toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-slate-500 text-sm">N/A</span>
                            )}
                          </div>
                        </div>
                        <div className="mt-2.5 pt-2 border-t border-surface-border text-[10px] text-slate-400 truncate num-tabular">
                          {m.data?.historical_median ? `Prev: ₹${m.data.historical_median.toLocaleString('en-IN')}` : m.data?.description || '—'}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Buy Timing vs Sell Timing Scorecards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Buy Timing Card */}
                    <div className="bg-surface-canvas/80 p-4 rounded border-l-2 border-l-brand-500 border-t border-r border-b border-surface-border space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-surface-border">
                        <div>
                          <span className="text-xs font-semibold text-brand-400 block uppercase">Buy Timing Indicator</span>
                          <span className="text-[10px] text-slate-400">Buyer negotiation and entry leverage</span>
                        </div>
                        <span className={getTimingBadgeStyle(forecastData.buy_timing.signal)}>
                          {forecastData.buy_timing.rating_label}
                        </span>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="w-14 h-14 rounded-lg bg-surface-canvas border border-surface-border p-2 flex flex-col items-center justify-center shrink-0">
                          <span className="text-lg font-bold text-brand-400 num-tabular">{forecastData.buy_timing.score ?? '—'}</span>
                          <span className="text-[8px] text-slate-500 font-mono">/ 100</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {forecastData.buy_timing.methodology_summary}
                        </p>
                      </div>

                      {/* Buy Factors Accordion */}
                      <div className="bg-surface-canvas rounded p-2.5 border border-surface-border space-y-2 text-xs">
                        <button
                          onClick={() => setShowBuyFactors(!showBuyFactors)}
                          className="w-full flex justify-between items-center text-slate-400 hover:text-slate-200 font-medium"
                        >
                          <span>Underlying factor breakdown</span>
                          {showBuyFactors ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        {showBuyFactors && (
                          <div className="space-y-1.5 pt-2 border-t border-surface-border">
                            {forecastData.buy_timing.positive_factors.map((f, i) => (
                              <div key={i} className="flex items-start gap-2 text-slate-300">
                                <span className="text-emerald-400 font-bold shrink-0">+</span>
                                <span>{f}</span>
                              </div>
                            ))}
                            {forecastData.buy_timing.negative_factors.map((f, i) => (
                              <div key={i} className="flex items-start gap-2 text-slate-400">
                                <span className="text-amber-400 font-bold shrink-0">-</span>
                                <span>{f}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Sell Timing Card */}
                    <div className="bg-surface-canvas/80 p-4 rounded border-l-2 border-l-purple-500 border-t border-r border-b border-surface-border space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-surface-border">
                        <div>
                          <span className="text-xs font-semibold text-purple-400 block uppercase">Sell Timing Indicator</span>
                          <span className="text-[10px] text-slate-400">Asset liquidation and value retention leverage</span>
                        </div>
                        <span className={getTimingBadgeStyle(forecastData.sell_timing.signal)}>
                          {forecastData.sell_timing.rating_label}
                        </span>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="w-14 h-14 rounded-lg bg-surface-canvas border border-surface-border p-2 flex flex-col items-center justify-center shrink-0">
                          <span className="text-lg font-bold text-purple-400 num-tabular">{forecastData.sell_timing.score ?? '—'}</span>
                          <span className="text-[8px] text-slate-500 font-mono">/ 100</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {forecastData.sell_timing.methodology_summary}
                        </p>
                      </div>

                      {/* Sell Factors Accordion */}
                      <div className="bg-surface-canvas rounded p-2.5 border border-surface-border space-y-2 text-xs">
                        <button
                          onClick={() => setShowSellFactors(!showSellFactors)}
                          className="w-full flex justify-between items-center text-slate-400 hover:text-slate-200 font-medium"
                        >
                          <span>Underlying factor breakdown</span>
                          {showSellFactors ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        {showSellFactors && (
                          <div className="space-y-1.5 pt-2 border-t border-surface-border">
                            {forecastData.sell_timing.positive_factors.map((f, i) => (
                              <div key={i} className="flex items-start gap-2 text-slate-300">
                                <span className="text-emerald-400 font-bold shrink-0">+</span>
                                <span>{f}</span>
                              </div>
                            ))}
                            {forecastData.sell_timing.negative_factors.map((f, i) => (
                              <div key={i} className="flex items-start gap-2 text-slate-400">
                                <span className="text-amber-400 font-bold shrink-0">-</span>
                                <span>{f}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Forecast Chart */}
                  <div className="bg-surface-canvas/60 p-4 rounded border border-surface-border space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-surface-border">
                      <div>
                        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                          Market Price Trajectory & Uncertainty Corridor
                        </span>
                        <span className="text-[11px] text-slate-400">
                          Historical asking-price trend connected to 1-year bounded forecast projections
                        </span>
                      </div>

                      {/* Horizon Selector */}
                      <div className="flex items-center gap-1 bg-surface-canvas p-1 rounded border border-surface-border text-xs">
                        {[
                          { label: '30D', days: 30 },
                          { label: '90D', days: 90 },
                          { label: '180D', days: 180 },
                          { label: '1 Year', days: 365 },
                        ].map((btn) => (
                          <button
                            key={btn.days}
                            onClick={() => handleForecastHorizonChange(btn.days)}
                            disabled={forecastLoading}
                            className={`px-2 py-0.5 rounded text-xs font-medium transition ${
                              forecastHorizon === btn.days
                                ? 'bg-brand-600 text-white'
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                          >
                            {btn.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="h-60 sm:h-64 w-full pt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={[
                            ...forecastData.historical_points.map((hp) => ({
                              period: hp.period_label,
                              observedMedian: hp.median_price,
                              type: 'Historical'
                            })),
                            {
                              period: 'Now',
                              observedMedian: forecastData.current_market_median,
                              baseForecast: forecastData.current_market_median,
                              lowerBound: forecastData.current_market_median,
                              upperBound: forecastData.current_market_median,
                              type: 'Current'
                            },
                            ...forecastData.forecast_points.map((fp) => ({
                              period: `+${fp.horizon_days}D`,
                              baseForecast: fp.base_price,
                              lowerBound: fp.lower_bound,
                              upperBound: fp.upper_bound,
                              type: 'Forecast'
                            }))
                          ]}
                          margin={{ top: 10, right: 15, left: 10, bottom: 5 }}
                        >
                          <defs>
                            <linearGradient id="forecastCorridor" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#0284c7" stopOpacity={0.25} />
                              <stop offset="95%" stopColor="#0284c7" stopOpacity={0.02} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1c263c" />
                          <XAxis dataKey="period" stroke="#64748b" fontSize={11} />
                          <YAxis
                            stroke="#64748b"
                            fontSize={11}
                            domain={['auto', 'auto']}
                            tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`}
                          />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#090d16', borderColor: '#1c263c', borderRadius: '0.5rem', fontSize: '11px' }}
                            formatter={(value: any, name: any) => [
                              `₹${Number(value).toLocaleString('en-IN')}`,
                              name === 'observedMedian' ? 'Observed Market Median' :
                              name === 'baseForecast' ? 'Base Forecast Estimate' :
                              name === 'upperBound' ? 'Optimistic Upper Bound' : 'Conservative Lower Bound'
                            ]}
                          />
                          <Area
                            type="monotone"
                            dataKey="upperBound"
                            stroke="#0284c7"
                            strokeDasharray="3 3"
                            fill="url(#forecastCorridor)"
                            strokeOpacity={0.4}
                          />
                          <Area
                            type="monotone"
                            dataKey="lowerBound"
                            stroke="#0284c7"
                            strokeDasharray="3 3"
                            fill="transparent"
                            strokeOpacity={0.4}
                          />
                          <Line
                            type="monotone"
                            dataKey="observedMedian"
                            stroke="#2dd4bf"
                            strokeWidth={2.5}
                            dot={{ fill: '#2dd4bf', r: 3 }}
                          />
                          <Line
                            type="monotone"
                            dataKey="baseForecast"
                            stroke="#0284c7"
                            strokeWidth={2}
                            strokeDasharray="4 4"
                            dot={{ fill: '#0284c7', r: 3 }}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="flex flex-wrap items-center justify-center gap-5 pt-2 text-xs text-slate-400 border-t border-surface-border">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-teal-400 inline-block"></span>
                        <span>Observed Historical Median</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-3 h-0.5 border-t-2 border-dashed border-brand-400 inline-block"></span>
                        <span>Base Forecast Trajectory</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 bg-brand-500/20 border border-brand-500/40 rounded inline-block"></span>
                        <span>Uncertainty Corridor</span>
                      </div>
                    </div>
                  </div>

                  {/* Scenario Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {forecastData.forecast_points.length > 0 && (() => {
                      const pt1y = forecastData.forecast_points[forecastData.forecast_points.length - 1];
                      const sc = pt1y.scenarios;
                      return (
                        <>
                          <div className="bg-surface-canvas/60 p-3.5 rounded border border-surface-border flex flex-col justify-between">
                            <div>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-[10px] font-mono text-amber-400 uppercase tracking-wider">Conservative</span>
                                <span className="text-[10px] text-slate-500">12 Months</span>
                              </div>
                              <div className="text-xl font-bold text-slate-100 mt-1 num-tabular">
                                {sc.CONSERVATIVE?.projected_value_formatted}
                              </div>
                              <p className="text-xs text-slate-400 mt-0.5 num-tabular">
                                Downside-aware path ({sc.CONSERVATIVE?.change_from_current_pct}%)
                              </p>
                            </div>
                            <div className="mt-3 pt-2 border-t border-surface-border text-[10px] text-slate-400 font-mono">
                              Deprec: <strong className="text-slate-200">{sc.CONSERVATIVE?.annual_depreciation_rate_pct}%/yr</strong>
                            </div>
                          </div>

                          <div className="bg-surface-canvas/80 p-3.5 rounded border border-brand-500/30 flex flex-col justify-between">
                            <div>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-[10px] font-mono text-brand-400 uppercase tracking-wider">Base Forecast</span>
                                <span className="text-[10px] text-brand-400 font-mono bg-brand-500/10 px-1.5 py-0.2 rounded">Primary</span>
                              </div>
                              <div className="text-xl font-bold text-white mt-1 num-tabular">
                                {sc.BASE?.projected_value_formatted}
                              </div>
                              <p className="text-xs text-slate-300 mt-0.5 num-tabular">
                                Central estimate ({sc.BASE?.change_from_current_pct}%)
                              </p>
                            </div>
                            <div className="mt-3 pt-2 border-t border-surface-border text-[10px] text-slate-300 flex justify-between font-mono">
                              <span>Range: {sc.BASE?.lower_bound_formatted} – {sc.BASE?.upper_bound_formatted}</span>
                            </div>
                          </div>

                          <div className="bg-surface-canvas/60 p-3.5 rounded border border-surface-border flex flex-col justify-between">
                            <div>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider">Optimistic</span>
                                <span className="text-[10px] text-slate-500">12 Months</span>
                              </div>
                              <div className="text-xl font-bold text-slate-100 mt-1 num-tabular">
                                {sc.OPTIMISTIC?.projected_value_formatted}
                              </div>
                              <p className="text-xs text-slate-400 mt-0.5 num-tabular">
                                Upside-aware path ({sc.OPTIMISTIC?.change_from_current_pct}%)
                              </p>
                            </div>
                            <div className="mt-3 pt-2 border-t border-surface-border text-[10px] text-slate-400 font-mono">
                              Deprec: <strong className="text-slate-200">{sc.OPTIMISTIC?.annual_depreciation_rate_pct}%/yr</strong>
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>

                  {/* Evidence Provenance Audit Drawer */}
                  <div className="bg-surface-canvas/40 rounded p-3.5 border border-surface-border text-xs space-y-2">
                    <button
                      onClick={() => setShowEvidenceAudit(!showEvidenceAudit)}
                      className="w-full flex justify-between items-center text-slate-300 hover:text-white font-medium"
                    >
                      <span className="flex items-center gap-2">
                        <Search className="w-3.5 h-3.5 text-brand-400" />
                        <span>Data Provenance & Methodology Audit</span>
                        <span className="text-[10px] text-slate-500 font-mono">({forecastData.evidence.source})</span>
                      </span>
                      {showEvidenceAudit ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {showEvidenceAudit && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2.5 border-t border-surface-border text-slate-400">
                        <div>
                          <span className="text-slate-500 block text-[9px] uppercase font-mono">Segment Match</span>
                          <span className="text-slate-200 font-medium">{forecastData.evidence.segment_hierarchy_used}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[9px] uppercase font-mono">Historical Span</span>
                          <span className="text-slate-200 font-medium">{forecastData.evidence.history_days} Days ({forecastData.evidence.earliest_observation_date} to {forecastData.evidence.latest_observation_date})</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[9px] uppercase font-mono">Forecast Algorithm</span>
                          <span className="text-slate-200 font-medium">{forecastData.evidence.forecast_method} ({forecastData.evidence.forecast_model_version})</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[9px] uppercase font-mono">Depreciation Model</span>
                          <span className="text-slate-200 font-medium">{forecastData.depreciation.methodology_comparison}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="bg-surface-canvas/40 p-3 rounded border border-surface-border text-xs text-slate-400 italic">
                    <p>
                      * {forecastData.disclaimer} AutoValue forecasts project asking price movements and statistical decay from observed marketplace evidence.
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Row 5: What-If Vehicle Simulator */}
          <div className="card-surface p-5 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-brand-400" />
                  Counterfactual Scenario Simulator
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Simulate counterfactual adjustments in mileage, model year, location, or fuel using active XGBoost inference.
                </p>
              </div>
              <span className="text-[10px] font-mono text-slate-400 bg-surface-canvas px-2 py-0.5 rounded border border-surface-border self-start md:self-auto">
                Non-destructive simulation
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 bg-surface-canvas/60 p-3.5 rounded border border-surface-border">
              <div>
                <label className="text-[11px] text-slate-400 block mb-1 font-medium">Odometer (km)</label>
                <input
                  type="number"
                  step="5000"
                  value={scenarioKm}
                  onChange={(e) => setScenarioKm(Number(e.target.value))}
                  className="input-field text-xs py-1.5"
                />
              </div>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1 font-medium">Manufacturing Year</label>
                <select
                  value={scenarioYear}
                  onChange={(e) => setScenarioYear(Number(e.target.value))}
                  className="input-field text-xs py-1.5"
                >
                  {[2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014].map((yr) => (
                    <option key={yr} value={yr}>
                      {yr}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1 font-medium">Fuel Type</label>
                <select
                  value={scenarioFuel}
                  onChange={(e) => setScenarioFuel(e.target.value)}
                  className="input-field text-xs py-1.5"
                >
                  {['Petrol', 'Diesel', 'CNG', 'Electric'].map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1 font-medium">City Location</label>
                <select
                  value={scenarioCity}
                  onChange={(e) => setScenarioCity(e.target.value)}
                  className="input-field text-xs py-1.5"
                >
                  {['Mumbai', 'Delhi', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai', 'Kolkata', 'Ahmedabad'].map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={runScenarioSimulation}
                  disabled={simulating}
                  className="btn-primary text-xs w-full py-2"
                >
                  {simulating ? 'Simulating...' : 'Run Simulation'}
                </button>
              </div>
            </div>

            {/* Simulation Results Display */}
            {scenarioResult && (
              <div className="bg-surface-canvas/80 p-4 rounded border border-brand-500/30">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase">Simulated Estimate</span>
                    <div className="text-xl font-bold text-white mt-0.5 num-tabular">
                      ₹{scenarioResult.scenario_estimate.toLocaleString('en-IN')}
                    </div>
                  </div>
                  <div className="sm:text-right">
                    <span className="text-[10px] font-mono text-slate-400 uppercase">Projected Value Impact</span>
                    <div
                      className={`text-base font-bold mt-0.5 num-tabular ${
                        scenarioResult.estimated_change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {scenarioResult.estimated_change >= 0 ? '+' : ''}
                      ₹{scenarioResult.estimated_change.toLocaleString('en-IN')} ({scenarioResult.percentage_change > 0 ? '+' : ''}
                      {scenarioResult.percentage_change.toFixed(1)}%)
                    </div>
                  </div>
                </div>

                <div className="mt-3 space-y-1.5">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                    Scenario Model Drivers
                  </span>
                  {scenarioResult.explanation.map((exp, idx) => (
                    <p key={idx} className="text-xs text-slate-300 leading-relaxed">
                      • {exp}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Row 6: Alternative Vehicle Discovery */}
          <div className="card-surface p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <Car className="w-4 h-4 text-brand-400" />
                  Evidence-Supported Market Alternatives
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Vehicles matching your budget band ranked by proximity, mileage, and specification similarity.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-mono">Budget:</span>
                <input
                  type="number"
                  step="50000"
                  value={altBudget}
                  onChange={(e) => {
                    const b = Number(e.target.value);
                    setAltBudget(b);
                    loadAlternatives(b, vehicle.fuel_type);
                  }}
                  className="input-field text-xs py-1 w-32 num-tabular"
                />
              </div>
            </div>

            {loadingAlts ? (
              <div className="py-6 text-center text-xs text-slate-400">Searching comparable listings...</div>
            ) : alternatives.length === 0 ? (
              <div className="py-6 text-center text-xs text-slate-500">
                No alternative listings found near ₹{altBudget.toLocaleString('en-IN')}.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {alternatives.map((alt) => (
                  <div
                    key={alt.listing_id}
                    className="bg-surface-canvas/60 p-3.5 rounded border border-surface-border hover:border-slate-700 transition flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="text-[10px] bg-surface-canvas text-slate-400 px-1.5 py-0.2 rounded font-mono border border-surface-border">
                          {alt.year}
                        </span>
                        <span className="text-[10px] font-bold text-teal-400 font-mono num-tabular">
                          {alt.overall_match_score}% Match
                        </span>
                      </div>
                      <h4 className="font-semibold text-xs text-slate-100 truncate">
                        {alt.brand} {alt.model}
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-0.5 num-tabular">{alt.city || 'India'} • {alt.km_driven.toLocaleString('en-IN')} km</p>
                      <div className="mt-2.5 text-sm font-bold text-white num-tabular">
                        {alt.listed_price_formatted}
                      </div>
                    </div>

                    <div className="mt-2.5 pt-2 border-t border-surface-border">
                      <span className="text-[10px] text-slate-500 block truncate">
                        {alt.match_reasons.join(' ')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Row 7: Observed Movement & SHAP Attributions */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Market Timing */}
            <div className="card-surface p-5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-border">
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-brand-400" />
                  Observed Market Movement
                </h3>
                <span className={getTrendBadgeStyle(intelligence.market_timing.direction)}>
                  {intelligence.market_timing.direction}
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {intelligence.market_timing.summary}
              </p>

              <div className="grid grid-cols-2 gap-2.5 bg-surface-canvas/60 p-3 rounded border border-surface-border text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Recent Median</span>
                  <span className="text-sm font-bold text-slate-200 num-tabular">
                    {intelligence.market_timing.recent_median
                      ? `₹${intelligence.market_timing.recent_median.toLocaleString('en-IN')}`
                      : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Price Movement</span>
                  <span className="text-sm font-bold text-slate-200 num-tabular">
                    {intelligence.market_timing.percentage_movement !== null && intelligence.market_timing.percentage_movement !== undefined
                      ? `${intelligence.market_timing.percentage_movement > 0 ? '+' : ''}${intelligence.market_timing.percentage_movement.toFixed(1)}%`
                      : 'N/A'}
                  </span>
                </div>
              </div>

              <p className="text-[11px] text-slate-500 italic pt-1">
                {intelligence.market_timing.disclaimer}
              </p>
            </div>

            {/* SHAP Feature Attributions */}
            <div className="card-surface p-5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-border">
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-400" />
                  Key Valuation Drivers (SHAP)
                </h3>
                <span className="text-[10px] text-slate-500 font-mono">Feature Impact</span>
              </div>

              <div className="space-y-2">
                {intelligence.shap_explanations.slice(0, 4).map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-surface-canvas/60 p-2.5 rounded border border-surface-border text-xs"
                  >
                    <div>
                      <span className="font-medium text-slate-200 block capitalize">
                        {item.feature.replace(/_/g, ' ')}
                      </span>
                      <span className="text-slate-400 text-[11px]">{item.human_readable_text}</span>
                    </div>
                    <span
                      className={`font-mono font-bold shrink-0 ml-3 num-tabular ${
                        item.direction === 'increases_price' ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {item.direction === 'increases_price' ? '+' : '-'}₹
                      {Math.abs(item.impact_inr).toLocaleString('en-IN')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Row 8: Limitations & Physical Unknowns */}
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-5">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs mb-2">
              <AlertTriangle className="w-4 h-4" />
              <span>Critical Limitations & Unverified Physical Factors</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed mb-3">
              {intelligence.confidence.disclaimer_text}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-amber-200/80">
              {intelligence.confidence.unverified_factors.map((factor, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <span className="text-amber-400 text-xs">•</span>
                  <span className="capitalize">{factor}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Formula Calculation Modal */}
      {showFormulaModal && intelligence && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card-elevated max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-surface-border pb-3">
              <h3 className="font-semibold text-white text-sm">Value Score Mathematical Breakdown</h3>
              <button
                onClick={() => setShowFormulaModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-2.5 text-xs text-slate-300">
              <div className="bg-surface-canvas p-3 rounded border border-surface-border">
                <span className="font-semibold text-brand-400 block mb-0.5">1. Price Advantage Formula</span>
                <p>{intelligence.value_score.score_breakdown.price_formula}</p>
              </div>
              <div className="bg-surface-canvas p-3 rounded border border-surface-border">
                <span className="font-semibold text-teal-400 block mb-0.5">2. Mileage Ratio Formula</span>
                <p>{intelligence.value_score.score_breakdown.mileage_formula}</p>
              </div>
              <div className="bg-surface-canvas p-3 rounded border border-surface-border">
                <span className="font-semibold text-indigo-400 block mb-0.5">3. Age Lifecycle Formula</span>
                <p>{intelligence.value_score.score_breakdown.age_formula}</p>
              </div>
              <div className="bg-surface-canvas p-3 rounded border border-surface-border">
                <span className="font-semibold text-purple-400 block mb-0.5">4. Empirical Market Support</span>
                <p>{intelligence.value_score.score_breakdown.market_support_formula}</p>
              </div>
              <div className="bg-surface-canvas p-3 rounded border border-brand-500/30 font-mono text-brand-300">
                {intelligence.value_score.score_breakdown.overall_calculation}
              </div>
            </div>
            <div className="pt-3 border-t border-surface-border text-right">
              <button
                onClick={() => setShowFormulaModal(false)}
                className="btn-secondary text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Risk Factor Evidence & Explanation Modal */}
      {selectedRiskFactor && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card-elevated max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-surface-border pb-3">
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-mono">
                  Risk Factor Mathematical Evidence
                </span>
                <h3 className="font-semibold text-white text-sm mt-0.5">{selectedRiskFactor.name}</h3>
              </div>
              <button
                onClick={() => setSelectedRiskFactor(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-300">
              {/* Score summary bar */}
              <div className="bg-surface-canvas p-3 rounded border border-surface-border flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 block uppercase font-mono">Score</span>
                  <div className="text-base font-bold text-white mt-0.5 num-tabular">
                    {selectedRiskFactor.score} <span className="text-xs text-slate-400">/ 100</span>
                  </div>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block uppercase font-mono">Severity</span>
                  <span className={getRiskBadgeStyle(selectedRiskFactor.severity)}>
                    {selectedRiskFactor.severity.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 block uppercase font-mono">Weight Impact</span>
                  <span className="text-xs font-mono font-bold text-brand-400 num-tabular">
                    {selectedRiskFactor.weighted_contribution !== undefined && selectedRiskFactor.weighted_contribution !== null
                      ? selectedRiskFactor.weighted_contribution.toFixed(1)
                      : selectedRiskFactor.weight !== undefined && selectedRiskFactor.score !== undefined
                      ? (selectedRiskFactor.score * selectedRiskFactor.weight).toFixed(1)
                      : '0.0'}{' '}
                    pts ({selectedRiskFactor.weight !== undefined ? (selectedRiskFactor.weight * 100).toFixed(0) : '0'}%)
                  </span>
                </div>
              </div>

              {/* Observed Mathematical Evidence */}
              <div className="bg-surface-canvas p-3 rounded border border-surface-border">
                <span className="font-semibold text-brand-400 block mb-1.5 uppercase tracking-wider text-[10px] font-mono">
                  Observed Mathematical Evidence
                </span>
                <ul className="space-y-1">
                  {selectedRiskFactor.evidence.map((ev, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-slate-200">
                      <span className="text-brand-400 font-bold">•</span>
                      <span>{ev}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Plain-Language Interpretation */}
              <div className="bg-surface-canvas p-3 rounded border border-surface-border">
                <span className="font-semibold text-teal-400 block mb-1 uppercase tracking-wider text-[10px] font-mono">
                  Interpretation & Risk Implication
                </span>
                <p className="text-slate-300 leading-relaxed">{selectedRiskFactor.interpretation}</p>
              </div>

              <div className="text-[10px] text-slate-500 italic">
                * Risk scores are computed deterministically from observed marketplace statistics and conformal calibration.
              </div>
            </div>

            <div className="pt-3 border-t border-surface-border text-right">
              <button
                onClick={() => setSelectedRiskFactor(null)}
                className="btn-secondary text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IntelligencePage;
