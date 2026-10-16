import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';

import { LandingPage } from './pages/LandingPage';
import { ValuationPage } from './pages/ValuationPage';
import { ResultsPage } from './pages/ResultsPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { SavedVehiclesPage } from './pages/SavedVehiclesPage';
import { ComparisonPage } from './pages/ComparisonPage';
import { ValuationReportPage } from './pages/ValuationReportPage';
import { SharedReportPage } from './pages/SharedReportPage';
import { MethodologyPage } from './pages/MethodologyPage';
import { MarketPage } from './pages/MarketPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { GaragePage } from './pages/GaragePage';
import './App.css';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-[#090d16] text-slate-100">
          <Navbar />
          <main className="flex-grow">
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/valuation" element={<ValuationPage />} />
              <Route path="/results" element={<ResultsPage />} />
              <Route path="/market" element={<MarketPage />} />
              <Route path="/intelligence" element={<MarketPage />} />
              <Route path="/methodology" element={<MethodologyPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/compare" element={<ComparisonPage />} />
              <Route path="/shared/:token" element={<SharedReportPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />


              {/* Authenticated Routes */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/history"
                element={
                  <ProtectedRoute>
                    <HistoryPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/saved-vehicles"
                element={
                  <ProtectedRoute>
                    <SavedVehiclesPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/garage"
                element={
                  <ProtectedRoute>
                    <GaragePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/valuation/:id"
                element={
                  <ProtectedRoute>
                    <ValuationReportPage />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
