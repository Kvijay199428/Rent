import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import MainLayout from './components/layout/MainLayout';
import { Toaster } from '@/components/ui/sonner';
import BrandWave from '@shared/loading/BrandWave';

// Pages (lazy-loaded for route-level code splitting)
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Tenants = lazy(() => import('./pages/Tenants'));
const Billing = lazy(() => import('./pages/Billing'));
const Settings = lazy(() => import('./pages/Settings'));
const History = lazy(() => import('./pages/History'));
const Backups = lazy(() => import('./pages/Backups'));
const Archive = lazy(() => import('./pages/Archive'));
const SecuritySettingsPage = lazy(() => import('./pages/SecuritySettingsPage'));
const ChangePasswordPage = lazy(() => import('./pages/ChangePasswordPage'));
const ActivityPage = lazy(() => import('./pages/ActivityPage'));
const LandlordAuthPage = lazy(() => import('./pages/LandlordAuthPage'));
const PrivacyPolicyPage = lazy(() => import('./pages/PrivacyPolicyPage'));
const PrivacyConsentPage = lazy(() => import('./pages/PrivacyConsentPage'));
const TermsConditionsPage = lazy(() => import('./pages/TermsConditionsPage'));
const Login = lazy(() => import('./pages/Login'));
const AdminSetupPage = lazy(() => import('./pages/AdminSetupPage'));
const SetupPage = lazy(() => import('./pages/SetupPage'));
import { APP_BASE } from './lib/runtime';

function FullPageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <BrandWave size="lg" stacked label="PropAura" />
    </div>
  );
}

function suspensed(node: React.ReactNode) {
  return <Suspense fallback={<FullPageLoader />}>{node}</Suspense>;
}

function RequirePrivacyConsent({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, privacyConsented, termsConsented } = useAuth();
  if (isAuthenticated && (privacyConsented === false || termsConsented === false)) {
    return <Navigate to="/privacy-consent" replace />;
  }
  return <>{children}</>;
}

function RequireSetup({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, privacyConsented, termsConsented, setupCompleted, setupSkipped } = useAuth();
  if (
    isAuthenticated &&
    !isLoading &&
    privacyConsented !== false &&
    termsConsented !== false &&
    !setupCompleted &&
    !setupSkipped
  ) {
    return <Navigate to="/setup" replace />;
  }
  return <>{children}</>;
}

function guarded(page: React.ReactNode) {
  return suspensed(
    <RequirePrivacyConsent>
      <RequireSetup>{page}</RequireSetup>
    </RequirePrivacyConsent>,
  );
}

function App() {
  const basename = APP_BASE === "/" ? "/" : APP_BASE.replace(/\/+$/, "");

  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter basename={basename}>
          <Routes>
            {/* Public/Auth Routes */}
            <Route path="/login" element={suspensed(<LandlordAuthPage defaultTab="login" />)} />
            <Route path="/signup" element={suspensed(<LandlordAuthPage defaultTab="signup" />)} />
            <Route path="/change-password" element={suspensed(<ChangePasswordPage />)} />
            <Route path="/privacy-policy" element={suspensed(<PrivacyPolicyPage />)} />
            <Route path="/privacy-consent" element={suspensed(<PrivacyConsentPage />)} />
            <Route path="/terms" element={suspensed(<TermsConditionsPage />)} />
            <Route path="/admin/login" element={suspensed(<Login />)} />
            <Route path="/admin/setup" element={suspensed(<AdminSetupPage />)} />

            {/* Protected Routes inside MainLayout — no UUID prefix */}
            <Route element={<MainLayout />}>
              <Route path="/" element={guarded(<Dashboard />)} />
              <Route path="/dashboard" element={guarded(<Dashboard />)} />
              <Route path="/tenants" element={guarded(<Tenants />)} />
              <Route path="/billing" element={guarded(<Billing />)} />
              <Route path="/settings" element={guarded(<Settings />)} />
              <Route path="/history" element={guarded(<History />)} />
              <Route path="/backups" element={guarded(<Backups />)} />
              <Route path="/archive" element={guarded(<Archive />)} />
              <Route path="/security" element={guarded(<SecuritySettingsPage />)} />
              <Route path="/activity" element={guarded(<ActivityPage />)} />
            </Route>

            {/* Initial setup wizard — standalone (RequireSetup redirects here) */}
            <Route path="/setup" element={suspensed(<SetupPage />)} />
            <Route path="/:uuid/setup" element={suspensed(<SetupPage />)} />

            {/* Protected Routes with UUID prefix — for when basename doesn't include UUID */}
            <Route path="/:uuid" element={<MainLayout />}>
              <Route index element={guarded(<Dashboard />)} />
              <Route path="dashboard" element={guarded(<Dashboard />)} />
              <Route path="tenants" element={guarded(<Tenants />)} />
              <Route path="billing" element={guarded(<Billing />)} />
              <Route path="settings" element={guarded(<Settings />)} />
              <Route path="history" element={guarded(<History />)} />
              <Route path="backups" element={guarded(<Backups />)} />
              <Route path="archive" element={guarded(<Archive />)} />
              <Route path="security" element={guarded(<SecuritySettingsPage />)} />
              <Route path="activity" element={guarded(<ActivityPage />)} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Toaster position="top-right" />
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  );
}

export default App;