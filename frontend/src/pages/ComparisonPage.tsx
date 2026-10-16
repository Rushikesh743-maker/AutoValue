import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  GitCompare,
  Plus,
  AlertCircle,
  TrendingUp,
  Gauge,
  Calendar,
  Fuel,
  Settings,
  MapPin,
  HelpCircle,
  ArrowRight,
  X
} from 'lucide-react';
import { api, type ComparisonResponse, type SavedValuationSummary, type SavedVehicle, type ForecastResponse, type LifecycleDecision } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage } from '../components/VehicleImage';

export const ComparisonPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonData, setComparisonData] = useState<ComparisonResponse | null>(null);
  const [forecasts, setForecasts] = useState<Record<string, ForecastResponse | null>>({});
  const [forecastsLoading, setForecastsLoading] = useState(false);
  const [lifecycles, setLifecycles] = useState<Record<string, LifecycleDecision | null>>({});
  const [lifecyclesLoading, setLifecyclesLoading] = useState(false);

  // Selector modal states
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [availableValuations, setAvailableValuations] = useState<SavedValuationSummary[]>([]);
  const [availableVehicles, setAvailableVehicles] = useState<SavedVehicle[]>([]);

  const valuationIds = searchParams.getAll('val');
  const vehicleIds = searchParams.getAll('veh');

  const fetchComparison = async () => {
    if (valuationIds.length + vehicleIds.length < 2) {
      setComparisonData(null);
      setForecasts({});
      setLifecycles({});
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await api.compareVehicles(
        valuationIds.length > 0 ? valuationIds : undefined,
        vehicleIds.length > 0 ? vehicleIds : undefined
      );
      setComparisonData(res);

      setForecastsLoading(true);
      setLifecyclesLoading(true);
      const forecastMap: Record<string, ForecastResponse | null> = {};
      const lifecycleMap: Record<string, LifecycleDecision | null> = {};

      await Promise.all(
        res.vehicles.map(async (v) => {
          const vReq = {
            brand: v.brand,
            model: v.model,
            variant: v.variant || undefined,
            year: v.year,
            fuel_type: v.fuel_type || undefined,
            transmission: v.transmission || undefined,
            km_driven: v.km_driven,
            city: v.city,
            asking_price: v.asking_price || undefined
          };

          try {
            const fc = await api.getMarketForecast(vReq, 365);
            forecastMap[v.id] = fc;
          } catch {
            forecastMap[v.id] = null;
          }

          try {
            const lc = await api.postLifecycleDecision(vReq);
            lifecycleMap[v.id] = lc;
          } catch {
            lifecycleMap[v.id] = null;
          }
        })
      );
      setForecasts(forecastMap);
      setLifecycles(lifecycleMap);
    } catch (err: any) {
      setError(err.message || 'Failed to generate vehicle comparison matrix.');
    } finally {
      setLoading(false);
      setForecastsLoading(false);
      setLifecyclesLoading(false);
    }
  };

  useEffect(() => {
    fetchComparison();
  }, [searchParams]);

  const openItemSelector = async () => {
    setSelectorOpen(true);
    try {
      const [histRes, vehRes] = await Promise.all([
        api.getValuationHistory(1, 20),
        api.getSavedVehicles()
      ]);
      setAvailableValuations(histRes.items);
      setAvailableVehicles(vehRes.items);
    } catch {
      // Ignored
    }
  };

  const addItem = (type: 'val' | 'veh', id: string) => {
    const currentVals = searchParams.getAll('val');
    const currentVehs = searchParams.getAll('veh');
    if (currentVals.length + currentVehs.length >= 3) {
      alert('Comparison matrix is limited to 3 vehicles.');
      return;
    }

    const newParams = new URLSearchParams(searchParams);
    newParams.append(type, id);
    setSearchParams(newParams);
    setSelectorOpen(false);
  };

  const removeItem = (type: 'val' | 'veh', id: string) => {
    const newParams = new URLSearchParams();
    searchParams.getAll('val').forEach((val) => {
      if (!(type === 'val' && val === id)) newParams.append('val', val);
    });
    searchParams.getAll('veh').forEach((veh) => {
      if (!(type === 'veh' && veh === id)) newParams.append('veh', veh);
    });
    setSearchParams(newParams);
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return 'N/A';
    if (val >= 10000000) return `₹ ${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹ ${(val / 100000).toFixed(2)} Lakh`;
    return `₹ ${val.toLocaleString('en-IN')}`;
  };

  const totalSelected = valuationIds.length + vehicleIds.length;
  const shouldReduceMotion = useReducedMotion();

  return (
    <PageTransition className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#1c263c] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center space-x-2">
              <GitCompare className="w-6 h-6 text-sky-400" />
              <span>Vehicle Comparison Matrix</span>
            </h1>
            <span className="badge-neutral font-mono">
              {totalSelected}/3 Selected
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Empirical side-by-side analysis highlighting model valuations, market medians, and lifecycle costs.
          </p>
        </div>

        {isAuthenticated && totalSelected < 3 && (
          <button
            onClick={openItemSelector}
            className="btn-primary self-start md:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Vehicle to Matrix</span>
          </button>
        )}
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Comparison Matrix or Empty Picker */}
      {totalSelected < 2 ? (
        <div className="card-surface p-12 text-center max-w-lg mx-auto my-6 space-y-4">
          <GitCompare className="w-10 h-10 text-slate-600 mx-auto" />
          <div>
            <h2 className="text-base font-semibold text-white">Select Vehicles to Compare</h2>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Select 2 or 3 saved vehicle valuations or bookmarked cars to inspect side-by-side deltas across valuations, odometer readings, and ownership costs.
            </p>
          </div>

          {isAuthenticated ? (
            <button
              onClick={openItemSelector}
              className="btn-primary"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Select from Portfolio</span>
            </button>
          ) : (
            <div className="space-y-2 pt-2">
              <p className="text-xs text-slate-400">Sign in to select vehicles from your valuation history</p>
              <Link
                to="/login"
                className="btn-primary"
              >
                <span>Sign In to Compare</span>
              </Link>
            </div>
          )}
        </div>
      ) : loading ? (
        <div className="space-y-4">
          <div className="h-44 rounded-lg bg-[#0d1322] border border-[#1c263c] animate-pulse"></div>
          <div className="h-64 rounded-lg bg-[#0d1322] border border-[#1c263c] animate-pulse"></div>
        </div>
      ) : comparisonData ? (
        <div className="space-y-6">
          {/* Factual Highlights Box */}
          <div className="card-surface p-5 space-y-3">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-sky-400" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                Empirical Differences & Variance Analysis
              </h3>
            </div>
            <p className="text-xs text-slate-400">{comparisonData.factual_summary}</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              {comparisonData.empirical_differences.map((delta, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-[#090e1a] border border-[#1c263c]">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-sky-400 block mb-0.5">
                    {delta.metric}
                  </span>
                  <p className="text-xs text-slate-200 leading-snug">{delta.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Side-by-Side Comparison Columns */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {comparisonData.vehicles.map((veh, i) => (
              <div
                key={veh.id}
                className="card-surface p-5 flex flex-col justify-between space-y-5"
              >
                <div>
                  <div className="flex items-center justify-between pb-3 border-b border-[#1c263c]">
                    <span className="badge-neutral font-mono text-[10px]">
                      Vehicle #{i + 1}
                    </span>

                    <button
                      onClick={() =>
                        removeItem(veh.source_type === 'saved_valuation' ? 'val' : 'veh', veh.id)
                      }
                      className="text-xs text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                    >
                      Remove
                    </button>
                  </div>

                  {/* Consistent Image Area with matching dimensions and crop behavior */}
                  <div className="pt-3 pb-1">
                    <VehicleImage
                      brand={veh.brand}
                      model={veh.model}
                      variant={veh.variant}
                      year={veh.year}
                      aspectRatio="16/9"
                      className="w-full"
                    />
                  </div>

                  <div className="pt-2">
                    <h3 className="text-base font-bold text-white">
                      {veh.year} {veh.brand} {veh.model}
                    </h3>
                    {veh.variant && <p className="text-xs text-slate-400 mt-0.5">{veh.variant}</p>}
                  </div>

                  {/* Valuation Highlight */}
                  <div className="my-4 p-4 rounded-lg bg-[#090e1a] border border-[#1c263c] space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">
                      Estimated Market Value
                    </span>
                    <div className="text-2xl font-bold text-white num-tabular">
                      {formatCurrency(veh.estimated_value)}
                    </div>
                    {veh.range_low && veh.range_high && (
                      <div className="text-[11px] text-slate-400 num-tabular">
                        80% Range: {formatCurrency(veh.range_low)} – {formatCurrency(veh.range_high)}
                      </div>
                    )}
                    {veh.market_median && (
                      <div className="text-[11px] text-slate-400 num-tabular">
                        Market Median: {formatCurrency(veh.market_median)}
                      </div>
                    )}
                  </div>

                  {/* Attributes Matrix */}
                  <div className="space-y-2 text-xs divide-y divide-[#1c263c]">
                    <div className="flex items-center justify-between py-1.5">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <Gauge className="w-3.5 h-3.5 text-slate-500" />
                        <span>Odometer</span>
                      </span>
                      <span className="font-semibold text-slate-200 num-tabular">
                        {veh.km_driven.toLocaleString('en-IN')} km
                      </span>
                    </div>

                    <div className="flex items-center justify-between py-1.5">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        <span>Model Year</span>
                      </span>
                      <span className="font-semibold text-slate-200 num-tabular">{veh.year}</span>
                    </div>

                    <div className="flex items-center justify-between py-1.5">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <Fuel className="w-3.5 h-3.5 text-slate-500" />
                        <span>Powertrain</span>
                      </span>
                      <span className="font-semibold text-slate-200">{veh.fuel_type || 'N/A'}</span>
                    </div>

                    <div className="flex items-center justify-between py-1.5">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <Settings className="w-3.5 h-3.5 text-slate-500" />
                        <span>Transmission</span>
                      </span>
                      <span className="font-semibold text-slate-200">{veh.transmission || 'N/A'}</span>
                    </div>

                    <div className="flex items-center justify-between py-1.5">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-500" />
                        <span>City / Region</span>
                      </span>
                      <span className="font-semibold text-slate-200">{veh.city}</span>
                    </div>

                    {veh.asking_price && (
                      <div className="flex items-center justify-between py-1.5">
                        <span className="text-slate-400">Asking Price</span>
                        <span className="font-semibold text-slate-200 num-tabular">
                          {formatCurrency(veh.asking_price)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* 5Y Ownership Economics Section */}
                  <div className="mt-4 p-3 rounded-lg bg-[#090e1a] border border-[#1c263c] space-y-1.5 text-xs">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                      5-Year Ownership Economics
                    </span>
                    <div className="flex items-center justify-between py-0.5">
                      <span className="text-slate-400">Net 5Y Cost:</span>
                      <span className="font-bold text-white num-tabular">
                        {veh.estimated_value ? formatCurrency((veh.estimated_value * 1.55) - (veh.estimated_value * 0.69)) : 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5">
                      <span className="text-slate-400">Est. Resale (Y5):</span>
                      <span className="font-semibold text-sky-300 num-tabular">
                        {veh.estimated_value ? formatCurrency(veh.estimated_value * 0.69) : 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5">
                      <span className="text-slate-400">Cost / km:</span>
                      <span className="font-semibold text-amber-300 num-tabular">
                        {veh.estimated_value ? `₹ ${(Math.round(((veh.estimated_value * 1.55) - (veh.estimated_value * 0.69)) / 60000 * 100) / 100).toFixed(2)}/km` : 'N/A'}
                      </span>
                    </div>
                  </div>

                  {/* Market Forecast & Timing */}
                  <div className="mt-3 p-3 rounded-lg bg-[#090e1a] border border-[#1c263c] space-y-1.5 text-xs">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                      1-Year Market Forecast
                    </span>
                    <div className="flex items-center justify-between py-0.5">
                      <span className="text-slate-400">Market Direction:</span>
                      <span className={`font-semibold ${
                        forecasts[veh.id]?.overall_trend === 'RISING'
                          ? 'text-emerald-400'
                          : forecasts[veh.id]?.overall_trend === 'DECLINING'
                          ? 'text-rose-400'
                          : 'text-sky-400'
                      }`}>
                        {forecastsLoading ? '...' : (forecasts[veh.id]?.overall_trend || 'STABLE')}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5">
                      <span className="text-slate-400">90D Momentum:</span>
                      <span className={`font-semibold num-tabular ${
                        (forecasts[veh.id]?.momentum?.m90d?.price_change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}>
                        {forecastsLoading
                          ? '...'
                          : forecasts[veh.id]?.momentum?.m90d?.price_change_pct !== undefined && forecasts[veh.id]?.momentum?.m90d?.price_change_pct !== null
                          ? `${forecasts[veh.id]!.momentum.m90d.price_change_pct! >= 0 ? '+' : ''}${forecasts[veh.id]!.momentum.m90d.price_change_pct}%`
                          : '—'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5">
                      <span className="text-slate-400">1Y Forecast:</span>
                      <span className="font-semibold text-white num-tabular">
                        {forecastsLoading ? '...' : (forecasts[veh.id]?.forecast_points?.find(p => p.horizon_days === 365)?.base_formatted || '—')}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5 pt-1 border-t border-slate-800">
                      <span className="text-slate-400">Lifecycle Action:</span>
                      <span className="font-semibold text-sky-400">
                        {lifecyclesLoading ? '...' : (lifecycles[veh.id]?.recommended_action?.replace(/_/g, ' ') || 'HOLD')}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-[#1c263c]">
                  {veh.source_type === 'saved_valuation' ? (
                    <Link
                      to={`/valuation/${veh.id}`}
                      className="btn-secondary w-full"
                    >
                      <span>View Full Report</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  ) : (
                    <Link
                      to={`/valuation?brand=${encodeURIComponent(veh.brand)}&model=${encodeURIComponent(
                        veh.model
                      )}&year=${veh.year}&km=${veh.km_driven}&city=${encodeURIComponent(veh.city)}`}
                      className="btn-primary w-full"
                    >
                      <span>Calculate Valuation</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Objective Methodology Notice */}
          <div className="p-3.5 rounded-lg border border-[#1c263c] bg-[#0d1322] text-xs text-slate-400 flex items-start space-x-2">
            <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-500" />
            <p>
              AutoValue comparison is strictly empirical. We provide objective model-derived valuation deltas, odometer differences, and ownership economics without declaring subjective winners.
            </p>
          </div>
        </div>
      ) : null}

      {/* Item Selector Modal */}
      <AnimatePresence>
        {selectorOpen && (
          <div className="fixed inset-0 z-50 bg-[#090d16]/80 backdrop-blur-sm flex items-center justify-center p-4">
            <motion.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.96 }}
              transition={{ duration: shouldReduceMotion ? 0 : 0.18, ease: 'easeOut' }}
              className="card-surface max-w-xl w-full p-6 border-[#273553] shadow-2xl max-h-[80vh] flex flex-col"
            >
              <div className="flex items-center justify-between pb-3 border-b border-[#1c263c]">
                <h3 className="text-sm font-bold text-white">Add Vehicle to Comparison Matrix</h3>
                <button
                  onClick={() => setSelectorOpen(false)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="overflow-y-auto py-4 space-y-5 flex-1">
                {/* Valuations */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                    Saved Valuation Snapshots
                  </h4>
                  {availableValuations.length === 0 ? (
                    <p className="text-xs text-slate-500">No saved valuations available.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {availableValuations.map((v) => (
                        <div
                          key={v.id}
                          className="p-3 rounded-lg bg-[#090e1a] border border-[#1c263c] flex items-center justify-between hover:border-[#273553] transition-colors"
                        >
                          <div>
                            <p className="text-xs font-bold text-white">
                              {v.year} {v.brand} {v.model}
                            </p>
                            <p className="text-[11px] text-slate-400 num-tabular">
                              {formatCurrency(v.estimated_value)} • {v.km_driven.toLocaleString('en-IN')} km • {v.city}
                            </p>
                          </div>
                          <button
                            onClick={() => addItem('val', v.id)}
                            className="btn-primary py-1 px-3"
                          >
                            Select
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Saved Vehicles */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                    Bookmarked Vehicles
                  </h4>
                  {availableVehicles.length === 0 ? (
                    <p className="text-xs text-slate-500">No bookmarked vehicles available.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {availableVehicles.map((veh) => (
                        <div
                          key={veh.id}
                          className="p-3 rounded-lg bg-[#090e1a] border border-[#1c263c] flex items-center justify-between hover:border-[#273553] transition-colors"
                        >
                          <div>
                            <p className="text-xs font-bold text-white">
                              {veh.year} {veh.brand} {veh.model}
                            </p>
                            <p className="text-[11px] text-slate-400 num-tabular">
                              {veh.km_driven.toLocaleString('en-IN')} km • {veh.city}
                            </p>
                          </div>
                          <button
                            onClick={() => addItem('veh', veh.id)}
                            className="btn-secondary py-1 px-3"
                          >
                            Select
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </PageTransition>
  );
};
