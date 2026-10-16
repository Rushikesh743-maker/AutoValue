import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  Car, 
  LogOut, 
  Bookmark, 
  History, 
  LayoutDashboard, 
  Menu, 
  X, 
  ChevronDown, 
  Warehouse, 
  User 
} from 'lucide-react';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import { useAuth } from '../hooks/useAuth';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);

  const shouldReduceMotion = useReducedMotion();

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target as Node)) {
        setAccountMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setAccountMenuOpen(false);
        setMobileMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    setAccountMenuOpen(false);
    setMobileMenuOpen(false);
    navigate('/');
  };

  const isActive = (path: string) => {
    if (path === '/market') {
      return location.pathname === '/market' || location.pathname === '/intelligence';
    }
    return location.pathname === path;
  };

  const isAccountActive = () => {
    return ['/dashboard', '/history', '/saved-vehicles', '/garage'].includes(location.pathname);
  };

  const closeMenus = () => {
    setMobileMenuOpen(false);
    setAccountMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 bg-[#090d16]/95 backdrop-blur-md border-b border-[#1c263c]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo -> Home */}
        <Link 
          to="/" 
          onClick={closeMenus}
          className="flex items-center space-x-3 group focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 rounded p-1"
          aria-label="AutoValue Pro Homepage"
        >
          <div className="w-8 h-8 rounded-lg bg-[#0d1322] border border-[#273553] flex items-center justify-center text-sky-400 group-hover:border-sky-500/50 transition-colors">
            <Car className="w-4 h-4" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-base tracking-tight text-slate-100">
              Auto<span className="text-sky-400">Value</span>
            </span>
            <span className="text-[10px] font-mono tracking-widest uppercase px-1.5 py-0.5 rounded bg-sky-950/60 text-sky-400 border border-sky-800/60 font-semibold">
              PRO
            </span>
          </div>
        </Link>

        {/* Primary Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-1 text-sm font-medium">
          <Link
            to="/valuation"
            onClick={closeMenus}
            className={`px-3.5 py-2 rounded-lg transition-colors ${
              isActive('/valuation') 
                ? 'text-white bg-[#141c30] border border-[#273553]' 
                : 'text-slate-300 hover:text-white hover:bg-[#11182c]'
            }`}
          >
            <span>Valuation</span>
          </Link>

          <Link
            to="/market"
            onClick={closeMenus}
            className={`px-3.5 py-2 rounded-lg transition-colors flex items-center space-x-1.5 ${
              isActive('/market') 
                ? 'text-white bg-[#141c30] border border-[#273553]' 
                : 'text-slate-300 hover:text-white hover:bg-[#11182c]'
            }`}
          >
            <span>Market</span>
          </Link>

          <Link
            to="/compare"
            onClick={closeMenus}
            className={`px-3.5 py-2 rounded-lg transition-colors ${
              isActive('/compare') 
                ? 'text-white bg-[#141c30] border border-[#273553]' 
                : 'text-slate-300 hover:text-white hover:bg-[#11182c]'
            }`}
          >
            <span>Compare</span>
          </Link>
        </nav>

        {/* Desktop Right Side: Account Dropdown or Auth Actions */}
        <div className="hidden md:flex items-center space-x-3">
          {isAuthenticated ? (
            <div className="relative" ref={accountMenuRef}>
              <button
                type="button"
                onClick={() => setAccountMenuOpen(!accountMenuOpen)}
                aria-expanded={accountMenuOpen}
                aria-haspopup="true"
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                  isAccountActive() || accountMenuOpen
                    ? 'bg-[#141c30] border-sky-500/50 text-white'
                    : 'bg-[#0d1322] border-[#1c263c] text-slate-300 hover:text-white hover:border-[#273553]'
                }`}
              >
                <div className="w-5 h-5 rounded-full bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400">
                  <User className="w-3 h-3" />
                </div>
                <span>My Account</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${accountMenuOpen ? 'rotate-180 text-sky-400' : 'text-slate-400'}`} />
              </button>

              {/* My Account Menu */}
              <AnimatePresence>
                {accountMenuOpen && (
                  <motion.div 
                    initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: -4, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: -4, scale: 0.98 }}
                    transition={{ duration: shouldReduceMotion ? 0 : 0.15, ease: 'easeOut' }}
                    className="absolute right-0 mt-2 w-56 rounded-xl bg-[#0b101c] border border-[#273553] shadow-xl shadow-black/60 py-1.5 z-50 text-xs"
                    role="menu"
                  >
                    <div className="px-3 py-2 border-b border-[#1c263c]">
                      <p className="font-semibold text-white truncate">{user?.full_name || 'Account'}</p>
                      <p className="text-[11px] text-slate-400 truncate font-mono">{user?.email}</p>
                    </div>

                    <div className="py-1">
                      <Link
                        to="/dashboard"
                        role="menuitem"
                        onClick={closeMenus}
                        className={`flex items-center space-x-2.5 px-3 py-2 transition-colors ${
                          isActive('/dashboard') ? 'bg-[#141c30] text-sky-400' : 'text-slate-300 hover:text-white hover:bg-[#11182c]'
                        }`}
                      >
                        <LayoutDashboard className="w-3.5 h-3.5" />
                        <span>Dashboard</span>
                      </Link>

                      <Link
                        to="/history"
                        role="menuitem"
                        onClick={closeMenus}
                        className={`flex items-center space-x-2.5 px-3 py-2 transition-colors ${
                          isActive('/history') ? 'bg-[#141c30] text-sky-400' : 'text-slate-300 hover:text-white hover:bg-[#11182c]'
                        }`}
                      >
                        <History className="w-3.5 h-3.5" />
                        <span>Valuation History</span>
                      </Link>

                      <Link
                        to="/saved-vehicles"
                        role="menuitem"
                        onClick={closeMenus}
                        className={`flex items-center space-x-2.5 px-3 py-2 transition-colors ${
                          isActive('/saved-vehicles') ? 'bg-[#141c30] text-sky-400' : 'text-slate-300 hover:text-white hover:bg-[#11182c]'
                        }`}
                      >
                        <Bookmark className="w-3.5 h-3.5" />
                        <span>Saved Vehicles</span>
                      </Link>

                      <Link
                        to="/garage"
                        role="menuitem"
                        onClick={closeMenus}
                        className={`flex items-center space-x-2.5 px-3 py-2 transition-colors ${
                          isActive('/garage') ? 'bg-[#141c30] text-sky-400' : 'text-slate-300 hover:text-white hover:bg-[#11182c]'
                        }`}
                      >
                        <Warehouse className="w-3.5 h-3.5" />
                        <span>Garage</span>
                      </Link>
                    </div>

                    <div className="border-t border-[#1c263c] pt-1">
                      <button
                        type="button"
                        role="menuitem"
                        onClick={handleLogout}
                        className="w-full text-left flex items-center space-x-2.5 px-3 py-2 text-rose-300 hover:text-rose-200 hover:bg-rose-950/30 transition-colors"
                      >
                        <LogOut className="w-3.5 h-3.5" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <div className="flex items-center space-x-2.5">
              <Link
                to="/login"
                className="text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/valuation"
                className="btn-primary py-1.5 px-3.5 text-xs"
              >
                <span>Estimate Value</span>
              </Link>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Button */}
        <div className="md:hidden flex items-center">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-[#11182c] border border-[#1c263c]"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div 
            initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, height: 0 }}
            transition={{ duration: shouldReduceMotion ? 0 : 0.2, ease: [0.25, 1, 0.5, 1] }}
            className="md:hidden border-b border-[#1c263c] bg-[#0b101c] px-4 pt-3 pb-5 space-y-3 overflow-hidden"
          >
            <div className="space-y-1">
              <Link
                to="/valuation"
                onClick={closeMenus}
                className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                  isActive('/valuation') ? 'bg-[#141c30] text-sky-400 font-semibold' : 'text-slate-300 hover:bg-[#11182c]'
                }`}
              >
                Valuation
              </Link>

              <Link
                to="/market"
                onClick={closeMenus}
                className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                  isActive('/market') ? 'bg-[#141c30] text-sky-400 font-semibold' : 'text-slate-300 hover:bg-[#11182c]'
                }`}
              >
                Market
              </Link>

              <Link
                to="/compare"
                onClick={closeMenus}
                className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                  isActive('/compare') ? 'bg-[#141c30] text-sky-400 font-semibold' : 'text-slate-300 hover:bg-[#11182c]'
                }`}
              >
                Compare
              </Link>
            </div>

            {isAuthenticated ? (
              <div className="pt-3 border-t border-[#1c263c] space-y-1">
                <span className="px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                  My Account ({user?.email})
                </span>
                <Link
                  to="/dashboard"
                  onClick={closeMenus}
                  className="block px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-[#11182c]"
                >
                  Dashboard
                </Link>
                <Link
                  to="/history"
                  onClick={closeMenus}
                  className="block px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-[#11182c]"
                >
                  Valuation History
                </Link>
                <Link
                  to="/saved-vehicles"
                  onClick={closeMenus}
                  className="block px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-[#11182c]"
                >
                  Saved Vehicles
                </Link>
                <Link
                  to="/garage"
                  onClick={closeMenus}
                  className="block px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-[#11182c]"
                >
                  Garage
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-sm text-rose-300 hover:bg-rose-950/30 rounded-lg mt-2 flex items-center space-x-2"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="pt-3 border-t border-[#1c263c] flex flex-col space-y-2">
                <Link
                  to="/login"
                  onClick={closeMenus}
                  className="btn-secondary text-center py-2 text-xs"
                >
                  Sign In
                </Link>
                <Link
                  to="/valuation"
                  onClick={closeMenus}
                  className="btn-primary text-center py-2 text-xs"
                >
                  Estimate a Car's Value
                </Link>
              </div>
            )}

            <div className="pt-2 border-t border-[#1c263c]">
              <Link
                to="/methodology"
                onClick={closeMenus}
                className="text-xs text-slate-400 hover:text-white px-3 py-1 block"
              >
                Methodology & Transparency →
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};
