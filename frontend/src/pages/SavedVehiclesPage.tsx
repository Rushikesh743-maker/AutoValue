import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bookmark,
  Trash2,
  PlusCircle,
  GitCompare,
  Gauge,
  MapPin,
  AlertCircle,
  ArrowRight
} from 'lucide-react';
import { api, type SavedVehicle } from '../services/api';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage, getVerifiedVehicleImage } from '../components/VehicleImage';

export const SavedVehiclesPage: React.FC = () => {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vehicles, setVehicles] = useState<SavedVehicle[]>([]);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ text: string; type: 'info' | 'error' } | null>(null);

  const fetchSavedVehicles = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSavedVehicles();
      setVehicles(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve saved vehicle bookmarks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSavedVehicles();
  }, []);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setNotification(null);
    try {
      await api.deleteSavedVehicle(id);
      setSelectedForCompare((prev) => prev.filter((item) => item !== id));
      await fetchSavedVehicles();
    } catch (err: any) {
      setNotification({ text: err.message || 'Failed to remove bookmark.', type: 'error' });
    } finally {
      setDeletingId(null);
    }
  };

  const toggleCompare = (id: string) => {
    setNotification(null);
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare((prev) => prev.filter((item) => item !== id));
    } else {
      if (selectedForCompare.length >= 3) {
        setNotification({ text: 'You can compare a maximum of 3 vehicles simultaneously.', type: 'info' });
        return;
      }
      setSelectedForCompare((prev) => [...prev, id]);
    }
  };

  const handleLaunchCompare = () => {
    if (selectedForCompare.length < 2) {
      setNotification({ text: 'Select at least 2 vehicles to launch comparison matrix.', type: 'info' });
      return;
    }
    const params = new URLSearchParams();
    selectedForCompare.forEach((id) => params.append('veh', id));
    navigate(`/compare?${params.toString()}`);
  };

  const handleRunValuation = (v: SavedVehicle) => {
    const params = new URLSearchParams({
      brand: v.brand,
      model: v.model,
      year: String(v.year),
      km: String(v.km_driven),
      city: v.city
    });
    if (v.variant) params.set('variant', v.variant);
    if (v.fuel_type) params.set('fuel_type', v.fuel_type);
    if (v.transmission) params.set('transmission', v.transmission);
    navigate(`/valuation?${params.toString()}`);
  };

  return (
    <PageTransition className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#1c263c] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center space-x-2">
              <Bookmark className="w-6 h-6 text-amber-400" />
              <span>Saved Vehicles</span>
            </h1>
            <span className="badge-neutral font-mono">
              {vehicles.length} bookmarked
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Vehicle configurations shortlisted for quick valuation reruns and multi-vehicle comparison.
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

          <button
            onClick={() => navigate('/valuation')}
            className="btn-primary"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Valuation</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </div>
          <button onClick={fetchSavedVehicles} className="underline text-sky-400 font-medium cursor-pointer">
            Retry
          </button>
        </div>
      )}

      {notification && (
        <div className={`p-3 rounded-lg text-xs flex justify-between items-center ${
          notification.type === 'error'
            ? 'bg-rose-950/40 border border-rose-800/60 text-rose-300'
            : 'bg-sky-950/40 border border-sky-800/60 text-sky-300'
        }`}>
          <span>{notification.text}</span>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-white ml-2 text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Grid of Saved Vehicles */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-lg bg-[#0d1322] border border-[#1c263c] animate-pulse"></div>
          ))}
        </div>
      ) : vehicles.length === 0 ? (
        <div className="card-surface p-12 text-center space-y-3">
          <Bookmark className="w-10 h-10 text-slate-600 mx-auto" />
          <div>
            <h3 className="text-sm font-semibold text-slate-200">No vehicles bookmarked</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Bookmark vehicle specifications from valuation results to keep a quick shortlist and run comparative analyses.
            </p>
          </div>
          <button
            onClick={() => navigate('/valuation')}
            className="btn-primary"
          >
            <span>Value a Vehicle</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {vehicles.map((veh) => {
            const isSelected = selectedForCompare.includes(veh.id);
            return (
              <div
                key={veh.id}
                className={`card-surface p-4 flex flex-col justify-between space-y-4 transition-colors ${
                  isSelected ? 'border-sky-500 bg-[#11182c]' : ''
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      {getVerifiedVehicleImage(veh.brand, veh.model) && (
                        <VehicleImage
                          brand={veh.brand}
                          model={veh.model}
                          compact={true}
                          className="w-12 h-12 rounded-lg shrink-0"
                        />
                      )}
                      <div className="min-w-0">
                        <h3 className="text-sm font-bold text-white truncate">
                          {veh.year} {veh.brand} {veh.model}
                        </h3>
                        {veh.variant && (
                          <p className="text-xs text-slate-400 mt-0.5 truncate">{veh.variant}</p>
                        )}
                      </div>
                    </div>

                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleCompare(veh.id)}
                      title="Select for comparison matrix"
                      className="mt-1 w-4 h-4 rounded border-[#273553] bg-[#090e1a] text-sky-500 focus:ring-sky-500/40 cursor-pointer shrink-0"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 mt-3 pt-3 border-t border-[#1c263c]">
                    <div className="flex items-center space-x-1.5">
                      <Gauge className="w-3.5 h-3.5 text-slate-500" />
                      <span className="num-tabular text-slate-300">{veh.km_driven.toLocaleString('en-IN')} km</span>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      <MapPin className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-slate-300">{veh.city}</span>
                    </div>

                    {veh.fuel_type && (
                      <div className="text-[11px] text-slate-400">
                        Fuel: <span className="text-slate-300">{veh.fuel_type}</span>
                      </div>
                    )}

                    {veh.transmission && (
                      <div className="text-[11px] text-slate-400">
                        Gearbox: <span className="text-slate-300">{veh.transmission}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-[#1c263c]">
                  <button
                    onClick={() => handleRunValuation(veh)}
                    className="btn-primary"
                  >
                    <span>Run Valuation</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => handleDelete(veh.id)}
                    disabled={deletingId === veh.id}
                    className="p-1.5 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/20 transition-colors cursor-pointer"
                    title="Remove vehicle bookmark"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </PageTransition>
  );
};
