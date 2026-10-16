import React from 'react';
import { Link } from 'react-router-dom';
import { Database, ShieldCheck, Car, Cpu } from 'lucide-react';

const CURRENT_YEAR = 2026;

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-[#1c263c] bg-[#070b14] mt-20 text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Brand & Purpose */}
          <div className="space-y-3 md:col-span-1">
            <Link to="/" className="flex items-center space-x-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#0d1322] border border-[#273553] flex items-center justify-center text-sky-400">
                <Car className="w-3.5 h-3.5" />
              </div>
              <span className="font-semibold text-base text-slate-100">
                Auto<span className="text-sky-400">Value</span>
              </span>
              <span className="text-[9px] font-mono tracking-widest uppercase px-1.5 py-0.2 rounded bg-sky-950/60 text-sky-400 border border-sky-800/60 font-semibold">
                PRO
              </span>
            </Link>
            <p className="text-xs text-slate-400 leading-relaxed">
              Automotive valuation terminal and marketplace intelligence engine combining machine learning with empirical comp evidence.
            </p>
            <div className="pt-1">
              <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-[#0d1322] border border-[#1c263c] text-[11px] text-slate-300">
                <Cpu className="w-3 h-3 text-sky-400" />
                <span>Engine: XGBoost v002</span>
              </div>
            </div>
          </div>

          {/* Platform Navigation */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200 mb-3.5">
              Terminal
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/valuation" className="hover:text-slate-200 transition-colors">
                  Valuation Engine
                </Link>
              </li>
              <li>
                <Link to="/market" className="hover:text-slate-200 transition-colors">
                  Market Dynamics
                </Link>
              </li>
              <li>
                <Link to="/compare" className="hover:text-slate-200 transition-colors">
                  Comparison Matrix
                </Link>
              </li>
              <li>
                <Link to="/methodology" className="hover:text-slate-200 transition-colors">
                  Valuation Methodology
                </Link>
              </li>
            </ul>
          </div>

          {/* User Account & Privacy */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200 mb-3.5 flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
              <span>Portfolio</span>
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/dashboard" className="hover:text-slate-200 transition-colors">
                  Portfolio Overview
                </Link>
              </li>
              <li>
                <Link to="/history" className="hover:text-slate-200 transition-colors">
                  Valuation History
                </Link>
              </li>
              <li>
                <Link to="/saved-vehicles" className="hover:text-slate-200 transition-colors">
                  Saved Bookmarks
                </Link>
              </li>
              <li>
                <Link to="/garage" className="hover:text-slate-200 transition-colors">
                  Garage Assets
                </Link>
              </li>
              <li>
                <Link to="/privacy" className="hover:text-slate-200 transition-colors">
                  Privacy & Data Rights
                </Link>
              </li>
            </ul>
          </div>

          {/* Model & Data Evidence */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200 mb-3.5 flex items-center space-x-1.5">
              <Database className="w-3.5 h-3.5 text-sky-400" />
              <span>Evidence Basis</span>
            </h4>
            <div className="space-y-2 text-slate-400">
              <p className="leading-relaxed">
                Calibrated on verified marketplace listings across 14 OEM brands with SHA-256 integrity validation.
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1 font-mono text-[10px]">
                <span className="px-2 py-0.5 rounded bg-[#0d1322] text-slate-300 border border-[#1c263c]">v0.3 Dataset</span>
                <span className="px-2 py-0.5 rounded bg-[#0d1322] text-slate-300 border border-[#1c263c]">Conformal Bounds</span>
                <span className="px-2 py-0.5 rounded bg-[#0d1322] text-slate-300 border border-[#1c263c]">SHAP Attribution</span>
              </div>
            </div>
          </div>
        </div>

        {/* Disclaimer Strip */}
        <div className="border-t border-[#1c263c] pt-6 space-y-3">
          <div className="p-3 rounded-lg bg-[#0d1322] border border-[#1c263c] text-[11px] text-slate-400 leading-relaxed">
            <span className="font-semibold text-slate-300">Methodology Notice:</span> AutoValue estimates represent statistical price expectations derived from gradient-boosted decision trees and observed active asking listings. Predictions do not constitute binding transaction commitments or formal bank appraisals.
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 pt-1">
            <p>© {CURRENT_YEAR} AutoValue Technologies. All rights reserved.</p>
            <div className="flex items-center space-x-4 mt-2 sm:mt-0 text-slate-400">
              <Link to="/privacy" className="hover:text-slate-200 transition-colors">
                Privacy Policy
              </Link>
              <span>•</span>
              <Link to="/methodology" className="hover:text-slate-200 transition-colors">
                Methodology
              </Link>
              <span>•</span>
              <span>Observed Market Evidence</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

