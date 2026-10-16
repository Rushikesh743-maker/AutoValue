import React, { useState, useEffect } from 'react';
import {
  Car,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  Plus,
  Trash2,
  Edit2,
  RefreshCw,
  Scale,
  CheckCircle2,
  AlertTriangle,
  Info,
  Sliders,
  PieChart,
  Repeat,
  X
} from 'lucide-react';
import {
  api,
  type GarageVehicle,
  type GarageVehicleCreate,
  type GarageVehicleUpdate,
  type GarageVehicleSnapshot,
  type GarageIntelligenceResponse,
  type GarageScenarioResponse,
  type GarageCompareResponse,
  type OwnershipStatus,
  type GarageScenarioActionType
} from '../services/api';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage, getVerifiedVehicleImage } from '../components/VehicleImage';

export const GaragePage: React.FC = () => {
  const [intelligence, setIntelligence] = useState<GarageIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Drawers
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [editingVehicle, setEditingVehicle] = useState<GarageVehicle | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<GarageVehicleSnapshot | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareResult, setCompareResult] = useState<GarageCompareResponse | null>(null);
  const [comparing, setComparing] = useState<boolean>(false);

  // Scenario Simulator State
  const [showScenarioModal, setShowScenarioModal] = useState<boolean>(false);
  const [scenarioActionType, setScenarioActionType] = useState<GarageScenarioActionType>('SELL');
  const [scenarioTargetVehicleId, setScenarioTargetVehicleId] = useState<string>('');
  const [scenarioAnnualKmOverride, setScenarioAnnualKmOverride] = useState<number>(10000);
  const [scenarioReplacementBrand, setScenarioReplacementBrand] = useState<string>('Honda');
  const [scenarioReplacementModel, setScenarioReplacementModel] = useState<string>('City');
  const [scenarioReplacementYear, setScenarioReplacementYear] = useState<number>(2022);
  const [scenarioReplacementPrice, setScenarioReplacementPrice] = useState<number>(1100000);
  const [scenarioResult, setScenarioResult] = useState<GarageScenarioResponse | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);

  // Add / Edit Form State
  const [formData, setFormData] = useState<GarageVehicleCreate>({
    brand: 'Hyundai',
    model: 'Creta',
    variant: '1.5 CRDi SX',
    year: 2021,
    fuel_type: 'Diesel',
    transmission: 'Manual',
    city: 'Bengaluru',
    nickname: 'Primary SUV',
    ownership_status: 'OWNED',
    purchase_price: 1350000,
    current_odometer: 38000,
    annual_km: 14000,
    ownership_purpose: 'Daily Commute & Highway Trips',
    notes: 'Bought certified pre-owned'
  });

  const fetchGarageIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getGarageIntelligence();
      setIntelligence(data);
      if (data?.snapshots && data.snapshots.length > 0 && !scenarioTargetVehicleId) {
        setScenarioTargetVehicleId(data.snapshots[0].vehicle.id);
      }
    } catch (err: any) {
      console.error('Failed to load garage intelligence:', err);
      setError(err.message || 'Unable to load garage intelligence. Please ensure you are logged in.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGarageIntelligence();
  }, []);

  const handleCreateVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createGarageVehicle(formData);
      setShowAddModal(false);
      fetchGarageIntelligence();
    } catch (err: any) {
      alert(`Failed to add vehicle: ${err.message || 'Unknown error'}`);
    }
  };

  const handleUpdateVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingVehicle) return;
    try {
      const updates: GarageVehicleUpdate = {
        brand: formData.brand,
        model: formData.model,
        variant: formData.variant,
        year: formData.year,
        fuel_type: formData.fuel_type,
        transmission: formData.transmission,
        city: formData.city,
        nickname: formData.nickname,
        ownership_status: formData.ownership_status,
        purchase_price: formData.purchase_price,
        current_odometer: formData.current_odometer,
        annual_km: formData.annual_km,
        ownership_purpose: formData.ownership_purpose,
        notes: formData.notes
      };
      await api.updateGarageVehicle(editingVehicle.id, updates);
      setEditingVehicle(null);
      fetchGarageIntelligence();
    } catch (err: any) {
      alert(`Failed to update vehicle: ${err.message || 'Unknown error'}`);
    }
  };

  const handleDeleteVehicle = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to remove "${name}" from your garage?`)) return;
    try {
      await api.deleteGarageVehicle(id);
      setCompareIds(prev => prev.filter(item => item !== id));
      fetchGarageIntelligence();
    } catch (err: any) {
      alert(`Failed to remove vehicle: ${err.message || 'Unknown error'}`);
    }
  };

  const toggleCompareSelection = (id: string) => {
    if (compareIds.includes(id)) {
      setCompareIds(compareIds.filter(i => i !== id));
    } else {
      if (compareIds.length >= 10) {
        alert('You can compare a maximum of 10 vehicles.');
        return;
      }
      setCompareIds([...compareIds, id]);
    }
  };

  const handleRunCompare = async () => {
    if (compareIds.length < 2) {
      alert('Please select at least 2 vehicles to compare.');
      return;
    }
    setComparing(true);
    try {
      const res = await api.compareGarageVehicles(compareIds);
      setCompareResult(res);
    } catch (err: any) {
      alert(`Comparison failed: ${err.message}`);
    } finally {
      setComparing(false);
    }
  };

  const handleSimulateScenario = async () => {
    if (!scenarioTargetVehicleId && scenarioActionType !== 'ADD') {
      alert('Please select a target vehicle for the scenario.');
      return;
    }
    setSimulating(true);
    try {
      const actions: any[] = [];
      if (scenarioActionType === 'SELL') {
        actions.push({
          vehicle_id: scenarioTargetVehicleId,
          action_type: 'SELL'
        });
      } else if (scenarioActionType === 'REPLACE') {
        actions.push({
          vehicle_id: scenarioTargetVehicleId,
          action_type: 'REPLACE',
          replacement_vehicle: {
            brand: scenarioReplacementBrand,
            model: scenarioReplacementModel,
            year: scenarioReplacementYear,
            purchase_price: scenarioReplacementPrice,
            annual_km: scenarioAnnualKmOverride
          }
        });
      } else if (scenarioActionType === 'UPDATE_MILEAGE') {
        actions.push({
          vehicle_id: scenarioTargetVehicleId,
          action_type: 'UPDATE_MILEAGE',
          annual_km_override: scenarioAnnualKmOverride
        });
      } else if (scenarioActionType === 'ADD') {
        actions.push({
          vehicle_id: 'new_vehicle',
          action_type: 'ADD',
          replacement_vehicle: {
            brand: scenarioReplacementBrand,
            model: scenarioReplacementModel,
            year: scenarioReplacementYear,
            purchase_price: scenarioReplacementPrice,
            annual_km: scenarioAnnualKmOverride
          }
        });
      }
      const res = await api.simulateGarageScenario({ actions, ownership_horizon_years: 5 });
      setScenarioResult(res);
    } catch (err: any) {
      alert(`Simulation failed: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const openEditModal = (vehicle: GarageVehicle) => {
    setEditingVehicle(vehicle);
    setFormData({
      brand: vehicle.brand,
      model: vehicle.model,
      variant: vehicle.variant || '',
      year: vehicle.year,
      fuel_type: vehicle.fuel_type || 'Petrol',
      transmission: vehicle.transmission || 'Manual',
      city: vehicle.city || 'Bengaluru',
      nickname: vehicle.nickname || '',
      ownership_status: vehicle.ownership_status,
      purchase_price: vehicle.purchase_price || 0,
      current_odometer: vehicle.current_odometer || 35000,
      annual_km: vehicle.annual_km || 12000,
      ownership_purpose: vehicle.ownership_purpose || '',
      notes: vehicle.notes || ''
    });
  };

  return (
    <PageTransition className="min-h-screen bg-surface-canvas text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* ================= HEADER & ACTIONS ================= */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-surface-border pb-6">
          <div>
            <div className="flex items-center space-x-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">
              <Car className="w-3.5 h-3.5 text-brand-400" />
              <span>Asset Intelligence & Portfolio Engine</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Garage & Portfolio Management
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Multi-vehicle economic tracking, TCO aggregation, and algorithmic capital allocation.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => fetchGarageIntelligence()}
              disabled={loading}
              className="btn-secondary text-xs flex items-center space-x-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-brand-400' : ''}`} />
              <span>Refresh</span>
            </button>

            {compareIds.length >= 2 && (
              <button
                onClick={handleRunCompare}
                disabled={comparing}
                className="btn-primary text-xs flex items-center space-x-1.5"
              >
                <Scale className={`w-3.5 h-3.5 ${comparing ? 'animate-spin' : ''}`} />
                <span>{comparing ? 'Comparing...' : `Compare (${compareIds.length})`}</span>
              </button>
            )}

            <button
              onClick={() => setShowScenarioModal(true)}
              className="btn-secondary text-xs flex items-center space-x-1.5"
            >
              <Sliders className="w-3.5 h-3.5 text-brand-400" />
              <span>What-If Simulator</span>
            </button>

            <button
              onClick={() => {
                setEditingVehicle(null);
                setFormData({
                  brand: 'Hyundai',
                  model: 'Creta',
                  variant: '1.5 SX',
                  year: 2021,
                  fuel_type: 'Petrol',
                  transmission: 'Manual',
                  city: 'Bengaluru',
                  nickname: '',
                  ownership_status: 'OWNED',
                  purchase_price: 1250000,
                  current_odometer: 35000,
                  annual_km: 12000,
                  ownership_purpose: 'Commute',
                  notes: ''
                });
                setShowAddModal(true);
              }}
              className="btn-primary text-xs flex items-center space-x-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Vehicle</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-3 text-rose-300">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
            <div>
              <p className="text-xs font-semibold">Garage Status</p>
              <p className="text-xs text-rose-200 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* ================= HERO SUMMARY CARDS ================= */}
        {intelligence && intelligence.summary && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
            <div className="card-surface p-4">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Total Vehicles</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-black text-white num-tabular">{intelligence.summary.total_vehicles || 0}</span>
                <span className="text-xs text-slate-400 font-mono">({intelligence.summary.owned_vehicles_count || 0} owned)</span>
              </div>
              <div className="mt-2 text-[11px] text-slate-400 truncate">
                Market: <span className="text-emerald-400 font-semibold">{intelligence.summary.overall_market_direction || 'STABLE'}</span>
              </div>
            </div>

            <div className="card-surface p-4">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Current Market Value</span>
              <div className="mt-2 text-2xl font-black text-slate-100 num-tabular">
                {intelligence.summary.total_current_value_formatted || '₹0'}
              </div>
              <div className="mt-2 text-[11px] text-slate-400">
                Sum of live model valuations
              </div>
            </div>

            <div className="card-surface p-4">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Annual Ownership Cost</span>
              <div className="mt-2 text-2xl font-black text-amber-400 num-tabular">
                {intelligence.summary.total_annual_cost_formatted || '₹0'}
              </div>
              <div className="mt-2 text-[11px] text-slate-400">
                Avg: <span className="text-slate-200 font-mono">{intelligence.summary.average_cost_per_km_formatted || '₹0/km'}</span>
              </div>
            </div>

            <div className="card-surface p-4">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">5Y Net TCO</span>
              <div className="mt-2 text-2xl font-black text-slate-100 num-tabular">
                {intelligence.summary.total_5y_tco_formatted || '₹0'}
              </div>
              <div className="mt-2 text-[11px] text-slate-400">
                5Y Resale: <span className="text-emerald-400 font-mono">{intelligence.summary.total_projected_5y_resale_formatted || '₹0'}</span>
              </div>
            </div>

            <div className="card-surface p-4 border-l-2 border-l-brand-500">
              <span className="text-[11px] font-mono uppercase tracking-wider text-brand-400 flex items-center justify-between">
                Garage Efficiency
                <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-black text-white num-tabular">{intelligence.efficiency_score?.overall_score ?? 0}</span>
                <span className="text-xs font-mono text-slate-400">/ 100 ({intelligence.efficiency_score?.rating_label || 'N/A'})</span>
              </div>
              <div className="mt-2 text-[11px] text-slate-400 truncate">
                Risk: <span className="text-slate-200 font-semibold">{intelligence.summary.risk_level_label || 'LOW'}</span>
              </div>
            </div>
          </div>
        )}

        {/* ================= PORTFOLIO RECOMMENDATION HERO BANNER ================= */}
        {intelligence && intelligence.summary && (intelligence.summary.total_vehicles || 0) > 0 && intelligence.recommendation && (
          <div className="card-surface p-6 sm:p-7">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="space-y-2 max-w-3xl">
                <div className="flex items-center gap-2.5">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-brand-500/10 text-brand-400 border border-brand-500/20">
                    PORTFOLIO ACTION: {(intelligence.recommendation.action || '').replace('_', ' ')}
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Confidence: <span className="text-slate-200 font-semibold">{intelligence.recommendation.confidence} ({intelligence.recommendation.confidence_score || 0}/100)</span>
                  </span>
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                  {intelligence.recommendation.headline}
                </h2>
                <div className="grid sm:grid-cols-2 gap-2 text-xs text-slate-300 pt-1">
                  {(intelligence.recommendation.primary_reasons || []).map((reason, idx) => (
                    <div key={idx} className="flex items-start gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <span>{reason}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex-shrink-0 flex flex-col sm:flex-row lg:flex-col gap-2">
                <button
                  onClick={() => setShowScenarioModal(true)}
                  className="btn-primary text-xs flex items-center justify-center space-x-1.5"
                >
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Simulate Optimization</span>
                </button>
                <div className="text-[10px] text-center font-mono text-slate-500">
                  Deterministic Portfolio Engine
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================= VEHICLE CARDS GRID ================= */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <Car className="w-4 h-4 text-brand-400" />
              <span>Garage Assets ({intelligence?.snapshots.length || 0})</span>
            </h2>
            <div className="text-xs text-slate-400 font-mono">
              Multi-asset portfolio view
            </div>
          </div>

          {loading ? (
            <div className="card-surface p-12 text-center">
              <RefreshCw className="w-6 h-6 text-brand-400 animate-spin mx-auto mb-3" />
              <p className="text-xs text-slate-400 font-mono uppercase tracking-wider">Evaluating portfolio valuations...</p>
            </div>
          ) : intelligence?.snapshots.length === 0 ? (
            <div className="card-surface p-12 text-center border-dashed space-y-4">
              <Car className="w-10 h-10 text-slate-600 mx-auto" />
              <div>
                <h3 className="text-base font-semibold text-white">Your Garage is Empty</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
                  Add vehicles you currently own, are tracking, or considering to unlock comprehensive multi-vehicle ownership economics.
                </p>
              </div>
              <button
                onClick={() => setShowAddModal(true)}
                className="btn-primary text-xs"
              >
                Add Your First Vehicle
              </button>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {intelligence?.snapshots.map((snap) => {
                const v = snap.vehicle;
                const isSelected = compareIds.includes(v.id);

                return (
                  <div
                    key={v.id}
                    className={`card-surface p-5 flex flex-col justify-between transition-all ${
                      isSelected ? 'border-brand-500/80 ring-1 ring-brand-500/40' : ''
                    }`}
                  >
                    <div>
                      {/* Top Row: Title & Badges */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 min-w-0">
                          {getVerifiedVehicleImage(v.brand, v.model) && (
                            <VehicleImage
                              brand={v.brand}
                              model={v.model}
                              compact={true}
                              className="w-12 h-12 rounded-lg shrink-0 border border-surface-border"
                            />
                          )}
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded uppercase bg-surface-canvas text-slate-300 border border-surface-border">
                                {v.ownership_status}
                              </span>
                              {v.nickname && (
                                <span className="text-xs font-mono text-brand-400 truncate max-w-[140px]">
                                  "{v.nickname}"
                                </span>
                              )}
                            </div>
                            <h3 className="text-base font-bold text-white mt-1.5 truncate">
                              {v.year} {v.brand} {v.model}
                            </h3>
                            <p className="text-xs text-slate-400 font-mono truncate">
                              {v.variant || 'Standard'} • {v.fuel_type} • {v.city}
                            </p>
                          </div>
                        </div>

                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleCompareSelection(v.id)}
                          className="w-4 h-4 rounded border-surface-border text-brand-500 focus:ring-brand-500 bg-surface-canvas cursor-pointer mt-1"
                          title="Select for comparison"
                        />
                      </div>

                      {/* Main Metric Badges */}
                      <div className="grid grid-cols-2 gap-2 my-4">
                        <div className="bg-surface-canvas p-2.5 rounded-lg border border-surface-border">
                          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Current Value</span>
                          <p className="text-sm font-bold text-white mt-0.5 num-tabular">
                            {snap.current_estimated_value_formatted}
                          </p>
                        </div>

                        <div className="bg-surface-canvas p-2.5 rounded-lg border border-surface-border">
                          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">5Y Net TCO</span>
                          <p className="text-sm font-bold text-slate-200 mt-0.5 num-tabular">
                            {snap.five_year_tco_formatted}
                          </p>
                        </div>

                        <div className="bg-surface-canvas p-2.5 rounded-lg border border-surface-border">
                          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Cost / km</span>
                          <p className="text-xs font-semibold text-amber-400 mt-0.5 num-tabular font-mono">
                            {snap.cost_per_km_formatted}
                          </p>
                        </div>

                        <div className="bg-surface-canvas p-2.5 rounded-lg border border-surface-border">
                          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Market Trend</span>
                          <p className="text-xs font-semibold text-emerald-400 mt-0.5 flex items-center gap-1 font-mono">
                            {snap.market_trend === 'RISING' ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5 text-rose-400" />}
                            {snap.market_trend}
                          </p>
                        </div>
                      </div>

                      {/* Lifecycle & Utilization Row */}
                      <div className="flex items-center justify-between text-xs py-2 px-3 bg-surface-canvas rounded-lg border border-surface-border font-mono text-[11px]">
                        <span className="text-slate-400">Lifecycle Signal:</span>
                        <span className="font-bold text-slate-200">
                          {snap.lifecycle_action} ({snap.lifecycle_score}/100)
                        </span>
                      </div>
                    </div>

                    {/* Actions Bar */}
                    <div className="flex items-center justify-between gap-2 pt-3.5 mt-3.5 border-t border-surface-border">
                      <button
                        onClick={() => setSelectedSnapshot(snap)}
                        className="text-xs font-semibold text-brand-400 hover:text-brand-300 flex items-center gap-1.5 py-1 transition-colors"
                      >
                        <Info className="w-3.5 h-3.5" />
                        <span>Asset Details</span>
                      </button>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => openEditModal(v)}
                          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-elevated rounded transition-all"
                          title="Edit vehicle details"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteVehicle(v.id, `${v.brand} ${v.model}`)}
                          className="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded transition-all"
                          title="Remove from garage"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ================= SELL-FIRST & KEEP-FIRST RANKINGS ================= */}
        {intelligence && intelligence.snapshots.length > 0 && (
          <div className="grid lg:grid-cols-2 gap-6">

            {/* Sell-First Table */}
            <div className="card-surface p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-rose-400" />
                    <span>Sell-First Priority Intelligence</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Ranked by depreciation velocity, capital drag, and impending maintenance cycles.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-surface-canvas text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-surface-border">
                    <tr>
                      <th className="py-2.5 px-3">Vehicle</th>
                      <th className="py-2.5 px-3">Priority</th>
                      <th className="py-2.5 px-3">Current Value</th>
                      <th className="py-2.5 px-3">Annual Cost</th>
                      <th className="py-2.5 px-3">Decline</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border font-mono">
                    {intelligence.sell_first_ranking.map((item, idx) => (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-2.5 px-3 font-sans font-medium text-white truncate max-w-[140px]">
                          {item.vehicle_display_name}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold num-tabular ${
                            item.sell_priority_score >= 70
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : 'bg-surface-canvas text-slate-300 border border-surface-border'
                          }`}>
                            {item.sell_priority_score}/100
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-100 font-semibold num-tabular">{item.current_value_formatted}</td>
                        <td className="py-2.5 px-3 text-amber-400 num-tabular">{item.annual_ownership_cost_formatted}</td>
                        <td className="py-2.5 px-3 text-slate-400 num-tabular">-{item.projected_resale_decline_pct}%/yr</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Keep-First Table */}
            <div className="card-surface p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Keep-First Value Preservation</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Vehicles exhibiting resilient residual values and low cost-per-kilometer curves.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-surface-canvas text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-surface-border">
                    <tr>
                      <th className="py-2.5 px-3">Vehicle</th>
                      <th className="py-2.5 px-3">Score</th>
                      <th className="py-2.5 px-3">5Y TCO</th>
                      <th className="py-2.5 px-3">Cost / km</th>
                      <th className="py-2.5 px-3">Risk Level</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border font-mono">
                    {intelligence.keep_first_ranking.map((item, idx) => (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-2.5 px-3 font-sans font-medium text-white truncate max-w-[140px]">
                          {item.vehicle_display_name}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold num-tabular ${
                            item.keep_priority_score >= 70
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-surface-canvas text-slate-300 border border-surface-border'
                          }`}>
                            {item.keep_priority_score}/100
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-200 num-tabular">{item.five_year_tco_formatted}</td>
                        <td className="py-2.5 px-3 text-amber-400 num-tabular">{item.cost_per_km_formatted}</td>
                        <td className="py-2.5 px-3">
                          <span className={`font-semibold ${item.risk_level === 'LOW' ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {item.risk_level} ({item.risk_score})
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

        {/* ================= REPLACEMENT & REDUNDANCY PANELS ================= */}
        {intelligence && intelligence.snapshots.length > 0 && (
          <div className="grid lg:grid-cols-2 gap-6">

            {/* Replacement Opportunities */}
            <div className="card-surface p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Repeat className="w-4 h-4 text-brand-400" />
                    <span>Replacement Arbitrage Opportunities</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Measurable economic upgrades identified from active marketplace inventories.
                  </p>
                </div>
              </div>

              {intelligence.replacement_opportunities.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-400 bg-surface-canvas border border-surface-border rounded-lg">
                  No replacement models currently outperform your owned portfolio vehicles economically.
                </div>
              ) : (
                <div className="space-y-3">
                  {intelligence.replacement_opportunities.map((opp, idx) => (
                    <div key={idx} className="p-3.5 bg-surface-canvas border border-surface-border rounded-lg space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white font-mono">
                          {opp.current_vehicle_name} → <span className="text-brand-400">{opp.candidate_replacement_name}</span>
                        </span>
                        <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
                          Score: {opp.replacement_opportunity_score}/100
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-400 pt-1 font-mono">
                        <div>
                          TCO Savings: <span className="text-emerald-400 font-semibold">{opp.tco_difference_formatted}</span>
                        </div>
                        <div>
                          Resale Adv: <span className="text-slate-200 font-semibold">{opp.resale_difference_formatted}</span>
                        </div>
                        <div>
                          Break-Even: <span className="text-amber-400 font-semibold">{opp.break_even_months ? `${opp.break_even_months} mo` : 'Immediate'}</span>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400 italic pt-0.5 leading-relaxed">
                        "{opp.recommendation_rationale}"
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Vehicle Redundancy Analysis */}
            <div className="card-surface p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <PieChart className="w-4 h-4 text-indigo-400" />
                    <span>Portfolio Redundancy & Segment Overlap</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Segment, powertrain, and utilization overlap detection across garage assets.
                  </p>
                </div>
              </div>

              {intelligence.redundancy_analysis.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-400 bg-surface-canvas border border-surface-border rounded-lg">
                  {intelligence.snapshots.length < 2
                    ? 'Add at least 2 vehicles to analyze segment redundancy.'
                    : 'No excessive functional redundancy detected between your vehicles.'}
                </div>
              ) : (
                <div className="space-y-3">
                  {intelligence.redundancy_analysis.map((red, idx) => (
                    <div key={idx} className="p-3.5 bg-surface-canvas border border-surface-border rounded-lg space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white font-mono">
                          {red.vehicle_a_name} & {red.vehicle_b_name}
                        </span>
                        <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                          red.redundancy_level === 'HIGH'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {red.redundancy_level} OVERLAP
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 flex-wrap">
                        {red.overlap_factors.map((f, i) => (
                          <span key={i} className="px-2 py-0.5 bg-surface-card border border-surface-border rounded text-slate-300 font-mono text-[10px]">
                            • {f}
                          </span>
                        ))}
                      </div>
                      <p className="text-[11px] text-slate-400 pt-0.5 leading-relaxed">
                        {red.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

        {/* ================= ADD / EDIT VEHICLE MODAL ================= */}
        {(showAddModal || editingVehicle) && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="card-elevated w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-6">
              <div className="flex items-center justify-between border-b border-surface-border pb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Car className="w-4 h-4 text-brand-400" />
                  <span>{editingVehicle ? 'Edit Garage Asset' : 'Add Vehicle to Portfolio'}</span>
                </h3>
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingVehicle(null);
                  }}
                  className="p-1.5 text-slate-400 hover:text-white rounded transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={editingVehicle ? handleUpdateVehicle : handleCreateVehicle} className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Make / Brand *</label>
                    <input
                      type="text"
                      required
                      value={formData.brand}
                      onChange={e => setFormData({ ...formData, brand: e.target.value })}
                      className="input-field text-xs text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Model *</label>
                    <input
                      type="text"
                      required
                      value={formData.model}
                      onChange={e => setFormData({ ...formData, model: e.target.value })}
                      className="input-field text-xs text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Year *</label>
                    <input
                      type="number"
                      required
                      min={1990}
                      max={2030}
                      value={formData.year}
                      onChange={e => setFormData({ ...formData, year: parseInt(e.target.value) || 2020 })}
                      className="input-field text-xs text-white num-tabular"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Variant / Trim</label>
                    <input
                      type="text"
                      value={formData.variant || ''}
                      onChange={e => setFormData({ ...formData, variant: e.target.value })}
                      className="input-field text-xs text-white"
                      placeholder="e.g. 1.5 SX"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Fuel Type</label>
                    <select
                      value={formData.fuel_type || 'Petrol'}
                      onChange={e => setFormData({ ...formData, fuel_type: e.target.value })}
                      className="input-field text-xs text-white"
                    >
                      <option value="Petrol">Petrol</option>
                      <option value="Diesel">Diesel</option>
                      <option value="CNG">CNG</option>
                      <option value="Electric">Electric</option>
                      <option value="Hybrid">Hybrid</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Transmission</label>
                    <select
                      value={formData.transmission || 'Manual'}
                      onChange={e => setFormData({ ...formData, transmission: e.target.value })}
                      className="input-field text-xs text-white"
                    >
                      <option value="Manual">Manual</option>
                      <option value="Automatic">Automatic</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Location / City</label>
                    <input
                      type="text"
                      value={formData.city || 'Bengaluru'}
                      onChange={e => setFormData({ ...formData, city: e.target.value })}
                      className="input-field text-xs text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Ownership Status</label>
                    <select
                      value={formData.ownership_status || 'OWNED'}
                      onChange={e => setFormData({ ...formData, ownership_status: e.target.value as OwnershipStatus })}
                      className="input-field text-xs text-white"
                    >
                      <option value="OWNED">OWNED</option>
                      <option value="CONSIDERING">CONSIDERING</option>
                      <option value="WATCHING">WATCHING</option>
                      <option value="SOLD">SOLD</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Asset Nickname</label>
                    <input
                      type="text"
                      value={formData.nickname || ''}
                      onChange={e => setFormData({ ...formData, nickname: e.target.value })}
                      className="input-field text-xs text-white"
                      placeholder="e.g. Daily Driver"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Purchase Price (₹)</label>
                    <input
                      type="number"
                      value={formData.purchase_price || 0}
                      onChange={e => setFormData({ ...formData, purchase_price: parseFloat(e.target.value) || 0 })}
                      className="input-field text-xs text-white num-tabular"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Odometer (km)</label>
                    <input
                      type="number"
                      value={formData.current_odometer || 35000}
                      onChange={e => setFormData({ ...formData, current_odometer: parseInt(e.target.value) || 0 })}
                      className="input-field text-xs text-white num-tabular"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Annual Mileage (km)</label>
                    <input
                      type="number"
                      value={formData.annual_km || 12000}
                      onChange={e => setFormData({ ...formData, annual_km: parseInt(e.target.value) || 0 })}
                      className="input-field text-xs text-white num-tabular"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Primary Utilization</label>
                  <input
                    type="text"
                    value={formData.ownership_purpose || ''}
                    onChange={e => setFormData({ ...formData, ownership_purpose: e.target.value })}
                    className="input-field text-xs text-white"
                    placeholder="e.g. Daily office commute & weekend highway trips"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Maintenance & Records Notes</label>
                  <textarea
                    rows={2}
                    value={formData.notes || ''}
                    onChange={e => setFormData({ ...formData, notes: e.target.value })}
                    className="input-field text-xs text-white"
                    placeholder="Major services, insurance renewal month, modifications..."
                  />
                </div>

                <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-surface-border">
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddModal(false);
                      setEditingVehicle(null);
                    }}
                    className="btn-secondary text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-primary text-xs"
                  >
                    {editingVehicle ? 'Update Vehicle' : 'Save to Portfolio'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ================= WHAT-IF SCENARIO MODAL ================= */}
        {showScenarioModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="card-elevated w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 space-y-6">
              <div className="flex items-center justify-between border-b border-surface-border pb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-brand-400" />
                    <span>What-If Scenario Simulator</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Evaluate portfolio effects of disposals, replacements, or utilization shifts.
                  </p>
                </div>
                <button onClick={() => setShowScenarioModal(false)} className="p-1.5 text-slate-400 hover:text-white rounded transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Action Type</label>
                    <select
                      value={scenarioActionType}
                      onChange={e => setScenarioActionType(e.target.value as GarageScenarioActionType)}
                      className="input-field text-xs text-white"
                    >
                      <option value="SELL">Sell a Vehicle</option>
                      <option value="REPLACE">Replace with Another Vehicle</option>
                      <option value="UPDATE_MILEAGE">Change Annual Usage</option>
                      <option value="ADD">Add New Vehicle</option>
                    </select>
                  </div>

                  {scenarioActionType !== 'ADD' && (
                    <div>
                      <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Target Portfolio Asset</label>
                      <select
                        value={scenarioTargetVehicleId}
                        onChange={e => setScenarioTargetVehicleId(e.target.value)}
                        className="input-field text-xs text-white"
                      >
                        {intelligence?.snapshots.map(s => (
                          <option key={s.vehicle.id} value={s.vehicle.id}>
                            {s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>

                {(scenarioActionType === 'REPLACE' || scenarioActionType === 'ADD') && (
                  <div className="p-4 bg-surface-canvas border border-surface-border rounded-lg space-y-3">
                    <span className="text-[11px] font-mono font-bold text-brand-400 uppercase tracking-wider">
                      {scenarioActionType === 'REPLACE' ? 'Replacement Specification' : 'Candidate Specification'}
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div>
                        <label className="block text-[10px] font-mono text-slate-400 mb-1">Brand</label>
                        <input
                          type="text"
                          value={scenarioReplacementBrand}
                          onChange={e => setScenarioReplacementBrand(e.target.value)}
                          className="input-field text-xs text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-mono text-slate-400 mb-1">Model</label>
                        <input
                          type="text"
                          value={scenarioReplacementModel}
                          onChange={e => setScenarioReplacementModel(e.target.value)}
                          className="input-field text-xs text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-mono text-slate-400 mb-1">Year</label>
                        <input
                          type="number"
                          value={scenarioReplacementYear}
                          onChange={e => setScenarioReplacementYear(parseInt(e.target.value) || 2022)}
                          className="input-field text-xs text-white num-tabular"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-mono text-slate-400 mb-1">Price (₹)</label>
                        <input
                          type="number"
                          value={scenarioReplacementPrice}
                          onChange={e => setScenarioReplacementPrice(parseFloat(e.target.value) || 0)}
                          className="input-field text-xs text-white num-tabular"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {(scenarioActionType === 'UPDATE_MILEAGE' || scenarioActionType === 'REPLACE' || scenarioActionType === 'ADD') && (
                  <div>
                    <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1">Adjusted Annual Usage (km/yr)</label>
                    <input
                      type="number"
                      value={scenarioAnnualKmOverride}
                      onChange={e => setScenarioAnnualKmOverride(parseInt(e.target.value) || 10000)}
                      className="input-field text-xs text-white num-tabular"
                    />
                  </div>
                )}

                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleSimulateScenario}
                    disabled={simulating}
                    className="btn-primary text-xs flex items-center space-x-1.5"
                  >
                    <Scale className={`w-3.5 h-3.5 ${simulating ? 'animate-spin' : ''}`} />
                    <span>{simulating ? 'Simulating...' : 'Run Simulation'}</span>
                  </button>
                </div>

                {scenarioResult && (
                  <div className="mt-4 p-4 bg-surface-canvas border border-surface-border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-white flex items-center gap-2">
                        <Scale className="w-3.5 h-3.5 text-brand-400" />
                        <span>Scenario Differential</span>
                      </h4>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        scenarioResult.delta_annual_cost <= 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {scenarioResult.delta_annual_cost <= 0 ? 'Cost Optimization' : 'Cost Increment'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed font-sans">
                      {scenarioResult.portfolio_impact_summary}
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs pt-1 font-mono">
                      <div className="bg-surface-card p-2.5 rounded border border-surface-border">
                        <span className="text-[10px] text-slate-400 block">Annual Cost Δ</span>
                        <p className={`text-xs font-bold num-tabular mt-0.5 ${scenarioResult.delta_annual_cost <= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {scenarioResult.delta_annual_cost_formatted}
                        </p>
                      </div>

                      <div className="bg-surface-card p-2.5 rounded border border-surface-border">
                        <span className="text-[10px] text-slate-400 block">5Y TCO Δ</span>
                        <p className={`text-xs font-bold num-tabular mt-0.5 ${scenarioResult.delta_5y_tco <= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {scenarioResult.delta_5y_tco_formatted}
                        </p>
                      </div>

                      <div className="bg-surface-card p-2.5 rounded border border-surface-border">
                        <span className="text-[10px] text-slate-400 block">Efficiency Δ</span>
                        <p className={`text-xs font-bold num-tabular mt-0.5 ${scenarioResult.delta_efficiency_score >= 0 ? 'text-brand-400' : 'text-amber-400'}`}>
                          {scenarioResult.delta_efficiency_score > 0 ? `+${scenarioResult.delta_efficiency_score}` : scenarioResult.delta_efficiency_score} pts
                        </p>
                      </div>

                      <div className="bg-surface-card p-2.5 rounded border border-surface-border">
                        <span className="text-[10px] text-slate-400 block">Break-Even</span>
                        <p className="text-xs font-bold text-slate-200 mt-0.5">
                          {scenarioResult.break_even_months !== null && scenarioResult.break_even_months !== undefined
                            ? `${scenarioResult.break_even_months} mos`
                            : 'N/A'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ================= VEHICLE COMPARISON DRAWER / MODAL ================= */}
        {compareResult && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="card-elevated w-full max-w-5xl max-h-[90vh] overflow-y-auto p-6 space-y-6">
              <div className="flex items-center justify-between border-b border-surface-border pb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Scale className="w-4 h-4 text-brand-400" />
                  <span>Portfolio Comparison ({compareResult.total_compared} Vehicles)</span>
                </h3>
                <button onClick={() => setCompareResult(null)} className="p-1.5 text-slate-400 hover:text-white rounded transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-surface-canvas text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-surface-border">
                    <tr>
                      <th className="py-2.5 px-3">Vehicle</th>
                      <th className="py-2.5 px-3">Current Value</th>
                      <th className="py-2.5 px-3">Annual Cost</th>
                      <th className="py-2.5 px-3">5Y TCO</th>
                      <th className="py-2.5 px-3">Cost / km</th>
                      <th className="py-2.5 px-3">Risk Level</th>
                      <th className="py-2.5 px-3">Lifecycle Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border font-mono">
                    {compareResult.vehicles.map(snap => (
                      <tr key={snap.vehicle.id} className="hover:bg-white/[0.02]">
                        <td className="py-2.5 px-3 font-sans font-semibold text-white">
                          {snap.vehicle.year} {snap.vehicle.brand} {snap.vehicle.model}
                        </td>
                        <td className="py-2.5 px-3 text-white font-bold num-tabular">{snap.current_estimated_value_formatted}</td>
                        <td className="py-2.5 px-3 text-amber-400 num-tabular">{snap.annual_ownership_cost_formatted}</td>
                        <td className="py-2.5 px-3 text-slate-200 font-semibold num-tabular">{snap.five_year_tco_formatted}</td>
                        <td className="py-2.5 px-3 text-slate-300 num-tabular">{snap.cost_per_km_formatted}</td>
                        <td className="py-2.5 px-3">
                          <span className={snap.risk_level === 'LOW' ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
                            {snap.risk_level} ({snap.risk_score})
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-bold text-brand-300">{snap.lifecycle_action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {compareResult.comparison_notes.length > 0 && (
                <div className="p-3.5 bg-surface-canvas border border-surface-border rounded-lg space-y-1.5">
                  <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">Comparative Analysis Notes:</span>
                  {compareResult.comparison_notes.map((note, idx) => (
                    <p key={idx} className="text-xs text-slate-400 leading-relaxed">• {note}</p>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================= VEHICLE DETAIL MODAL ================= */}
        {selectedSnapshot && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="card-elevated w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-surface-border pb-3.5">
                <div>
                  <h3 className="text-base font-bold text-white">
                    {selectedSnapshot.vehicle.year} {selectedSnapshot.vehicle.brand} {selectedSnapshot.vehicle.model}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    {selectedSnapshot.vehicle.variant || 'Standard'} • {selectedSnapshot.vehicle.city} • {selectedSnapshot.vehicle.ownership_status}
                  </p>
                </div>
                <button onClick={() => setSelectedSnapshot(null)} className="p-1.5 text-slate-400 hover:text-white rounded transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs font-mono">
                <div className="bg-surface-canvas p-3 rounded-lg border border-surface-border">
                  <span className="text-slate-400 text-[10px] uppercase block">Current Value</span>
                  <p className="text-sm font-bold text-white mt-0.5 num-tabular">{selectedSnapshot.current_estimated_value_formatted}</p>
                </div>
                <div className="bg-surface-canvas p-3 rounded-lg border border-surface-border">
                  <span className="text-slate-400 text-[10px] uppercase block">5Y Net TCO</span>
                  <p className="text-sm font-bold text-slate-200 mt-0.5 num-tabular">{selectedSnapshot.five_year_tco_formatted}</p>
                </div>
                <div className="bg-surface-canvas p-3 rounded-lg border border-surface-border">
                  <span className="text-slate-400 text-[10px] uppercase block">Annual Cost</span>
                  <p className="text-sm font-bold text-amber-400 mt-0.5 num-tabular">{selectedSnapshot.annual_ownership_cost_formatted}</p>
                </div>
                <div className="bg-surface-canvas p-3 rounded-lg border border-surface-border">
                  <span className="text-slate-400 text-[10px] uppercase block">Cost / km</span>
                  <p className="text-xs font-semibold text-slate-200 mt-0.5 num-tabular">{selectedSnapshot.cost_per_km_formatted}</p>
                </div>
                <div className="bg-surface-canvas p-3 rounded-lg border border-surface-border">
                  <span className="text-slate-400 text-[10px] uppercase block">Projected 5Y Resale</span>
                  <p className="text-xs font-semibold text-emerald-400 mt-0.5 num-tabular">{selectedSnapshot.projected_5y_resale_formatted}</p>
                </div>
                <div className="bg-surface-canvas p-3 rounded-lg border border-surface-border">
                  <span className="text-slate-400 text-[10px] uppercase block">Risk Assessment</span>
                  <p className="text-xs font-semibold text-slate-200 mt-0.5">{selectedSnapshot.risk_level} ({selectedSnapshot.risk_score})</p>
                </div>
              </div>

              <div className="p-3.5 bg-surface-canvas border border-surface-border rounded-lg space-y-2 text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-300">Lifecycle Recommendation:</span>
                  <span className="font-bold text-brand-400">{selectedSnapshot.lifecycle_action} ({selectedSnapshot.lifecycle_score}/100)</span>
                </div>
                <div className="flex items-center justify-between text-slate-400 font-mono text-[11px] pt-1">
                  <span>Market Momentum (90D):</span>
                  <span className="text-slate-200">{selectedSnapshot.market_momentum_90d}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                  <span>Utilization Class:</span>
                  <span className="text-slate-200">{selectedSnapshot.utilization_class} ({selectedSnapshot.monthly_km} km/mo)</span>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setSelectedSnapshot(null)}
                  className="btn-secondary text-xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </PageTransition>
  );
};
