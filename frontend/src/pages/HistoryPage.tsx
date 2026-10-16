import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  History as HistoryIcon,
  Trash2,
  GitCompare,
  PlusCircle,
  Search,
  ChevronLeft,
  ChevronRight,
  Gauge,
  MapPin,
  Calendar,
  Share2,
  AlertCircle,
  ArrowRight
} from 'lucide-react';
import { api, type SavedValuationSummary } from '../services/api';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage, getVerifiedVehicleImage } from '../components/VehicleImage';

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [valuations, setValuations] = useState<SavedValuationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchBrand, setSearchBrand] = useState('');
  const [searchModel, setSearchModel] = useState('');
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchHistory = async (targetPage: number = page) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getValuationHistory(targetPage, 10, searchBrand || undefined, searchModel || undefined);
      setValuations(res.items);
      setTotal(res.total);
      setPage(res.page);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve valuation history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(1);
  }, [searchBrand, searchModel]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this saved valuation snapshot?')) {
      return;
    }

    setDeletingId(id);
    try {
      await api.deleteSavedValuation(id);
      setSelectedForCompare((prev) => prev.filter((item) => item !== id));
      await fetchHistory(page);
    } catch (err: any) {
      alert(err.message || 'Failed to delete valuation.');
    } finally {
      setDeletingId(null);
    }
  };

  const toggleCompare = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare((prev) => prev.filter((item) => item !== id));
    } else {
      if (selectedForCompare.length >= 3) {
        alert('You can compare a maximum of 3 vehicles simultaneously.');
        return;
      }
      setSelectedForCompare((prev) => [...prev, id]);
    }
  };

  const handleLaunchCompare = () => {
    if (selectedForCompare.length < 2) {
      alert('Select at least 2 valuations to launch comparison matrix.');
      return;
    }
    const params = new URLSearchParams();
    selectedForCompare.forEach((id) => params.append('val', id));
    navigate(`/compare?${params.toString()}`);
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return 'N/A';
    if (val >= 10000000) return `₹ ${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹ ${(val / 100000).toFixed(2)} Lakh`;
    return `₹ ${val.toLocaleString('en-IN')}`;
  };

  return (
    <PageTransition className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#1c263c] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center space-x-2">
              <HistoryIcon className="w-6 h-6 text-sky-400" />
              <span>Valuation History</span>
            </h1>
            <span className="badge-neutral font-mono">
              {total} records
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Immutable valuation snapshots with saved model versions, residual coverage bounds, and peer evidence.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          {selectedForCompare.length >= 2 && (
            <button
              onClick={handleLaunchCompare}
              className="btn-secondary text-sky-300 border-sky-700 bg-sky-950/40"
            >
              <GitCompare className="w-3.5 h-3.5 text-sky-400" />
              <span>Compare Selected ({selectedForCompare.length})</span>
            </button>
          )}

          <Link
            to="/valuation"
            className="btn-primary"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Valuation</span>
          </Link>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Filter by Make (e.g. Hyundai, Honda, Maruti)..."
            value={searchBrand}
            onChange={(e) => setSearchBrand(e.target.value)}
            className="input-field pl-9 text-xs"
          />
        </div>
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Filter by Model (e.g. Creta, City, Swift)..."
            value={searchModel}
            onChange={(e) => setSearchModel(e.target.value)}
            className="input-field pl-9 text-xs"
          />
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </div>
          <button onClick={() => fetchHistory(page)} className="underline text-sky-400 font-medium cursor-pointer">
            Retry
          </button>
        </div>
      )}

      {/* Valuations List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-24 rounded-lg bg-[#0d1322] border border-[#1c263c] animate-pulse"></div>
          ))}
        </div>
      ) : valuations.length === 0 ? (
        <div className="card-surface p-12 text-center space-y-3">
          <HistoryIcon className="w-10 h-10 text-slate-600 mx-auto" />
          <div>
            <h3 className="text-sm font-semibold text-slate-200">No valuation records found</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              {searchBrand || searchModel
                ? 'No saved valuations match your current search criteria. Clear filters to see all entries.'
                : 'You have not saved any vehicle valuation snapshots yet. Run a valuation and select "Save Snapshot".'}
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
          {valuations.map((v) => {
            const isSelected = selectedForCompare.includes(v.id);
            return (
              <div
                key={v.id}
                onClick={() => navigate(`/valuation/${v.id}`)}
                className={`card-surface p-4 interactive-hover cursor-pointer transition-colors ${
                  isSelected ? 'border-sky-500 bg-[#11182c]' : ''
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Vehicle Spec & Metadata */}
                  <div className="flex items-start space-x-3.5">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      onClick={(e) => toggleCompare(v.id, e)}
                      title="Select for comparison matrix"
                      className="mt-1 w-4 h-4 rounded border-[#273553] bg-[#090e1a] text-sky-500 focus:ring-sky-500/40 cursor-pointer"
                    />

                    {getVerifiedVehicleImage(v.brand, v.model) && (
                      <VehicleImage
                        brand={v.brand}
                        model={v.model}
                        compact={true}
                        className="w-14 h-11 rounded-lg shrink-0 border border-[#1c263c]"
                      />
                    )}

                    <div>
                      <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span className="text-sm font-bold text-white group-hover:text-sky-300">
                          {v.year} {v.brand} {v.model}
                        </span>
                        {v.variant && (
                          <span className="text-[11px] text-slate-400 bg-[#090e1a] border border-[#1c263c] px-1.5 py-0.2 rounded font-mono">
                            {v.variant}
                          </span>
                        )}
                        <span className="text-[10px] font-mono text-slate-400 uppercase bg-[#090e1a] border border-[#1c263c] px-1.5 py-0.2 rounded">
                          {v.model_version}
                        </span>
                        {v.is_shared && (
                          <span className="badge-brand font-mono text-[10px] flex items-center space-x-1">
                            <Share2 className="w-2.5 h-2.5" />
                            <span>Shared</span>
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
                        {v.fuel_type && (
                          <>
                            <span>•</span>
                            <span>{v.fuel_type}</span>
                          </>
                        )}
                        {v.transmission && (
                          <>
                            <span>•</span>
                            <span>{v.transmission}</span>
                          </>
                        )}
                        <span>•</span>
                        <span className="flex items-center space-x-1">
                          <Calendar className="w-3.5 h-3.5 text-slate-500" />
                          <span>{new Date(v.created_at).toLocaleDateString()}</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Financial Values & Actions */}
                  <div className="flex items-center justify-between lg:justify-end space-x-6 border-t lg:border-t-0 pt-3 lg:pt-0 border-[#1c263c]">
                    <div className="text-left lg:text-right">
                      <div className="text-[11px] text-slate-400 font-medium">Estimated Value</div>
                      <div className="text-base font-bold text-white num-tabular">
                        {formatCurrency(v.estimated_value)}
                      </div>
                      <div className="text-[11px] text-slate-400 num-tabular">
                        80% Range:{' '}
                        {v.range_low && v.range_high
                          ? `${formatCurrency(v.range_low)} – ${formatCurrency(v.range_high)}`
                          : 'N/A'}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/valuation/${v.id}`);
                        }}
                        className="btn-ghost"
                        title="View formal valuation report"
                      >
                        View Report
                      </button>

                      <button
                        onClick={(e) => handleDelete(v.id, e)}
                        disabled={deletingId === v.id}
                        className="p-1.5 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/20 transition-colors cursor-pointer"
                        title="Delete snapshot record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-[#1c263c] text-xs text-slate-400">
          <div>
            Page <span className="font-semibold text-white num-tabular">{page}</span> of <span className="font-semibold text-white num-tabular">{totalPages}</span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              disabled={page <= 1}
              onClick={() => fetchHistory(page - 1)}
              className="btn-secondary px-2.5 py-1 disabled:opacity-30"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => fetchHistory(page + 1)}
              className="btn-secondary px-2.5 py-1 disabled:opacity-30"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </PageTransition>
  );
};
