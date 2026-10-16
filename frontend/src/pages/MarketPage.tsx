import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Info,
  AlertCircle,
  Filter,
  Car
} from 'lucide-react';
import {
  ResponsiveContainer,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area
} from 'recharts';
import { api, type HistoricalMarketResponse, type MarketTiming } from '../services/api';
import { PageTransition } from '../components/motion/PageTransition';
import { getVerifiedVehicleImage } from '../components/VehicleImage';

const AVAILABLE_BRANDS: Record<string, string[]> = {
  'Hyundai': ['Creta', 'i20', 'Venue', 'Verna'],
  'Maruti Suzuki': ['Swift', 'Baleno', 'Brezza', 'Dzire'],
  'Honda': ['City', 'Amaze', 'Civic'],
  'Toyota': ['Innova Crysta', 'Fortuner', 'Glanza'],
  'Tata': ['Nexon', 'Harrier', 'Punch', 'Altroz']
};

const AVAILABLE_CITIES = ['All Cities', 'Bengaluru', 'Mumbai', 'Delhi NCR', 'Pune', 'Hyderabad', 'Chennai'];

export const MarketPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  // Filters
  const [selectedBrand, setSelectedBrand] = useState<string>(searchParams.get('brand') || 'Hyundai');
  const [selectedModel, setSelectedModel] = useState<string>(searchParams.get('model') || 'Creta');
  const [selectedCity, setSelectedCity] = useState<string>(searchParams.get('city') || 'All Cities');
  const [selectedPeriod, setSelectedPeriod] = useState<string>('all');

  // Data states
  const [trendData, setTrendData] = useState<HistoricalMarketResponse | null>(null);
  const [timingData, setTimingData] = useState<MarketTiming | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Update models dropdown when brand changes
  useEffect(() => {
    const models = AVAILABLE_BRANDS[selectedBrand] || [];
    if (!models.includes(selectedModel)) {
      setSelectedModel(models[0] || '');
    }
  }, [selectedBrand]);

  // Fetch market trends and timing data
  useEffect(() => {
    let isMounted = true;
    const fetchMarketData = async () => {
      setLoading(true);
      setError(null);
      try {
        const cityParam = selectedCity === 'All Cities' ? undefined : selectedCity;
        const [historyRes, timingRes] = await Promise.all([
          api.getMarketHistory(selectedBrand, selectedModel, selectedPeriod, cityParam),
          api.getMarketTiming(selectedBrand, selectedModel, cityParam, selectedPeriod === '3m' ? '3m' : '6m')
        ]);
        if (isMounted) {
          setTrendData(historyRes);
          setTimingData(timingRes);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Unable to retrieve market dataset metrics.');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchMarketData();
    return () => {
      isMounted = false;
    };
  }, [selectedBrand, selectedModel, selectedCity, selectedPeriod]);

  const formatLakhs = (val?: number | null) => {
    if (val === undefined || val === null) return 'N/A';
    return `₹ ${(val / 100000).toFixed(2)} L`;
  };

  const chartData = (trendData?.history || []).map((h) => ({
    period: h.period,
    median: Math.round((h.median_price / 100000) * 100) / 100,
    p25: Math.round((h.p25 / 100000) * 100) / 100,
    p75: Math.round((h.p75 / 100000) * 100) / 100,
    count: h.listing_count
  }));

  const latestPoint = trendData?.history && trendData.history.length > 0
    ? trendData.history[trendData.history.length - 1]
    : null;

  const verifiedAsset = getVerifiedVehicleImage(selectedBrand, selectedModel);

  return (
    <PageTransition className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 text-slate-100">
      {/* Header */}
      <div className="space-y-3 pb-6 border-b border-[#1c263c]">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 text-xs font-mono text-sky-400 mb-1">
              <Activity className="w-3.5 h-3.5" />
              <span className="uppercase tracking-wider">MARKET ANALYSIS & PRICE DYNAMICS</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Automotive Market Intelligence
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed mt-1">
              Explore observed asking-price distributions, interquartile price spreads, and price trajectory
              metrics across manufacturers, models, and metropolitan regions.
            </p>
          </div>

          <div className="flex items-center space-x-3 self-start md:self-auto">
            <Link
              to="/valuation"
              className="btn-primary py-2 px-4 text-xs"
            >
              <Car className="w-3.5 h-3.5" />
              <span>Estimate Specific Vehicle</span>
            </Link>
          </div>
        </div>

        {/* Honest Demonstration Data Notice */}
        <div className="p-3 rounded-lg bg-[#0d1322] border border-[#273553] text-xs text-slate-300 flex items-start space-x-2.5">
          <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="text-white">Demonstration Dataset Disclosure:</strong> Historical trends and market statistics are derived from calibrated demonstration listings across Indian regional hubs. These figures illustrate platform analytical models and do not claim live dealer inventory synchronization.{' '}
            <Link to="/methodology" className="text-sky-400 underline hover:text-sky-300">
              Read methodology details
            </Link>.
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card-surface p-4 sm:p-5 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-[#1c263c] text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
              <Filter className="w-3.5 h-3.5 text-sky-400" />
              <span>Market Query Filters</span>
            </span>
            {verifiedAsset && (
              <span className="badge-brand text-[9px] py-0">
                Verified Benchmark
              </span>
            )}
          </div>
          <span className="font-mono text-[11px]">
            {trendData?.total_listings_analyzed !== undefined
              ? `${trendData.total_listings_analyzed} listings evaluated`
              : 'Filtering dataset'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Brand */}
          <div>
            <label className="block text-slate-300 font-medium mb-1">Manufacturer (OEM)</label>
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="input-field py-1.5"
            >
              {Object.keys(AVAILABLE_BRANDS).map((brand) => (
                <option key={brand} value={brand}>{brand}</option>
              ))}
            </select>
          </div>

          {/* Model */}
          <div>
            <label className="block text-slate-300 font-medium mb-1">Model Series</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="input-field py-1.5"
            >
              {(AVAILABLE_BRANDS[selectedBrand] || []).map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>

          {/* City */}
          <div>
            <label className="block text-slate-300 font-medium mb-1">Region / City</label>
            <select
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              className="input-field py-1.5"
            >
              {AVAILABLE_CITIES.map((city) => (
                <option key={city} value={city}>{city}</option>
              ))}
            </select>
          </div>

          {/* Period */}
          <div>
            <label className="block text-slate-300 font-medium mb-1">Observation Window</label>
            <div className="grid grid-cols-4 gap-1">
              {[
                { id: '3m', label: '3M' },
                { id: '6m', label: '6M' },
                { id: '12m', label: '12M' },
                { id: 'all', label: 'All' }
              ].map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setSelectedPeriod(p.id)}
                  className={`py-1.5 rounded text-center transition-colors font-medium ${
                    selectedPeriod === p.id
                      ? 'bg-[#141c30] text-sky-300 border border-[#273553]'
                      : 'bg-[#0d1322] text-slate-400 border border-[#1c263c] hover:text-white'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="card-surface p-12 text-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-sky-400 border-t-transparent animate-spin mx-auto"></div>
          <p className="text-xs text-slate-400">Aggregating market records for {selectedBrand} {selectedModel}...</p>
        </div>
      ) : error ? (
        <div className="card-surface p-8 border-rose-900/50 text-center space-y-3">
          <AlertCircle className="w-6 h-6 text-rose-400 mx-auto" />
          <h3 className="text-sm font-semibold text-white">Dataset Query Error</h3>
          <p className="text-xs text-rose-300/80 max-w-md mx-auto">{error}</p>
        </div>
      ) : !trendData || chartData.length === 0 ? (
        <div className="card-surface p-12 text-center space-y-3">
          <Car className="w-8 h-8 text-slate-500 mx-auto" />
          <h3 className="text-base font-semibold text-white">Insufficient Market Observations</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            No valid records matched the combination of {selectedBrand} {selectedModel} in {selectedCity}. Try expanding the region to "All Cities" or selecting a different observation window.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Key Metrics Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Metric 1: Median Price */}
            <div className="card-surface p-4 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                Observed Median Price
              </span>
              <div className="text-2xl font-bold text-white num-tabular">
                {formatLakhs(latestPoint?.median_price)}
              </div>
              <p className="text-[11px] text-slate-500">
                50th percentile asking price across recent listings
              </p>
            </div>

            {/* Metric 2: Interquartile Range (P25 - P75) */}
            <div className="card-surface p-4 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                Middle 50% Spread (P25–P75)
              </span>
              <div className="text-2xl font-bold text-sky-300 num-tabular">
                {latestPoint ? `${formatLakhs(latestPoint.p25)} – ${formatLakhs(latestPoint.p75)}` : 'N/A'}
              </div>
              <p className="text-[11px] text-slate-500">
                Core trading range filtering top & bottom 25% outliers
              </p>
            </div>

            {/* Metric 3: Movement Velocity */}
            <div className="card-surface p-4 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                Price Movement Direction
              </span>
              <div className="flex items-center space-x-2">
                {timingData?.direction === 'RISING' ? (
                  <>
                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                    <span className="text-xl font-bold text-emerald-400">Rising Trend</span>
                  </>
                ) : timingData?.direction === 'DECLINING' ? (
                  <>
                    <TrendingDown className="w-5 h-5 text-rose-400" />
                    <span className="text-xl font-bold text-rose-400">Softening</span>
                  </>
                ) : (
                  <>
                    <Activity className="w-5 h-5 text-slate-400" />
                    <span className="text-xl font-bold text-slate-200">Stable Market</span>
                  </>
                )}
              </div>
              <p className="text-[11px] text-slate-500">
                {trendData.observed_change?.description || 'Based on multi-period trajectory analysis'}
              </p>
            </div>

            {/* Metric 4: Supporting Data Density */}
            <div className="card-surface p-4 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
                Sample Evidence Density
              </span>
              <div className="text-2xl font-bold text-white num-tabular">
                {trendData.total_listings_analyzed} Records
              </div>
              <p className="text-[11px] text-slate-500">
                Active valid data points supporting this analysis
              </p>
            </div>
          </div>

          {/* Main Price Trajectory Chart */}
          <div className="card-surface p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-[#1c263c] gap-2">
              <div>
                <h2 className="text-sm font-semibold text-white">
                  Observed Price Distribution Over Time (₹ in Lakhs)
                </h2>
                <p className="text-xs text-slate-400">
                  Solid line denotes Median; shaded corridor represents Interquartile Spread (P25 to P75).
                </p>
              </div>
              <div className="flex items-center space-x-4 text-xs font-mono">
                <span className="flex items-center space-x-1.5 text-sky-400">
                  <span className="w-3 h-0.5 bg-sky-400 inline-block"></span>
                  <span>Median Price</span>
                </span>
                <span className="flex items-center space-x-1.5 text-slate-400">
                  <span className="w-3 h-2 bg-[#273553] rounded-xs inline-block"></span>
                  <span>P25–P75 Range</span>
                </span>
              </div>
            </div>

            <div className="h-72 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1c263c" vertical={false} />
                  <XAxis
                    dataKey="period"
                    stroke="#64748b"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: '#1c263c' }}
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={11}
                    tickFormatter={(v) => `₹ ${v}L`}
                    domain={['auto', 'auto']}
                    tickLine={false}
                    axisLine={{ stroke: '#1c263c' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0d1322',
                      borderColor: '#273553',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#f8fafc'
                    }}
                    formatter={(val: any, name: any) => {
                      if (name === 'median') return [`₹ ${val} Lakh`, 'Median Price'];
                      if (name === 'p75') return [`₹ ${val} Lakh`, '75th Percentile'];
                      if (name === 'p25') return [`₹ ${val} Lakh`, '25th Percentile'];
                      return [val, name];
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="p75"
                    stroke="transparent"
                    fill="#1e293b"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="p25"
                    stroke="transparent"
                    fill="#0d1322"
                    fillOpacity={0.9}
                  />
                  <Line
                    type="monotone"
                    dataKey="median"
                    stroke="#38bdf8"
                    strokeWidth={2.5}
                    dot={{ fill: '#38bdf8', r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="pt-3 border-t border-[#1c263c] flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
              <span>Data source: AutoValue Processed Benchmark Dataset (SHA-256 verified)</span>
              <div className="flex items-center space-x-2">
                <Link to="/methodology" className="hover:text-slate-300 underline">
                  How percentiles are calculated
                </Link>
                <span>•</span>
                <Link to="/valuation" className="text-sky-400 hover:text-sky-300">
                  Value a {selectedBrand} {selectedModel} →
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </PageTransition>
  );
};
