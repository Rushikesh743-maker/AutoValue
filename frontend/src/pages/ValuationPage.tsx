import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Car, 
  MapPin, 
  Gauge, 
  Calendar, 
  Fuel, 
  Settings2, 
  IndianRupee, 
  ArrowRight, 
  ShieldCheck, 
  RotateCcw, 
  ChevronDown
} from 'lucide-react';
import { PageTransition } from '../components/motion/PageTransition';
import { VehicleImage, getVerifiedVehicleImage } from '../components/VehicleImage';

interface PresetVehicle {
  label: string;
  brand: string;
  model: string;
  variant: string;
  year: number;
  km_driven: number;
  fuel_type: string;
  transmission: string;
  city: string;
  asking_price: string;
}

const PRESET_VEHICLES: PresetVehicle[] = [
  {
    label: '2021 Hyundai Creta SX',
    brand: 'Hyundai',
    model: 'Creta',
    variant: '1.5 CRDi SX',
    year: 2021,
    km_driven: 38000,
    fuel_type: 'Diesel',
    transmission: 'Manual',
    city: 'Bengaluru',
    asking_price: '1350000'
  },
  {
    label: '2020 Honda City V CVT',
    brand: 'Honda',
    model: 'City',
    variant: '1.5 i-VTEC V CVT',
    year: 2020,
    km_driven: 42000,
    fuel_type: 'Petrol',
    transmission: 'Automatic',
    city: 'Mumbai',
    asking_price: '1025000'
  },
  {
    label: '2019 Maruti Swift ZXi',
    brand: 'Maruti Suzuki',
    model: 'Swift',
    variant: '1.2 ZXi AMT',
    year: 2019,
    km_driven: 51000,
    fuel_type: 'Petrol',
    transmission: 'Automatic',
    city: 'Delhi NCR',
    asking_price: '585000'
  },
  {
    label: '2022 Tata Nexon XZ+',
    brand: 'Tata',
    model: 'Nexon',
    variant: '1.5 Revotorq XZ+',
    year: 2022,
    km_driven: 29000,
    fuel_type: 'Diesel',
    transmission: 'Manual',
    city: 'Pune',
    asking_price: '1150000'
  }
];

export const ValuationPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [formData, setFormData] = useState({
    brand: searchParams.get('brand') || 'Hyundai',
    model: searchParams.get('model') || 'Creta',
    variant: searchParams.get('variant') || '1.5 CRDi SX',
    year: Number(searchParams.get('year')) || 2021,
    km_driven: Number(searchParams.get('km')) || 38000,
    fuel_type: searchParams.get('fuel_type') || 'Diesel',
    transmission: searchParams.get('transmission') || 'Manual',
    city: searchParams.get('city') || 'Bengaluru',
    asking_price: searchParams.get('asking_price') || '1350000'
  });

  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // If search params change, re-populate formData
  useEffect(() => {
    if (searchParams.get('brand') || searchParams.get('model')) {
      setFormData(prev => ({
        ...prev,
        brand: searchParams.get('brand') || prev.brand,
        model: searchParams.get('model') || prev.model,
        variant: searchParams.get('variant') || prev.variant,
        year: Number(searchParams.get('year')) || prev.year,
        km_driven: Number(searchParams.get('km')) || prev.km_driven,
        fuel_type: searchParams.get('fuel_type') || prev.fuel_type,
        transmission: searchParams.get('transmission') || prev.transmission,
        city: searchParams.get('city') || prev.city
      }));
    }
  }, [searchParams]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: (name === 'year' || name === 'km_driven') ? Number(value) : value
    }));
  };

  const applyPreset = (preset: PresetVehicle) => {
    setFormData({
      brand: preset.brand,
      model: preset.model,
      variant: preset.variant,
      year: preset.year,
      km_driven: preset.km_driven,
      fuel_type: preset.fuel_type,
      transmission: preset.transmission,
      city: preset.city,
      asking_price: preset.asking_price
    });
    setErrorMsg(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (formData.km_driven < 0) {
      setErrorMsg("Odometer reading cannot be negative.");
      return;
    }

    if (!formData.model.trim()) {
      setErrorMsg("Please enter a vehicle model name.");
      return;
    }

    const payload = {
      ...formData,
      asking_price: formData.asking_price ? Number(formData.asking_price) : undefined
    };

    navigate('/results', { state: { vehicleData: payload } });
  };

  const activeCatalogAsset = getVerifiedVehicleImage(formData.brand, formData.model);

  return (
    <PageTransition className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-2 text-xs text-sky-400 font-mono mb-2">
          <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
          <span>RESEARCH TERMINAL • MODEL SPECIFICATION</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          Vehicle Valuation Terminal
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
          Specify vehicle attributes to generate an empirical point valuation, 80% uncertainty bounds, SHAP factor attribution, and active marketplace comparables.
        </p>

        {/* Quick Reference Presets */}
        <div className="mt-5 pt-4 border-t border-[#1c263c]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Quick Reference Benchmarks
            </span>
            <span className="text-[11px] text-slate-500">Click to populate form</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {PRESET_VEHICLES.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => applyPreset(p)}
                className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer border ${
                  formData.brand === p.brand && formData.model === p.model
                    ? 'bg-[#141c30] text-sky-300 border-[#273553]'
                    : 'bg-[#0d1322] text-slate-400 border-[#1c263c] hover:text-slate-200 hover:border-[#273553]'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Compact Verified Model Photo Reference (Non-obtrusive) */}
          {activeCatalogAsset && (
            <div className="mt-3.5 p-2.5 rounded-lg bg-[#090e1a] border border-[#1c263c] flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-16 h-10 rounded overflow-hidden shrink-0 border border-[#273553] bg-[#0c1220]">
                  <img
                    src={activeCatalogAsset.webp}
                    alt={activeCatalogAsset.label}
                    className="w-full h-full object-cover object-center"
                    loading="lazy"
                  />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-white truncate">
                      {formData.brand} {formData.model}
                    </span>
                    <span className="badge-brand text-[9px] py-0">Catalog Reference</span>
                  </div>
                  <p className="text-[11px] text-slate-400 truncate">
                    Verified specification visual • Form remains primary task
                  </p>
                </div>
              </div>
              <span className="hidden sm:inline-block text-[10px] font-mono text-slate-500">
                Spec Verified
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Error Alert Container */}
      {errorMsg && (
        <div className="mb-6 p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-200 flex items-center space-x-2.5">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0"></span>
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Terminal Form */}
      <div className="card-surface p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1: Vehicle Identity */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#1c263c]">
              <div className="flex items-center space-x-2">
                <Car className="w-4 h-4 text-sky-400" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                  1. Vehicle Specification
                </h2>
              </div>
              {getVerifiedVehicleImage(formData.brand, formData.model) ? (
                <div className="flex items-center space-x-1.5 text-[11px] text-sky-300 font-mono bg-sky-950/40 border border-sky-800/50 px-2 py-0.5 rounded-full">
                  <VehicleImage
                    brand={formData.brand}
                    model={formData.model}
                    compact={true}
                    className="w-4 h-4 rounded-full"
                  />
                  <span>Verified Catalog Reference</span>
                </div>
              ) : (
                <span className="text-[11px] text-slate-500 font-mono">Make / Model / Trim</span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Brand */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Make / OEM Brand <span className="text-sky-400">*</span>
                </label>
                <select
                  name="brand"
                  value={formData.brand}
                  onChange={handleChange}
                  className="input-field"
                >
                  <option value="Hyundai">Hyundai</option>
                  <option value="Maruti Suzuki">Maruti Suzuki</option>
                  <option value="Tata">Tata</option>
                  <option value="Mahindra">Mahindra</option>
                  <option value="Honda">Honda</option>
                  <option value="Toyota">Toyota</option>
                  <option value="Kia">Kia</option>
                  <option value="Volkswagen">Volkswagen</option>
                  <option value="Skoda">Skoda</option>
                  <option value="MG">MG</option>
                  <option value="Renault">Renault</option>
                  <option value="Ford">Ford</option>
                </select>
                <span className="text-[11px] text-slate-500 mt-1 block">Vehicle manufacturer</span>
              </div>

              {/* Model */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Model Line <span className="text-sky-400">*</span>
                </label>
                <input
                  type="text"
                  name="model"
                  value={formData.model}
                  onChange={handleChange}
                  placeholder="e.g. Creta, City, Swift, Nexon"
                  required
                  className="input-field"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">Model name</span>
              </div>

              {/* Variant / Trim */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Variant / Trim Package
                </label>
                <input
                  type="text"
                  name="variant"
                  value={formData.variant}
                  onChange={handleChange}
                  placeholder="e.g. 1.5 CRDi SX, V CVT, ZXi"
                  className="input-field"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">Optional specification trim</span>
              </div>
            </div>
          </div>

          {/* Section 2: Specification & Condition */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#1c263c]">
              <div className="flex items-center space-x-2">
                <Gauge className="w-4 h-4 text-sky-400" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                  2. Configuration & Mileage
                </h2>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Age / Usage / Powertrain</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {/* Year */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>Registration Year <span className="text-sky-400">*</span></span>
                </label>
                <select
                  name="year"
                  value={formData.year}
                  onChange={handleChange}
                  className="input-field num-tabular"
                >
                  {Array.from({ length: 15 }, (_, i) => 2024 - i).map(yr => (
                    <option key={yr} value={yr}>{yr}</option>
                  ))}
                </select>
                <span className="text-[11px] text-slate-500 mt-1 block">Year of manufacture</span>
              </div>

              {/* Kilometers Driven */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center space-x-1">
                  <Gauge className="w-3.5 h-3.5 text-slate-400" />
                  <span>Odometer (KM) <span className="text-sky-400">*</span></span>
                </label>
                <input
                  type="number"
                  name="km_driven"
                  value={formData.km_driven}
                  onChange={handleChange}
                  min={0}
                  max={500000}
                  required
                  className="input-field num-tabular"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">Total distance logged</span>
              </div>

              {/* Fuel Type */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center space-x-1">
                  <Fuel className="w-3.5 h-3.5 text-slate-400" />
                  <span>Powertrain Fuel <span className="text-sky-400">*</span></span>
                </label>
                <select
                  name="fuel_type"
                  value={formData.fuel_type}
                  onChange={handleChange}
                  className="input-field"
                >
                  <option value="Petrol">Petrol</option>
                  <option value="Diesel">Diesel</option>
                  <option value="CNG">CNG</option>
                  <option value="Electric">Electric</option>
                  <option value="Hybrid">Hybrid</option>
                </select>
                <span className="text-[11px] text-slate-500 mt-1 block">Engine fuel type</span>
              </div>

              {/* Transmission */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center space-x-1">
                  <Settings2 className="w-3.5 h-3.5 text-slate-400" />
                  <span>Transmission <span className="text-sky-400">*</span></span>
                </label>
                <select
                  name="transmission"
                  value={formData.transmission}
                  onChange={handleChange}
                  className="input-field"
                >
                  <option value="Manual">Manual</option>
                  <option value="Automatic">Automatic</option>
                </select>
                <span className="text-[11px] text-slate-500 mt-1 block">Gearbox type</span>
              </div>
            </div>
          </div>

          {/* Section 3: Market Location */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#1c263c]">
              <div className="flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-sky-400" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                  3. Regional Market Location
                </h2>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Metro / State Cluster</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* City */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  RTO / Metro Region <span className="text-sky-400">*</span>
                </label>
                <select
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                  className="input-field"
                >
                  <option value="Bengaluru">Bengaluru</option>
                  <option value="Mumbai">Mumbai</option>
                  <option value="Delhi NCR">Delhi NCR</option>
                  <option value="Hyderabad">Hyderabad</option>
                  <option value="Pune">Pune</option>
                  <option value="Chennai">Chennai</option>
                  <option value="Kolkata">Kolkata</option>
                  <option value="Ahmedabad">Ahmedabad</option>
                  <option value="Jaipur">Jaipur</option>
                  <option value="Chandigarh">Chandigarh</option>
                  <option value="Kochi">Kochi</option>
                </select>
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Calibrates regional used-car market liquidity and state taxes
                </span>
              </div>
            </div>
          </div>

          {/* Section 4: Optional Target Price (Collapsible) */}
          <div className="border border-[#1c263c] rounded-lg p-4 bg-[#0a0f1d]/60 space-y-3">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between text-xs font-medium text-slate-300 hover:text-white transition-colors cursor-pointer"
            >
              <div className="flex items-center space-x-2">
                <IndianRupee className="w-4 h-4 text-slate-400" />
                <span>Optional Listing Benchmark (Asking Price)</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Optional</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAdvanced ? 'rotate-180 text-sky-400' : 'text-slate-400'}`} />
              </div>
            </button>

            {showAdvanced && (
              <div className="pt-3 border-t border-[#1c263c] space-y-2">
                <label className="block text-xs font-medium text-slate-300">
                  Target Asking Price (INR ₹)
                </label>
                <div className="relative max-w-md">
                  <IndianRupee className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="number"
                    name="asking_price"
                    value={formData.asking_price}
                    onChange={handleChange}
                    placeholder="e.g. 1350000"
                    min={10000}
                    className="input-field pl-9 num-tabular"
                  />
                </div>
                <span className="text-[11px] text-slate-500 block">
                  If provided, AutoValue analyzes how this asking price compares to the model estimate and peer range.
                </span>
              </div>
            )}
          </div>

          {/* Form Actions */}
          <div className="pt-4 border-t border-[#1c263c] flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-[11px] text-slate-500 flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
              <span>Inference executes XGBoost regression model with 80% coverage calibration</span>
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <button
                type="button"
                onClick={() => setFormData({
                  brand: 'Hyundai',
                  model: 'Creta',
                  variant: '1.5 CRDi SX',
                  year: 2021,
                  km_driven: 38000,
                  fuel_type: 'Diesel',
                  transmission: 'Manual',
                  city: 'Bengaluru',
                  asking_price: ''
                })}
                className="btn-ghost"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>

              <button
                type="submit"
                className="btn-primary w-full sm:w-auto"
              >
                <span>Calculate Fair Valuation</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </PageTransition>
  );
};

