import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Car,
  Share2,
  Copy,
  Check,
  Calendar,
  Gauge,
  MapPin,
  HelpCircle,
  ArrowLeft,
  ShieldAlert,
  Printer,
  FileText,
  Layers
} from 'lucide-react';
import { api, type SavedValuationDetail } from '../services/api';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage, getVerifiedVehicleImage } from '../components/VehicleImage';

export const ValuationReportPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [valuation, setValuation] = useState<SavedValuationDetail | null>(null);

  // Sharing states
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const [shareToken, setShareToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchValuation = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSavedValuationById(id);
      setValuation(data);
      if (data.is_shared && data.share_token) {
        setShareToken(data.share_token);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load valuation report.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchValuation();
  }, [id]);

  const handleCreateShare = async () => {
    if (!id) return;
    setShareLoading(true);
    try {
      const res = await api.shareValuation(id);
      setShareToken(res.share_token);
      setValuation((prev) => (prev ? { ...prev, is_shared: true, share_token: res.share_token } : null));
    } catch (err: any) {
      alert(err.message || 'Failed to generate share link.');
    } finally {
      setShareLoading(false);
    }
  };

  const handleRevokeShare = async () => {
    if (!id) return;
    setShareLoading(true);
    try {
      await api.revokeValuationShare(id);
      setShareToken(null);
      setValuation((prev) => (prev ? { ...prev, is_shared: false, share_token: undefined } : null));
      alert('Public sharing has been revoked.');
    } catch (err: any) {
      alert(err.message || 'Failed to revoke sharing.');
    } finally {
      setShareLoading(false);
    }
  };

  const copyShareLink = () => {
    if (!shareToken) return;
    const url = `${window.location.origin}/shared/${shareToken}`;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return 'N/A';
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} Lakh`;
    return `₹${val.toLocaleString('en-IN')}`;
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-20 text-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-slate-400 font-mono uppercase tracking-wider">Loading immutable valuation snapshot...</p>
      </div>
    );
  }

  if (error || !valuation) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-white">Valuation Report Unavailable</h2>
        <p className="text-xs text-slate-400 mt-1 mb-6">{error || 'Could not find the requested record.'}</p>
        <Link
          to="/history"
          className="btn-secondary text-xs inline-flex items-center space-x-2"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Valuation History</span>
        </Link>
      </div>
    );
  }

  const payload = valuation.payload;

  return (
    <PageTransition className="min-h-screen bg-surface-canvas py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Top Navigation & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
          <Link
            to="/history"
            className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Valuation History</span>
          </Link>

          <div className="flex items-center space-x-2.5">
            <button
              onClick={() => window.print()}
              className="btn-secondary text-xs flex items-center space-x-1.5"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Snapshot</span>
            </button>

            <button
              onClick={() => {
                if (!shareToken) handleCreateShare();
                setShareModalOpen(true);
              }}
              className="btn-primary text-xs flex items-center space-x-1.5"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>{valuation.is_shared ? 'Share Active' : 'Share Snapshot'}</span>
            </button>
          </div>
        </div>

        {/* Hero Header */}
        <div className="card-surface p-6 sm:p-8">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
            <div className="flex flex-col sm:flex-row sm:items-start gap-5">
              {getVerifiedVehicleImage(valuation.brand, valuation.model) && (
                <div className="w-28 h-20 sm:w-36 sm:h-24 rounded-lg overflow-hidden border border-[#1c263c] shrink-0 bg-[#090d16]">
                  <VehicleImage
                    brand={valuation.brand}
                    model={valuation.model}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div>
                <div className="flex items-center space-x-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2">
                  <FileText className="w-3.5 h-3.5 text-brand-400" />
                  <span className="text-slate-300 font-semibold">Snapshot Certificate</span>
                  <span>•</span>
                  <span>Model Engine: {valuation.model_version}</span>
                </div>

                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {valuation.year} {valuation.brand} {valuation.model}
                </h1>
                {valuation.variant && <p className="text-sm text-slate-400 mt-1 font-mono">{valuation.variant}</p>}

              <div className="flex items-center space-x-3 text-xs text-slate-400 mt-4 flex-wrap gap-y-2">
                <span className="flex items-center space-x-1 text-slate-300">
                  <Gauge className="w-3.5 h-3.5 text-slate-500" />
                  <span className="num-tabular font-medium">{valuation.km_driven.toLocaleString('en-IN')} km</span>
                </span>
                <span className="text-slate-700">•</span>
                <span className="flex items-center space-x-1 text-slate-300">
                  <MapPin className="w-3.5 h-3.5 text-slate-500" />
                  <span>{valuation.city}</span>
                </span>
                <span className="text-slate-700">•</span>
                <span className="text-slate-300">{valuation.fuel_type || 'Fuel N/A'}</span>
                <span className="text-slate-700">•</span>
                <span className="text-slate-300">{valuation.transmission || 'Transmission N/A'}</span>
                <span className="text-slate-700">•</span>
                <span className="flex items-center space-x-1 text-slate-400">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  <span>Certified on {new Date(valuation.created_at).toLocaleDateString()}</span>
                </span>
              </div>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-surface-canvas border border-surface-border text-left md:text-right min-w-[240px]">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">
                Estimated Market Value
              </span>
              <div className="text-3xl font-black text-white mt-1 num-tabular">
                {formatCurrency(valuation.estimated_value)}
              </div>
              <div className="text-xs text-slate-400 mt-1.5">
                Observed Range:{' '}
                <span className="text-slate-200 font-medium num-tabular">
                  {formatCurrency(valuation.range_low)} – {formatCurrency(valuation.range_high)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tripartite Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card-surface p-5 border-l-2 border-l-brand-500">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
              1. Model Point Estimate
            </span>
            <div className="text-xl font-bold text-white num-tabular">{formatCurrency(valuation.estimated_value)}</div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Supervised gradient boosted regression (XGBoost) trained on cleaned automotive marketplace listings.
            </p>
          </div>

          <div className="card-surface p-5 border-l-2 border-l-emerald-500">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
              2. Observed Market Evidence
            </span>
            <div className="text-xl font-bold text-emerald-400 num-tabular">
              {formatCurrency(valuation.market_median)}
            </div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Empirical median asking price from {valuation.comparable_count} comparable listings observed across sources.
            </p>
          </div>

          <div className="card-surface p-5 border-l-2 border-l-indigo-400">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
              3. Conformal Prediction Interval
            </span>
            <div className="text-xl font-bold text-slate-100 num-tabular">
              {formatCurrency(valuation.model_interval_low)} – {formatCurrency(valuation.model_interval_high)}
            </div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              80% empirical conformal prediction interval quantifying residual pricing uncertainty.
            </p>
          </div>
        </div>

        {/* SHAP Explanation Top Factors */}
        {payload?.explanation && payload.explanation.length > 0 && (
          <div className="card-surface p-6">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-surface-border">
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                <Layers className="w-4 h-4 text-brand-400" />
                <span>Feature Attribution (SHAP Analysis)</span>
              </h3>
              <span className="text-[11px] text-slate-400">Marginal INR Price Impact</span>
            </div>

            <div className="space-y-2.5">
              {payload.explanation.map((item, idx) => {
                const isPositive = item.direction === 'increases_price' || item.impact_inr > 0;
                return (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-surface-canvas border border-surface-border flex items-center justify-between text-xs"
                  >
                    <div>
                      <span className="font-semibold text-slate-200">{item.feature}</span>
                      <p className="text-[11px] text-slate-400 mt-0.5">{item.human_readable_text}</p>
                    </div>
                    <div
                      className={`font-mono font-semibold px-2 py-1 rounded text-xs num-tabular ${
                        isPositive ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {isPositive ? '+' : ''}
                      {formatCurrency(item.impact_inr)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Comparable Listings Snapshot */}
        {payload?.comparables && payload.comparables.length > 0 && (
          <div className="card-surface p-6">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-surface-border">
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                <Car className="w-4 h-4 text-brand-400" />
                <span>Observed Comparable Listings ({payload.comparables.length})</span>
              </h3>
              <span className="text-[11px] text-slate-400">Market Benchmark Evidence</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-surface-canvas text-slate-400 font-mono uppercase tracking-wider border-b border-surface-border text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Vehicle Specification</th>
                    <th className="py-2.5 px-3">Year / Mileage</th>
                    <th className="py-2.5 px-3">Location</th>
                    <th className="py-2.5 px-3">Source Feed</th>
                    <th className="py-2.5 px-3 text-right">Asking Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border font-mono">
                  {payload.comparables.map((c, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-2.5 px-3 font-sans font-medium text-white">
                        {c.brand} {c.model} {c.variant}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 num-tabular">
                        {c.year} • {c.km_driven?.toLocaleString('en-IN')} km
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">{c.city || 'N/A'}</td>
                      <td className="py-2.5 px-3 text-slate-400">{c.source}</td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-100 num-tabular">
                        {c.listed_price_formatted}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Limitations & Disclaimer */}
        <div className="card-surface p-5 text-xs text-slate-400 space-y-2">
          <div className="flex items-center space-x-2 text-slate-300 font-semibold font-mono uppercase tracking-wider text-[11px]">
            <HelpCircle className="w-3.5 h-3.5 text-brand-400" />
            <span>Valuation Methodology & Disclaimers</span>
          </div>
          <p className="leading-relaxed">
            AutoValue estimates are empirical algorithmic valuations derived from active and historical market asking prices. They do not constitute certified appraisals, mechanical condition guarantees, or firm transaction commitments. Final transaction prices are subject to physical inspection, vehicle maintenance records, and mutual negotiation.
          </p>
        </div>

        {/* Share Modal */}
        {shareModalOpen && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="card-elevated max-w-md w-full p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <Share2 className="w-4 h-4 text-brand-400" />
                  <span>Share Valuation Report</span>
                </h3>
                <button
                  onClick={() => setShareModalOpen(false)}
                  className="text-slate-400 hover:text-white text-xs font-mono px-2 py-1"
                >
                  Close
                </button>
              </div>

              <div className="space-y-4 text-xs">
                <p className="text-slate-400 leading-relaxed">
                  Anyone with this public URL can view a read-only, sanitized summary of this valuation. Account details and personal information are strictly excluded.
                </p>

                {shareToken ? (
                  <div className="space-y-3">
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        readOnly
                        value={`${window.location.origin}/shared/${shareToken}`}
                        className="input-field text-xs text-slate-200 font-mono py-2"
                      />
                      <button
                        onClick={copyShareLink}
                        className="btn-primary text-xs px-3 py-2 flex items-center space-x-1"
                      >
                        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copied ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>

                    <div className="pt-2 flex items-center justify-between">
                      <span className="text-[11px] text-emerald-400 font-mono">● Link active & verified</span>
                      <button
                        disabled={shareLoading}
                        onClick={handleRevokeShare}
                        className="text-xs text-rose-400 hover:underline disabled:opacity-50"
                      >
                        Revoke Access
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    disabled={shareLoading}
                    onClick={handleCreateShare}
                    className="w-full btn-primary py-2.5 text-xs font-semibold disabled:opacity-50"
                  >
                    {shareLoading ? 'Generating Link...' : 'Create Public Share Link'}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  );
};

