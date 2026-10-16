import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Trash2,
  Lock,
  Database,
  HelpCircle,
  AlertTriangle
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export const PrivacyPage: React.FC = () => {
  const { user, isAuthenticated, deleteAccount } = useAuth();
  const navigate = useNavigate();

  const [deleting, setDeleting] = useState(false);

  const handleDeleteAccount = async () => {
    const confirmation = window.prompt(
      'Type "DELETE" to permanently delete your AutoValue account and all associated valuation snapshots and bookmarks:'
    );
    if (confirmation !== 'DELETE') {
      alert('Account deletion cancelled.');
      return;
    }

    setDeleting(true);
    try {
      await deleteAccount();
      alert('Your account and associated personal data have been permanently deleted.');
      navigate('/');
    } catch (err: any) {
      alert(err.message || 'Failed to delete account.');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-canvas py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2">
            <ShieldCheck className="w-4 h-4 text-brand-400" />
            <span>Governance & Architecture</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Privacy Policy & Data Security
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-2 leading-relaxed">
            AutoValue operates on principles of statistical transparency, cryptographic credential storage, and explicit user sovereignty over saved snapshots.
          </p>
        </div>

        <div className="space-y-5">
          {/* Section 1 */}
          <div className="card-surface p-6">
            <h2 className="text-sm font-semibold text-white flex items-center space-x-2 mb-3">
              <Database className="w-4 h-4 text-brand-400" />
              <span>What Information Is Stored?</span>
            </h2>
            <div className="space-y-2 text-xs text-slate-300 leading-relaxed">
              <p>
                When you register an account, we store your normalized email address and a cryptographically salted password hash (using <strong>bcrypt with 12 cost rounds</strong>). We never store, log, or transmit plaintext credentials.
              </p>
              <p>
                When you save a valuation, we store an immutable snapshot of the vehicle attributes (make, model, year, mileage, city) and the resulting model prediction metrics (point estimate, conformal prediction interval, market median, and SHAP factor attributions).
              </p>
            </div>
          </div>

          {/* Section 2 */}
          <div className="card-surface p-6">
            <h2 className="text-sm font-semibold text-white flex items-center space-x-2 mb-3">
              <Lock className="w-4 h-4 text-emerald-400" />
              <span>Why Is Valuation History Preserved?</span>
            </h2>
            <div className="space-y-2 text-xs text-slate-300 leading-relaxed">
              <p>
                Valuation history allows users to track market depreciation, audit historical predictions against real sales, compare portfolio vehicles, and produce shareable verification links.
              </p>
              <p>
                Saved valuation snapshots are <strong>strictly immutable</strong>: future model iterations (e.g. v003) do not retroactively alter the parameters, intervals, or SHAP factors calculated when your report was generated.
              </p>
            </div>
          </div>

          {/* Section 3 */}
          <div className="card-surface p-6">
            <h2 className="text-sm font-semibold text-white flex items-center space-x-2 mb-3">
              <HelpCircle className="w-4 h-4 text-amber-400" />
              <span>Market Data Sources & Empirical Disclaimers</span>
            </h2>
            <div className="space-y-2 text-xs text-slate-300 leading-relaxed">
              <p>
                <strong>Observed asking prices vs. transaction prices:</strong> AutoValue collects publicly listed asking prices from vetted automotive marketplaces. Asking prices reflect seller expectations and do not account for unrecorded dealer discounts or trade-in adjustments.
              </p>
              <p>
                <strong>No guaranteed resale prices:</strong> AutoValue machine-learning estimates are statistical research tools. They do not constitute certified insurance appraisals, financing guarantees, or contractual bids.
              </p>
            </div>
          </div>

          {/* Section 4: Self-Service Deletion */}
          <div className="card-surface p-6 border-l-2 border-l-rose-500">
            <h2 className="text-sm font-semibold text-rose-400 flex items-center space-x-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>User Rights & Self-Service Data Purging</span>
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed mb-4">
              You maintain full ownership of your data. You may delete individual saved valuations and bookmarks at any time, or permanently purge your account and all associated records from our primary database.
            </p>

            {isAuthenticated ? (
              <div className="p-4 rounded-lg bg-surface-canvas border border-surface-border flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold text-white">Permanently Delete Account</p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Signed in as {user?.email}
                  </p>
                </div>
                <button
                  disabled={deleting}
                  onClick={handleDeleteAccount}
                  className="px-3.5 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold flex items-center space-x-2 disabled:opacity-50 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>{deleting ? 'Deleting...' : 'Delete Account & Purge Data'}</span>
                </button>
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                Sign in to manage your account or execute self-service data deletion.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

