import React, { useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowRight, 
  ShieldCheck, 
  Cpu, 
  Layers, 
  TrendingUp,
  Sparkles
} from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { PageTransition } from '../components/motion/PageTransition';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const videoRef = useRef<HTMLVideoElement>(null);

  // Safely ensure muted autoplay without throwing uncaught promise rejection
  useEffect(() => {
    if (!shouldReduceMotion && videoRef.current) {
      videoRef.current.play().catch(() => {
        // Autoplay policy fallback (poster remains visible)
      });
    }
  }, [shouldReduceMotion]);

  // Subtle staggered motion variants
  const containerVariants = {
    hidden: { opacity: shouldReduceMotion ? 1 : 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : 0.08,
        delayChildren: shouldReduceMotion ? 0 : 0.04
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: shouldReduceMotion ? 1 : 0, y: shouldReduceMotion ? 0 : 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: shouldReduceMotion ? 0 : 0.28,
        ease: "easeOut" as const
      }
    }
  };

  const cardVariants = {
    hidden: { opacity: shouldReduceMotion ? 1 : 0, scale: shouldReduceMotion ? 1 : 0.985 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: {
        duration: shouldReduceMotion ? 0 : 0.32,
        ease: "easeOut" as const
      }
    }
  };

  return (
    <PageTransition className="text-slate-100 space-y-16 md:space-y-20 pb-16">
      {/* ========================================================================= */}
      {/* 1. CINEMATIC FULL-WIDTH AUTOMOTIVE VIDEO HERO DIRECTLY BENEATH NAVBAR */}
      {/* ========================================================================= */}
      <section 
        className="relative w-full overflow-hidden bg-[#070b14] border-b border-[#1c263c]"
        aria-label="AutoValue Pro Hero"
      >
        {/* Cinematic Video Background & Poster Fallback */}
        <div className="absolute inset-0 w-full h-full overflow-hidden pointer-events-none select-none">
          {!shouldReduceMotion ? (
            <video
              ref={videoRef}
              autoPlay
              muted
              loop
              playsInline
              preload="auto"
              poster="/images/hero_dark_suv_poster.jpg"
              aria-hidden="true"
              tabIndex={-1}
              className="hero-video-element w-full h-full object-cover object-[70%_center] sm:object-center"
            >
              <source src="/videos/hero_dark_suv.mp4" type="video/mp4" />
            </video>
          ) : null}

          {/* High-fidelity poster fallback for reduced motion or before playback begins */}
          <picture className={`hero-poster-element w-full h-full ${!shouldReduceMotion ? 'hidden' : 'block'}`}>
            <source type="image/webp" srcSet="/images/hero_dark_suv_poster.webp" />
            <img
              src="/images/hero_dark_suv_poster.jpg"
              alt=""
              aria-hidden="true"
              className="w-full h-full object-cover object-[70%_center] sm:object-center"
            />
          </picture>

          {/* Dark navy overlay with subtle directional and vertical gradients for contrast */}
          <div 
            className="absolute inset-0 bg-gradient-to-r from-[#070b14] via-[#070b14]/90 sm:via-[#070b14]/80 md:via-[#070b14]/70 to-[#070b14]/30" 
            aria-hidden="true" 
          />
          <div 
            className="absolute inset-0 bg-gradient-to-t from-[#090d16] via-transparent to-[#070b14]/60" 
            aria-hidden="true" 
          />
          {/* Subtle mobile contrast backing */}
          <div 
            className="absolute inset-0 bg-[#070b14]/40 sm:hidden" 
            aria-hidden="true" 
          />
        </div>

        {/* Hero Content: Aligned to Left, Generous Room to Breathe */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-20 lg:py-28 min-h-[500px] sm:min-h-[580px] lg:min-h-[640px] flex items-center">
          <motion.div 
            className="max-w-2xl lg:max-w-3xl space-y-5 sm:space-y-6"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Terminal Badge */}
            <motion.div 
              variants={itemVariants} 
              className="inline-flex items-center space-x-2 text-xs font-mono text-sky-400 bg-sky-950/60 border border-sky-800/50 px-3 py-1 rounded-full backdrop-blur-md shadow-sm"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse"></span>
              <span className="tracking-wider uppercase">Automotive Valuation Terminal</span>
            </motion.div>

            {/* Headline with restrained cyan accent and balanced line breaking */}
            <motion.h1 
              variants={itemVariants}
              className="text-xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-snug sm:leading-tight"
            >
              Accurate used-car <br className="sm:hidden" />
              valuations based on <br className="hidden sm:inline" />
              <span className="text-sky-400">real market data.</span>
            </motion.h1>

            {/* Description */}
            <motion.p 
              variants={itemVariants}
              className="text-sm sm:text-base lg:text-lg text-slate-200 max-w-2xl leading-relaxed font-normal"
            >
              AutoValue calculates fair market value using machine learning regression and observed comparable listings. Enter your vehicle's details to see a reliable price estimate and uncertainty range.
            </motion.p>

            {/* Clear Primary & Secondary CTAs */}
            <motion.div 
              variants={itemVariants}
              className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 sm:gap-4 pt-1"
            >
              <button
                type="button"
                onClick={() => navigate('/valuation')}
                className="btn-primary py-3 sm:py-3.5 px-6 sm:px-7 text-sm font-semibold flex items-center justify-center space-x-2 shadow-xl shadow-sky-500/25 transition-transform active:scale-[0.985]"
              >
                <span>Estimate a Car's Value</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <Link
                to="/methodology"
                className="inline-flex items-center justify-center text-xs sm:text-sm font-medium text-slate-300 hover:text-white transition-colors px-3 py-2 sm:py-2.5 rounded-lg hover:bg-white/5"
              >
                <span>See how our valuation works</span>
                <span className="ml-1.5">→</span>
              </Link>
            </motion.div>

            {/* Trust signals */}
            <motion.div 
              variants={itemVariants}
              className="pt-5 sm:pt-6 border-t border-white/10 flex flex-wrap items-center gap-y-2 gap-x-5 sm:gap-x-6 text-xs text-slate-300"
            >
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0" />
                <span>80% conformal uncertainty interval</span>
              </div>
              <div className="flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-sky-400 shrink-0" />
                <span>XGBoost regression model (v002)</span>
              </div>
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-sky-400 shrink-0" />
                <span>Direct nearest-neighbor comparables</span>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 2. THREE STEPS: HOW DO I USE IT? */}
      {/* ========================================================================= */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
        <div>
          <span className="text-xs font-mono text-sky-400 uppercase tracking-wider block mb-1">
            WORKFLOW
          </span>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            How AutoValue Works
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-xl">
            A three-step valuation workflow designed for clear, reproducible automotive pricing.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Step 1 */}
          <div className="card-surface p-5 space-y-3 transition-colors duration-150 hover:border-[#273553]">
            <div className="w-8 h-8 rounded-lg bg-[#0d1322] border border-[#273553] flex items-center justify-center text-sky-400 font-mono font-bold text-xs">
              01
            </div>
            <h3 className="text-sm font-semibold text-white">Enter Vehicle Details</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Select manufacturer, model, registration year, cumulative odometer mileage, transmission, and city location.
            </p>
          </div>

          {/* Step 2 */}
          <div className="card-surface p-5 space-y-3 transition-colors duration-150 hover:border-[#273553]">
            <div className="w-8 h-8 rounded-lg bg-[#0d1322] border border-[#273553] flex items-center justify-center text-sky-400 font-mono font-bold text-xs">
              02
            </div>
            <h3 className="text-sm font-semibold text-white">Machine Learning Inference</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Our XGBoost regression model calculates an expected price, while conformal bounds compute an 80% uncertainty interval.
            </p>
          </div>

          {/* Step 3 */}
          <div className="card-surface p-5 space-y-3 transition-colors duration-150 hover:border-[#273553]">
            <div className="w-8 h-8 rounded-lg bg-[#0d1322] border border-[#273553] flex items-center justify-center text-sky-400 font-mono font-bold text-xs">
              03
            </div>
            <h3 className="text-sm font-semibold text-white">Review Evidence & Comps</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Inspect matching comparable records from the market dataset, examine SHAP price factors, and bookmark for comparison.
            </p>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 3. SAMPLE VALUATION BENCHMARK PREVIEW (PRESERVED PRODUCT OUTPUT TRUTH) */}
      {/* ========================================================================= */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-t border-[#1c263c] pt-12 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <span className="text-xs font-mono text-sky-400 uppercase tracking-wider block mb-1">
              REPORT PREVIEW
            </span>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Sample Valuation Output
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-xl">
              Inspect an illustrative benchmark report showing our conformal prediction interval and comparable breakdown.
            </p>
          </div>
          <span className="badge-neutral font-mono text-[11px] self-start sm:self-auto">
            Illustrative Benchmark Spec
          </span>
        </div>

        <motion.div 
          className="max-w-4xl mx-auto"
          variants={cardVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-40px" }}
        >
          <div className="card-surface overflow-hidden border-[#273553] shadow-2xl shadow-black/60 group">
            <div className="p-5 sm:p-6 space-y-4 bg-[#0d1322]">
              <div className="flex items-center justify-between pb-3 border-b border-[#1c263c]">
                <div className="flex items-center space-x-2 text-xs text-slate-400">
                  <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
                  <span className="font-semibold text-white">Valuation Output Preview</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-[#090d16] border border-[#273553] text-[10px] font-mono text-slate-300">
                    <Sparkles className="w-3 h-3 text-sky-400" />
                    <span>Editorial Benchmark</span>
                  </span>
                  <span className="badge-neutral font-mono text-[10px]">
                    Model Engine v002
                  </span>
                </div>
              </div>

              {/* Vehicle Title */}
              <div>
                <h3 className="text-lg font-bold text-white">2021 Hyundai Creta SX</h3>
                <p className="text-xs text-slate-400 mt-0.5">1.5 CRDi Diesel · Manual · 38,000 km · Pune</p>
              </div>

              {/* Estimated Market Value */}
              <div className="p-4 rounded-lg bg-[#090e1a] border border-[#1c263c] space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Estimated Fair Market Value
                </span>
                <div className="text-3xl font-extrabold text-white num-tabular tracking-tight">
                  ₹ 11.84 Lakh
                </div>
                <p className="text-[11px] text-slate-400 pt-0.5">
                  Point estimate from trained regression model.
                </p>
              </div>

              {/* Uncertainty Interval & Comparable Spread */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-[#090e1a] border border-[#1c263c]">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    80% Prediction Interval
                  </span>
                  <p className="font-bold text-sky-300 num-tabular text-sm">₹ 11.02L – ₹ 12.65L</p>
                  <span className="text-[10px] text-slate-500">Holdout residuals</span>
                </div>

                <div className="p-3 rounded-lg bg-[#090e1a] border border-[#1c263c]">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Observed Market Comps
                  </span>
                  <p className="font-bold text-slate-200 num-tabular text-sm">10 Matching Cars</p>
                  <span className="text-[10px] text-slate-500">Median ₹ 11.75L</span>
                </div>
              </div>

              {/* Preview Actions */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => navigate('/valuation')}
                  className="w-full py-2.5 px-3 rounded-lg bg-[#141c30] hover:bg-[#1a2540] border border-[#273553] text-xs font-medium text-sky-300 transition-colors flex items-center justify-center space-x-1.5 active:scale-[0.985]"
                >
                  <span>Value your vehicle now</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ========================================================================= */}
      {/* 4. EXPLORE MARKET DATA & METHODOLOGY */}
      {/* ========================================================================= */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-t border-[#1c263c] pt-12">
        <div className="card-surface p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <h2 className="text-lg font-bold text-white">
              Interested in broader market price movements?
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Explore asking-price distributions, interquartile spreads, and historical price trajectories across different OEMs and cities in our Market section.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/market"
              className="btn-secondary py-2.5 px-4 text-xs flex items-center space-x-1.5"
            >
              <TrendingUp className="w-3.5 h-3.5 text-sky-400" />
              <span>Explore Market Trends</span>
            </Link>
            <Link
              to="/methodology"
              className="text-xs text-slate-400 hover:text-white px-2 py-1"
            >
              Read Methodology →
            </Link>
          </div>
        </div>
      </section>
    </PageTransition>
  );
};
