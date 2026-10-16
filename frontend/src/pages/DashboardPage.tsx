import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Car,
  History,
  Bookmark,
  TrendingUp,
  PlusCircle,
  ArrowUpRight,
  ShieldCheck,
  Calendar,
  Gauge,
  MapPin,
  GitCompare,
  Cpu,
  ArrowRight
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { api, type SavedValuationSummary, type SavedVehicle } from '../services/api';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage, getVerifiedVehicleImage } from '../components/VehicleImage';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentValuations, setRecentValuations] = useState<SavedValuationSummary[]>([]);
  const [totalValuations, setTotalValuations] = useState(0);
  const [savedVehicles, setSavedVehicles] = useState<SavedVehicle[]>([]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [historyRes, vehiclesRes] = await Promise.all([
        api.getValuationHistory(1, 5),
        api.getSavedVehicles()
      ]);
      setRecentValuations(historyRes.items);
      setTotalValuations(historyRes.total);
      setSavedVehicles(vehiclesRes.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return 'N/A';
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} Lakh`;
    return `₹${val.toLocaleString('en-IN')}`;
  };

  return (
    <PageTransition className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#1c263c] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Portfolio Overview
            </h1>
            <span className="badge-emerald font-mono">
              Active Member
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Track saved valuations, bookmarked vehicle specifications, and pre-owned market intelligence for {user?.email}.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <Link
            to="/valuation"
            className="btn-primary"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Valuation</span>
          </Link>
          <Link
            to="/compare"
            className="btn-secondary"
          >
            <GitCompare className="w-3.5 h-3.5 text-slate-400" />
            <span>Compare Matrix</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex justify-between items-center">
          <span>{error}</span>
          <button onClick={fetchData} className="underline text-sky-400 font-medium cursor-pointer">
            Retry
          </button>
        </div>
      )}

      {/* KPI Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card-surface p-5 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Valuations</span>
            <History className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-white num-tabular tracking-tight">
            {loading ? <span className="text-slate-600">--</span> : totalValuations}
          </div>
          <p className="text-[11px] text-slate-400">Saved reports in account history</p>
        </div>

        <div className="card-surface p-5 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Saved Vehicles</span>
            <Bookmark className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-white num-tabular tracking-tight">
            {loading ? <span className="text-slate-600">--</span> : savedVehicles.length}
          </div>
          <p className="text-[11px] text-slate-400">Shortlisted vehicle benchmarks</p>
        </div>

        <div className="card-surface p-5 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Latest Valuation</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-white num-tabular tracking-tight">
            {loading ? (
              <span className="text-slate-600">--</span>
            ) : recentValuations.length > 0 ? (
              formatCurrency(recentValuations[0].estimated_value)
            ) : (
              '₹ 0'
            )}
          </div>
          <p className="text-[11px] text-slate-400 truncate">
            {recentValuations.length > 0
              ? `${recentValuations[0].year} ${recentValuations[0].brand} ${recentValuations[0].model}`
              : 'No valuations recorded'}
          </p>
        </div>

        <div className="card-surface p-5 space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Active ML Model</span>
            <Cpu className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-xl font-bold text-white font-mono tracking-tight">
            XGBoost v002
          </div>
          <p className="text-[11px] text-slate-400">Validated 93.68% R² • Conformal 80%</p>
        </div>
      </div>

      {/* Main Grid: Recent Valuations & Bookmarks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Valuations List */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between pb-1">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center space-x-2">
              <History className="w-4 h-4 text-sky-400" />
              <span>Recent Valuations</span>
            </h2>
            <Link 
              to="/history" 
              className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center space-x-1"
            >
              <span>View All ({totalValuations})</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {loading ? (
            <div className="space-y-2.5">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded-lg bg-[#0d1322] border border-[#1c263c] animate-pulse"></div>
              ))}
            </div>
          ) : recentValuations.length === 0 ? (
            <div className="card-surface p-10 text-center space-y-3">
              <Car className="w-8 h-8 text-slate-600 mx-auto" />
              <div>
                <h3 className="text-sm font-semibold text-slate-200">No valuations in portfolio</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                  Run a valuation for any used car to evaluate its market value, confidence interval, and comparable evidence.
                </p>
              </div>
              <Link
                to="/valuation"
                className="btn-primary"
              >
                <span>Value Your First Car</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <div className="space-y-2.5">
              {recentValuations.map((v) => (
                <div
                  key={v.id}
                  onClick={() => navigate(`/valuation/${v.id}`)}
                  className="card-surface p-4 interactive-hover cursor-pointer group"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      {getVerifiedVehicleImage(v.brand, v.model) && (
                        <VehicleImage
                          brand={v.brand}
                          model={v.model}
                          compact={true}
                          className="w-10 h-10 rounded shrink-0"
                        />
                      )}
                      <div className="min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-bold text-white group-hover:text-sky-300 transition-colors">
                            {v.year} {v.brand} {v.model}
                          </span>
                          {v.variant && (
                            <span className="text-[11px] text-slate-400 bg-[#090e1a] border border-[#1c263c] px-1.5 py-0.2 rounded font-mono">
                              {v.variant}
                            </span>
                          )}
                          {v.is_shared && (
                            <span className="badge-brand font-mono text-[10px]">
                              Shared
                            </span>
                          )}
                        </div>

                      <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1.5 flex-wrap gap-y-1">
                        <span className="flex items-center space-x-1">
                          <Gauge className="w-3.5 h-3.5 text-slate-500" />
                          <span className="num-tabular font-medium text-slate-300">{v.km_driven.toLocaleString('en-IN')} km</span>
                        </span>
                        <span>•</span>
                        <span className="flex items-center space-x-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-500" />
                          <span>{v.city}</span>
                        </span>
                        <span>•</span>
                        <span className="flex items-center space-x-1">
                          <Calendar className="w-3.5 h-3.5 text-slate-500" />
                          <span>{new Date(v.created_at).toLocaleDateString()}</span>
                        </span>
                      </div>
                    </div>
                  </div>

                    <div className="text-left sm:text-right">
                      <div className="text-base font-bold text-white num-tabular">
                        {formatCurrency(v.estimated_value)}
                      </div>
                      <div className="text-[11px] text-slate-400 num-tabular">
                        {v.range_low && v.range_high
                          ? `${formatCurrency(v.range_low)} – ${formatCurrency(v.range_high)}`
                          : 'Model Estimate'}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bookmarked Vehicles Quick View */}
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-1">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center space-x-2">
              <Bookmark className="w-4 h-4 text-amber-400" />
              <span>Bookmarked Cars</span>
            </h2>
            <Link
              to="/saved-vehicles"
              className="text-xs text-amber-400 hover:text-amber-300 font-medium flex items-center space-x-1"
            >
              <span>Manage ({savedVehicles.length})</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {loading ? (
            <div className="h-44 rounded-lg bg-[#0d1322] border border-[#1c263c] animate-pulse"></div>
          ) : savedVehicles.length === 0 ? (
            <div className="card-surface p-6 text-center space-y-2">
              <Bookmark className="w-6 h-6 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-300 font-medium">No bookmarks saved</p>
              <p className="text-[11px] text-slate-500">
                Bookmark interesting vehicle specifications from valuation results for rapid re-evaluation.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {savedVehicles.slice(0, 4).map((veh) => (
                <div key={veh.id} className="card-surface p-3.5 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-white">
                      {veh.year} {veh.brand} {veh.model}
                    </p>
                    <p className="text-[11px] text-slate-400 num-tabular">
                      {veh.km_driven.toLocaleString('en-IN')} km • {veh.city}
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      navigate(
                        `/valuation?brand=${encodeURIComponent(veh.brand)}&model=${encodeURIComponent(
                          veh.model
                        )}&year=${veh.year}&km=${veh.km_driven}&city=${encodeURIComponent(veh.city)}`
                      )
                    }
                    className="btn-ghost text-sky-400 hover:text-white px-2.5 py-1"
                  >
                    Value Now
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Privacy & Provenance card */}
          <div className="p-4 rounded-lg bg-[#0d1322] border border-[#1c263c] text-xs text-slate-400 space-y-1.5">
            <div className="flex items-center space-x-1.5 text-slate-200 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Snapshot Immutability</span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-400">
              Saved valuations preserve the exact model parameters, SHAP explanations, and market evidence medians recorded at the time of creation.
            </p>
          </div>
        </div>
      </div>
    </PageTransition>
  );
};
