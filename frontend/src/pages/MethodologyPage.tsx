import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Cpu, 
  ShieldCheck, 
  ArrowRight, 
  AlertTriangle
} from 'lucide-react';

export const MethodologyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10 text-slate-100">
      {/* Header */}
      <div className="space-y-3 pb-6 border-b border-[#1c263c]">
        <div className="inline-flex items-center space-x-2 text-xs font-mono text-sky-400">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span className="uppercase tracking-wider">TRANSPARENCY & EVIDENCE BASIS</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-white">
          Valuation Methodology & Model Architecture
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
          How AutoValue calculates used-car market estimates, constructs uncertainty intervals,
          matches comparable records, and attributes price factors.
        </p>
      </div>

      {/* Overview Card */}
      <div className="card-surface p-6 space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-sky-950/60 border border-sky-800/60 flex items-center justify-center text-sky-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Five-Stage Estimation Pipeline</h2>
            <p className="text-xs text-slate-400">Every valuation query executes an identical deterministic evaluation pipeline.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-2 text-xs">
          <div className="p-3 rounded-lg bg-[#0d1322] border border-[#1c263c] space-y-1">
            <span className="font-mono text-sky-400 font-bold">01. Inputs</span>
            <p className="text-slate-300 font-medium">Feature Vector</p>
            <p className="text-[11px] text-slate-500">Brand, model, year, km, fuel, gearbox, city location.</p>
          </div>

          <div className="p-3 rounded-lg bg-[#0d1322] border border-[#1c263c] space-y-1">
            <span className="font-mono text-sky-400 font-bold">02. ML Model</span>
            <p className="text-slate-300 font-medium">XGBoost v002</p>
            <p className="text-[11px] text-slate-500">Gradient-boosted decision trees trained on price regressions.</p>
          </div>

          <div className="p-3 rounded-lg bg-[#0d1322] border border-[#1c263c] space-y-1">
            <span className="font-mono text-sky-400 font-bold">03. Uncertainty</span>
            <p className="text-slate-300 font-medium">Conformal Bounds</p>
            <p className="text-[11px] text-slate-500">80% empirical residual calibration from validation holdouts.</p>
          </div>

          <div className="p-3 rounded-lg bg-[#0d1322] border border-[#1c263c] space-y-1">
            <span className="font-mono text-sky-400 font-bold">04. Comps</span>
            <p className="text-slate-300 font-medium">Nearest Neighbors</p>
            <p className="text-[11px] text-slate-500">Weighted similarity matching against observed dataset listings.</p>
          </div>

          <div className="p-3 rounded-lg bg-[#0d1322] border border-[#1c263c] space-y-1">
            <span className="font-mono text-sky-400 font-bold">05. SHAP</span>
            <p className="text-slate-300 font-medium">Attribution</p>
            <p className="text-[11px] text-slate-500">Quantified delta impact for each vehicle attribute.</p>
          </div>
        </div>
      </div>

      {/* Detailed Sections */}
      <div className="space-y-8">
        {/* Section 1 */}
        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-white flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            <span>1. Vehicle Input Normalization</span>
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            The valuation engine ingests explicit vehicle specifications: manufacturer make, model designation, trim/variant, manufacturing year, cumulative odometer reading, fuel propulsion type, transmission mechanism, and registration/sale locality. Categorical values are mapped through calibrated label encoders, while numerical variables (age, mileage) are scaled to prevent bias.
          </p>
        </section>

        {/* Section 2 */}
        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-white flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            <span>2. Machine Learning Point Valuation</span>
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            The primary point estimate is generated using an XGBoost gradient-boosted decision tree regressor (active version: <code className="text-sky-300 bg-[#0d1322] px-1.5 py-0.5 rounded border border-[#1c263c] font-mono text-xs">v002</code>). The model is optimized for Mean Absolute Error (MAE) and Coefficient of Determination (R²) on holdout test partitions. The model captures non-linear depreciation patterns, such as the steep initial two-year drop and mileage thresholds.
          </p>
        </section>

        {/* Section 3 */}
        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-white flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            <span>3. Conformal Prediction Uncertainty Bounds</span>
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Unlike simplistic percentage spreads (e.g. ±10%), AutoValue calculates uncertainty intervals using split-conformal inference on validation residual errors. An 80% coverage interval guarantees that, under identical distribution assumptions, the true market asking price falls within the interval with empirical 80% coverage. Wider intervals reflect sparse data or high dispersion for rare configurations.
          </p>
        </section>

        {/* Section 4 */}
        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-white flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            <span>4. Comparable Vehicle Evidence</span>
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            For empirical validation, the engine retrieves the top comparable records using weighted multi-attribute distance (matching make, model, age delta, mileage delta, and fuel/transmission alignment). Each comparable displays its similarity score and asking price, giving buyers and sellers direct context.
          </p>
        </section>

        {/* Section 5 */}
        <section className="space-y-3">
          <h3 className="text-lg font-semibold text-white flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            <span>5. SHAP Factor Attribution</span>
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Using TreeSHAP (SHapley Additive exPlanations), the valuation explains why a vehicle received its estimate. Every factor (e.g. low mileage, premium automatic transmission, vehicle age) is shown with its precise rupee addition or reduction relative to the baseline market average.
          </p>
        </section>
      </div>

      {/* Honest Data Provenance & Limitations */}
      <div className="card-surface p-6 border-amber-800/50 bg-[#0d1322] space-y-4">
        <div className="flex items-center space-x-3 text-amber-300">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <h3 className="text-sm font-semibold">Data Provenance & System Limitations</h3>
        </div>
        <div className="text-xs text-slate-300 space-y-2 leading-relaxed">
          <p>
            <strong className="text-white">Demonstration Dataset:</strong> The current database consists of standardized benchmark records compiled for model calibration, testing, and functional demonstration. While calibrated against Indian automotive price curves across 14 OEMs, records are demonstration data rather than real-time live dealer inventory feeds.
          </p>
          <p>
            <strong className="text-white">Physical Inspection Disclaimer:</strong> The algorithm evaluates statistical price indicators based on reported specifications. It cannot detect physical vehicle condition, mechanical wear, flood damage, accident history, cosmetic paint depth, or title liens.
          </p>
          <p>
            <strong className="text-white">Not a Binding Appraisal:</strong> AutoValue estimates do not constitute binding transaction offers, guaranteed buyback commitments, or legal appraisals.
          </p>
        </div>
      </div>

      {/* CTA */}
      <div className="pt-4 flex items-center justify-between border-t border-[#1c263c]">
        <Link to="/" className="text-xs text-slate-400 hover:text-white transition-colors">
          ← Return to Home
        </Link>
        <Link to="/valuation" className="btn-primary py-2 px-4 text-xs">
          <span>Estimate a Car's Value</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
};
