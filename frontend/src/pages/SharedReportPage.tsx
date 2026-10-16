import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Gauge,
  MapPin,
  HelpCircle,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  FileText,
  Layers
} from 'lucide-react';
import { api, type SharedValuationResponse } from '../services/api';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage, getVerifiedVehicleImage } from '../components/VehicleImage';

export const SharedReportPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<SharedValuationResponse | null>(null);

  useEffect(() => {
    const fetchSharedReport = async () => {
      if (!token) return;
      setLoading(true);
      setError(null);
      try {
        const data = await api.getSharedReport(token);
        setReport(data);
      } catch (err: any) {
        setError(err.message || 'Shared report not found or link has expired.');
      } finally {
        setLoading(false);
      }
    };

    fetchSharedReport();
  }, [token]);

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return 'N/A';
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} Lakh`;
    return `₹${val.toLocaleString('en-IN')}`;
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-slate-400 font-mono uppercase tracking-wider">Loading verified snapshot report...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-md mx-auto px-4 py-20 text-center">
        <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-white">Report Unavailable</h2>
        <p className="text-xs text-slate-400 mt-1 mb-6">
          {error || 'This report link may have been revoked or does not exist.'}
        </p>
        <Link
          to="/valuation"
          className="btn-primary text-xs inline-flex items-center space-x-2"
        >
          <span>Calculate Free Valuation</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    );
  }

  const payload = report.payload;

  return (
    <PageTransition className="min-h-screen bg-surface-canvas py-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Banner */}
        <div className="p-3.5 rounded-lg bg-surface-card border border-surface-border flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="font-mono text-[11px] uppercase tracking-wider">Verified Snapshot • Read-Only Audit View</span>
          </div>
          <Link to="/valuation" className="text-brand-400 hover:text-brand-300 font-semibold flex items-center space-x-1 transition-colors">
            <span>Value Your Vehicle</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Main Snapshot Card */}
        <div className="card-surface p-6 sm:p-8">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
            <div className="flex flex-col sm:flex-row sm:items-start gap-5">
              {getVerifiedVehicleImage(report.brand, report.model) && (
                <div className="w-28 h-20 sm:w-36 sm:h-24 rounded-lg overflow-hidden border border-[#1c263c] shrink-0 bg-[#090d16]">
                  <VehicleImage
                    brand={report.brand}
                    model={report.model}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div>
                <div className="flex items-center space-x-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2">
                  <FileText className="w-3.5 h-3.5 text-brand-400" />
                  <span className="text-slate-300 font-semibold">AutoValue Verified Certificate</span>
                  <span>•</span>
                  <span>Engine: {report.model_version}</span>
                </div>

                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {report.year} {report.brand} {report.model}
                </h1>
                {report.variant && <p className="text-sm text-slate-400 mt-1 font-mono">{report.variant}</p>}

                <div className="flex items-center space-x-3 text-xs text-slate-400 mt-4 flex-wrap gap-y-2">
                  <span className="flex items-center space-x-1 text-slate-300">
                    <Gauge className="w-3.5 h-3.5 text-slate-500" />
                    <span className="num-tabular font-medium">{report.km_driven.toLocaleString('en-IN')} km</span>
                  </span>
                  <span className="text-slate-700">•</span>
                  <span className="flex items-center space-x-1 text-slate-300">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    <span>{report.city}</span>
                  </span>
                  <span className="text-slate-700">•</span>
                  <span className="text-slate-300">{report.fuel_type || 'Fuel N/A'}</span>
                  <span className="text-slate-700">•</span>
                  <span className="text-slate-300">{report.transmission || 'Transmission N/A'}</span>
                </div>
              </div>
            </div>

            <div className="p-5 rounded-xl bg-surface-canvas border border-surface-border text-left md:text-right min-w-[240px]">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">
                Estimated Market Value
              </span>
              <div className="text-3xl font-black text-white mt-1 num-tabular">
                {formatCurrency(report.estimated_value)}
              </div>
              <div className="text-xs text-slate-400 mt-1.5">
                Observed Range:{' '}
                <span className="text-slate-200 font-medium num-tabular">
                  {formatCurrency(report.range_low)} – {formatCurrency(report.range_high)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tripartite Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card-surface p-5 border-l-2 border-l-brand-500">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
              Model Point Estimate
            </span>
            <div className="text-xl font-bold text-white num-tabular">{formatCurrency(report.estimated_value)}</div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Algorithmic price estimation trained on verified marketplace transactions and historical asking data.
            </p>
          </div>

          <div className="card-surface p-5 border-l-2 border-l-emerald-500">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
              Market Median Evidence
            </span>
            <div className="text-xl font-bold text-emerald-400 num-tabular">{formatCurrency(report.market_median)}</div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Observed median asking price among comparable market listings in the region.
            </p>
          </div>

          <div className="card-surface p-5 border-l-2 border-l-indigo-400">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
              Conformal Interval (80%)
            </span>
            <div className="text-xl font-bold text-slate-100 num-tabular">
              {formatCurrency(report.model_interval_low)} – {formatCurrency(report.model_interval_high)}
            </div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Empirical prediction interval quantifying residual variance and market spread.
            </p>
          </div>
        </div>

        {/* SHAP Explanation */}
        {payload?.explanation && payload.explanation.length > 0 && (
          <div className="card-surface p-6">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-surface-border">
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                <Layers className="w-4 h-4 text-brand-400" />
                <span>Valuation Factor Attribution</span>
              </h3>
              <span className="text-[11px] text-slate-400">Marginal Price Impact</span>
            </div>

            <div className="space-y-2.5">
              {payload.explanation.map((item, idx) => {
                const isPositive = item.direction === 'increases_price' || item.impact_inr > 0;
                return (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-surface-canvas border border-surface-border flex items-center justify-between text-xs"
                  >
                    <span className="text-slate-300 font-medium">{item.human_readable_text}</span>
                    <span
                      className={`font-mono font-semibold px-2 py-0.5 rounded text-xs num-tabular ${
                        isPositive ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {isPositive ? '+' : ''}
                      {formatCurrency(item.impact_inr)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <div className="card-surface p-5 text-xs text-slate-400 space-y-2">
          <div className="flex items-center space-x-2 text-slate-300 font-semibold font-mono uppercase tracking-wider text-[11px]">
            <HelpCircle className="w-3.5 h-3.5 text-brand-400" />
            <span>Valuation Notice</span>
          </div>
          <p className="leading-relaxed">{report.disclaimer}</p>
        </div>
      </div>
    </PageTransition>
  );
};

