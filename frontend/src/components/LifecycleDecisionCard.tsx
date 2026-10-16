import React, { useState } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Clock,
  ShieldCheck,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Sliders,
  Gauge,
  Activity,
  Play
} from 'lucide-react';
import type {
  LifecycleDecision,
  LifecycleAction
} from '../services/api';

interface LifecycleDecisionCardProps {
  decision: LifecycleDecision | null;
  loading: boolean;
  onSimulateScenario?: (annualKm?: number, priceOverride?: number, marketShift?: number) => void;
  simulating?: boolean;
}

export const LifecycleDecisionCard: React.FC<LifecycleDecisionCardProps> = ({
  decision,
  loading,
  onSimulateScenario,
  simulating = false
}) => {
  const [selectedHorizon, setSelectedHorizon] = useState<number>(5);
  const [showAllFactors, setShowAllFactors] = useState<boolean>(false);
  const [showSimulator, setShowSimulator] = useState<boolean>(false);

  // Simulator inputs
  const [simKm, setSimKm] = useState<number>(decision?.vehicle_summary?.annual_km || 12000);
  const [simPriceShift, setSimPriceShift] = useState<number>(0);

  if (loading) {
    return (
      <div className="card-surface p-8 text-center animate-pulse">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent mb-3" />
        <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider">Evaluating Lifecycle Decision Engine...</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          Synthesizing valuation model, TCO curves, market momentum, risk indicators, and replacement options.
        </p>
      </div>
    );
  }

  if (!decision) {
    return null;
  }

  const {
    recommended_action,
    decision_score,
    confidence,
    confidence_score,
    positive_factors,
    negative_factors,
    horizon_outlooks,
    best_replacement_candidate,
    decision_sensitivities,
    missing_data
  } = decision;

  // Visual styling mapped to LifecycleAction
  const getActionBadge = (action: LifecycleAction) => {
    switch (action) {
      case 'BUY':
        return {
          title: 'BUY THIS VEHICLE',
          desc: 'Financially and market-wise favorable purchase opportunity relative to category peers.',
          textColor: 'text-emerald-400',
          borderColor: 'border-emerald-500/30',
          bgLight: 'bg-emerald-500/10',
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        };
      case 'KEEP':
        return {
          title: 'HOLD / MAINTAIN POSITION',
          desc: 'Ownership economics and market depreciation position strongly favor holding current asset.',
          textColor: 'text-brand-400',
          borderColor: 'border-brand-500/30',
          bgLight: 'bg-brand-500/10',
          icon: <ShieldCheck className="w-5 h-5 text-brand-400" />
        };
      case 'SELL_NOW':
        return {
          title: 'CONSIDER TIMED SALE',
          desc: 'Current market near local valuation peak; projected depreciation curve accelerates noticeably.',
          textColor: 'text-amber-400',
          borderColor: 'border-amber-500/30',
          bgLight: 'bg-amber-500/10',
          icon: <TrendingUp className="w-5 h-5 text-amber-400" />
        };
      case 'WAIT':
        return {
          title: 'MONITOR POSITION',
          desc: 'Market momentum developing; immediate execution carries neutral risk/reward.',
          textColor: 'text-indigo-400',
          borderColor: 'border-indigo-500/30',
          bgLight: 'bg-indigo-500/10',
          icon: <Clock className="w-5 h-5 text-indigo-400" />
        };
      case 'REPLACE':
        return {
          title: 'REPLACE WITH ALTERNATIVE',
          desc: 'Alternative candidate delivers measurable TCO and risk advantages surpassing switching friction.',
          textColor: 'text-rose-400',
          borderColor: 'border-rose-500/30',
          bgLight: 'bg-rose-500/10',
          icon: <RefreshCw className="w-5 h-5 text-rose-400" />
        };
      default:
        return {
          title: 'INSUFFICIENT EVIDENCE',
          desc: 'Critical vehicle or marketplace data unavailable for high-confidence recommendation.',
          textColor: 'text-slate-400',
          borderColor: 'border-surface-border',
          bgLight: 'bg-surface-canvas',
          icon: <AlertTriangle className="w-5 h-5 text-slate-400" />
        };
    }
  };

  const actionConfig = getActionBadge(recommended_action);
  const currentOutlook = horizon_outlooks.find(h => h.horizon_years === selectedHorizon) || horizon_outlooks[horizon_outlooks.length - 1];

  const handleSimulate = () => {
    if (onSimulateScenario) {
      onSimulateScenario(simKm, undefined, simPriceShift !== 0 ? simPriceShift : undefined);
    }
  };

  return (
    <div className="card-surface overflow-hidden mb-8">
      {/* 1. Header Banner: Primary Recommendation */}
      <div className="p-6 sm:p-7 border-b border-surface-border bg-surface-canvas">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-start gap-3.5">
            <div className={`p-2.5 rounded-lg ${actionConfig.bgLight} border ${actionConfig.borderColor}`}>
              {actionConfig.icon}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-surface-card text-brand-400 border border-surface-border">
                  Lifecycle Capital Allocation Engine
                </span>
                <span className="text-[11px] font-mono text-slate-400">• Mode: {decision.mode}</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                {actionConfig.title}
              </h2>
              <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                {actionConfig.desc}
              </p>
            </div>
          </div>

          {/* Decision Score & Confidence Gauges */}
          <div className="flex items-center gap-4 bg-surface-card p-3.5 rounded-lg border border-surface-border font-mono">
            <div className="text-center px-3 border-r border-surface-border">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block">
                Score
              </span>
              <div className="text-2xl sm:text-3xl font-extrabold text-white mt-0.5 num-tabular">
                {decision_score.overall_score.toFixed(0)}
                <span className="text-xs font-normal text-slate-500">/100</span>
              </div>
              <span className="text-[10px] text-brand-400 block mt-0.5 num-tabular">
                Margin: +{decision_score.decision_margin.toFixed(1)}
              </span>
            </div>

            <div className="text-center px-3">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 block">
                Confidence
              </span>
              <div className="mt-1">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  confidence === 'HIGH'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : confidence === 'MODERATE'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                }`}>
                  {confidence}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 block mt-1 num-tabular">
                {confidence_score.toFixed(0)}% Index
              </span>
            </div>
          </div>
        </div>

        {/* Insufficient Evidence Alert Banner if applicable */}
        {missing_data && missing_data.length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-amber-300">
              <strong className="font-semibold">Evidence Notice: </strong>
              Parameters with sparse regional coverage: {missing_data.join(', ')}. Model bounds widened accordingly.
            </div>
          </div>
        )}
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {/* 2. Six-Pillar Transparent Score Grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Gauge className="w-3.5 h-3.5 text-brand-400" />
              <span>Multi-Pillar Decision Attribution</span>
            </h3>
            <span className="text-[11px] font-mono text-slate-400 num-tabular">
              Weighted Sum = {decision_score.overall_score.toFixed(1)}/100
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {decision_score.category_breakdown.map((cat, idx) => (
              <div
                key={idx}
                className="bg-surface-canvas p-3.5 rounded-lg border border-surface-border transition"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-semibold text-slate-300">{cat.category_name}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-card text-brand-400 border border-surface-border">
                    {(cat.weight * 100).toFixed(0)}% Wt
                  </span>
                </div>
                <div className="flex items-baseline gap-2 mb-2 font-mono">
                  <span className="text-xl font-bold text-white num-tabular">{cat.score.toFixed(0)}</span>
                  <span className="text-[11px] text-slate-400">
                    Contrib: <strong className="text-slate-200 num-tabular">+{cat.contribution.toFixed(1)}</strong>
                  </span>
                </div>
                {/* Progress bar */}
                <div className="w-full bg-surface-card rounded-full h-1 mb-2 overflow-hidden border border-surface-border">
                  <div
                    className="bg-brand-500 h-1 rounded-full"
                    style={{ width: `${Math.min(100, Math.max(0, cat.score))}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                  {cat.reasoning}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* 3. Why? Empirical Factors Attribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Positive Factors */}
          <div className="bg-surface-canvas p-4 rounded-lg border border-surface-border">
            <h4 className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Supporting Signals ({positive_factors.length})</span>
            </h4>
            <div className="space-y-2">
              {positive_factors.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No dominant positive signals observed.</p>
              ) : (
                positive_factors.slice(0, showAllFactors ? undefined : 3).map((f, i) => (
                  <div key={i} className="bg-surface-card p-3 rounded border border-surface-border text-xs">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-semibold text-emerald-400">{f.category}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-canvas text-slate-400 font-mono border border-surface-border">
                        {f.source_type}
                      </span>
                    </div>
                    <p className="text-slate-300 leading-relaxed text-[11px]">{f.factor_text}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Negative Factors / Headwinds */}
          <div className="bg-surface-canvas p-4 rounded-lg border border-surface-border">
            <h4 className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Risk Signals & Headwinds ({negative_factors.length})</span>
            </h4>
            <div className="space-y-2">
              {negative_factors.slice(0, showAllFactors ? undefined : 3).map((f, i) => (
                <div key={i} className="bg-surface-card p-3 rounded border border-surface-border text-xs">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-amber-400">{f.category}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-canvas text-slate-400 font-mono border border-surface-border">
                      {f.source_type}
                    </span>
                  </div>
                  <p className="text-slate-300 leading-relaxed text-[11px]">{f.factor_text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Toggle all factors */}
        {(positive_factors.length > 3 || negative_factors.length > 3) && (
          <div className="text-center">
            <button
              onClick={() => setShowAllFactors(!showAllFactors)}
              className="text-xs font-mono text-brand-400 hover:text-brand-300 inline-flex items-center gap-1 transition"
            >
              {showAllFactors ? (
                <>
                  <span>Show Fewer Factors</span>
                  <ChevronUp className="w-3.5 h-3.5" />
                </>
              ) : (
                <>
                  <span>View All Empirical Factors</span>
                  <ChevronDown className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        )}

        {/* 4. Multi-Horizon Financial Outlook & Replacement Intelligence */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Ownership Horizon Projections */}
          <div className="lg:col-span-2 bg-surface-canvas p-5 rounded-lg border border-surface-border">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-brand-400" />
                  <span>Ownership Horizon Trajectory</span>
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">Cumulative financial commitment and resale retention curve.</p>
              </div>

              {/* Horizon Tabs */}
              <div className="flex items-center gap-1 bg-surface-card p-1 rounded-lg border border-surface-border">
                {[1, 3, 5].map(h => (
                  <button
                    key={h}
                    onClick={() => setSelectedHorizon(h)}
                    className={`px-2.5 py-1 rounded text-xs font-mono font-semibold transition ${
                      selectedHorizon === h
                        ? 'bg-brand-500 text-slate-950'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {h}Y Horizon
                  </button>
                ))}
              </div>
            </div>

            {currentOutlook && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                <div className="bg-surface-card p-3 rounded border border-surface-border">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">Projected Resale</span>
                  <span className="text-sm font-bold text-white block num-tabular">
                    {currentOutlook.projected_resale_formatted}
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Year {selectedHorizon} Terminal</span>
                </div>

                <div className="bg-surface-card p-3 rounded border border-surface-border">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">Cumulative TCO</span>
                  <span className="text-sm font-bold text-slate-200 block num-tabular">
                    {currentOutlook.total_cost_of_ownership_formatted}
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Deprec + Fuel + Maint</span>
                </div>

                <div className="bg-surface-card p-3 rounded border border-surface-border">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">Depreciation Loss</span>
                  <span className="text-sm font-bold text-amber-400 block num-tabular">
                    {currentOutlook.cumulative_depreciation_formatted}
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Asset Delta</span>
                </div>

                <div className="bg-surface-card p-3 rounded border border-surface-border">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">Cost Per KM</span>
                  <span className="text-sm font-bold text-brand-400 block num-tabular">
                    {currentOutlook.cost_per_km_formatted}
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Normalized Drag</span>
                </div>
              </div>
            )}
          </div>

          {/* Replacement Candidate Opportunity Card */}
          <div className="bg-surface-canvas p-5 rounded-lg border border-surface-border flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2 pb-2 border-b border-surface-border">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                  Replacement Arbitrage
                </span>
                <span className="text-[10px] text-slate-500 font-mono">Market Feed</span>
              </div>

              {best_replacement_candidate ? (
                <div>
                  <h5 className="text-sm font-bold text-white font-mono">
                    {best_replacement_candidate.brand} {best_replacement_candidate.model} ({best_replacement_candidate.year})
                  </h5>
                  <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                    {best_replacement_candidate.variant || 'Standard'} • {best_replacement_candidate.fuel_type}
                  </p>

                  <div className="mt-3 space-y-1.5 text-xs font-mono">
                    <div className="flex justify-between p-2 rounded bg-surface-card border border-surface-border">
                      <span className="text-slate-400 text-[11px]">5Y TCO Advantage:</span>
                      <span className="font-bold text-emerald-400 num-tabular">
                        {best_replacement_candidate.tco_savings_5y_formatted}
                      </span>
                    </div>

                    <div className="flex justify-between p-2 rounded bg-surface-card border border-surface-border">
                      <span className="text-slate-400 text-[11px]">Break-Even:</span>
                      <span className="font-semibold text-slate-200">
                        {best_replacement_candidate.break_even_months !== null && best_replacement_candidate.break_even_months !== undefined
                          ? `~${best_replacement_candidate.break_even_months} Mo`
                          : 'Immediate'}
                      </span>
                    </div>

                    <div className="flex justify-between p-2 rounded bg-surface-card border border-surface-border">
                      <span className="text-slate-400 text-[11px]">Advantage Index:</span>
                      <span className="font-bold text-brand-400 num-tabular">
                        {best_replacement_candidate.replacement_advantage_score.toFixed(0)}/100
                      </span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 mt-2.5 leading-relaxed italic">
                    "{best_replacement_candidate.recommendation_reason}"
                  </p>
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-slate-500">
                  <ShieldCheck className="w-6 h-6 text-slate-600 mx-auto mb-2" />
                  No alternative currently provides superior 5-year economics to justify replacement friction.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 5. Decision Sensitivity Thresholds */}
        {decision_sensitivities && decision_sensitivities.length > 0 && (
          <div className="bg-surface-canvas p-5 rounded-lg border border-surface-border">
            <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-brand-400" />
              <span>Critical Decision Pivot Thresholds</span>
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {decision_sensitivities.map((s, idx) => (
                <div key={idx} className="bg-surface-card p-3 rounded border border-surface-border">
                  <div className="flex justify-between items-center mb-1.5 font-mono">
                    <span className="font-bold text-white text-[11px]">{s.variable_name}</span>
                    <span className="px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-400 text-[10px] border border-brand-500/20">
                      Pivot: {s.action_before} → {s.action_after}
                    </span>
                  </div>
                  <p className="text-slate-400 leading-relaxed text-[11px]">{s.sensitivity_description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. Interactive What-If Simulation Controls */}
        <div className="bg-surface-canvas p-5 rounded-lg border border-surface-border">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-3.5 h-3.5 text-amber-400" />
                <span>Simulate Parameter Variations</span>
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">Test how driving usage or market price shifts impact the recommendation.</p>
            </div>
            <button
              onClick={() => setShowSimulator(!showSimulator)}
              className="text-xs font-mono text-brand-400 hover:text-brand-300 transition flex items-center gap-1"
            >
              {showSimulator ? 'Collapse Simulator' : 'Expand Simulator'}
              {showSimulator ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

          {showSimulator && (
            <div className="pt-4 mt-4 border-t border-surface-border grid grid-cols-1 sm:grid-cols-3 gap-5 items-end">
              <div>
                <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1.5">
                  Annual Mileage: <strong className="text-white num-tabular">{simKm.toLocaleString()} km/yr</strong>
                </label>
                <input
                  type="range"
                  min="3000"
                  max="40000"
                  step="1000"
                  value={simKm}
                  onChange={e => setSimKm(Number(e.target.value))}
                  className="w-full h-1.5 bg-surface-card rounded appearance-none cursor-pointer accent-brand-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1.5">
                  Market Price Shift: <strong className={simPriceShift >= 0 ? 'text-emerald-400 num-tabular' : 'text-rose-400 num-tabular'}>
                    {simPriceShift > 0 ? `+${simPriceShift}%` : `${simPriceShift}%`}
                  </strong>
                </label>
                <input
                  type="range"
                  min="-20"
                  max="20"
                  step="2"
                  value={simPriceShift}
                  onChange={e => setSimPriceShift(Number(e.target.value))}
                  className="w-full h-1.5 bg-surface-card rounded appearance-none cursor-pointer accent-brand-500"
                />
              </div>

              <div>
                <button
                  onClick={handleSimulate}
                  disabled={simulating}
                  className="w-full btn-primary text-xs flex items-center justify-center space-x-1.5 py-2.5"
                >
                  {simulating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  <span>Recalculate Lifecycle Decision</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

