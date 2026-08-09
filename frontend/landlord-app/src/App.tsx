import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import MainLayout from './components/layout/MainLayout';
import { Toaster } from '@/components/ui/sonner';

// Pages
import Dashboard from './pages/Dashboard';
import Tenants from './pages/Tenants';
import Billing from './pages/Billing';
import Settings from './pages/Settings';
import History from './pages/History';
import Backups from './pages/Backups';
import Archive from './pages/Archive';
import SecuritySettingsPage from './pages/SecuritySettingsPage';
import ChangePasswordPage from './pages/ChangePasswordPage';
import ActivityPage from './pages/ActivityPage';
import LandlordLoginPage from './pages/LandlordLoginPage';
import LandlordSignupPage from './pages/LandlordSignupPage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import PrivacyConsentPage from './pages/PrivacyConsentPage';
import Login from './pages/Login';
import AdminSetupPage from './pages/AdminSetupPage';
import { APP_BASE } from './lib/runtime';

function RequirePrivacyConsent({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, privacyConsented } = useAuth();
  if (isAuthenticated && privacyConsented === false) {
    return <Navigate to="/privacy-consent" replace />;
  }
  return <>{children}</>;
}

function App() {
  const basename = APP_BASE === "/" ? "/" : APP_BASE.replace(/\/+$/, "");

  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter basename={basename}>
          <Routes>
            {/* Public/Auth Routes */}
            <Route path="/login" element={<LandlordLoginPage />} />
            <Route path="/signup" element={<LandlordSignupPage />} />
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
            <Route path="/privacy-consent" element={<PrivacyConsentPage />} />
            <Route path="/admin/login" element={<Login />} />
            <Route path="/admin/setup" element={<AdminSetupPage />} />
            
            {/* Protected Routes inside MainLayout — no UUID prefix */}
            <Route element={<MainLayout />}>
              <Route path="/" element={<RequirePrivacyConsent><Dashboard /></RequirePrivacyConsent>} />
              <Route path="/dashboard" element={<RequirePrivacyConsent><Dashboard /></RequirePrivacyConsent>} />
              <Route path="/tenants" element={<RequirePrivacyConsent><Tenants /></RequirePrivacyConsent>} />
              <Route path="/billing" element={<RequirePrivacyConsent><Billing /></RequirePrivacyConsent>} />
              <Route path="/settings" element={<RequirePrivacyConsent><Settings /></RequirePrivacyConsent>} />
              <Route path="/history" element={<RequirePrivacyConsent><History /></RequirePrivacyConsent>} />
              <Route path="/backups" element={<RequirePrivacyConsent><Backups /></RequirePrivacyConsent>} />
              <Route path="/archive" element={<RequirePrivacyConsent><Archive /></RequirePrivacyConsent>} />
              <Route path="/security" element={<RequirePrivacyConsent><SecuritySettingsPage /></RequirePrivacyConsent>} />
              <Route path="/activity" element={<RequirePrivacyConsent><ActivityPage /></RequirePrivacyConsent>} />
            </Route>

            {/* Protected Routes with UUID prefix — for when basename doesn't include UUID */}
            <Route path="/:uuid" element={<MainLayout />}>
              <Route index element={<RequirePrivacyConsent><Dashboard /></RequirePrivacyConsent>} />
              <Route path="dashboard" element={<RequirePrivacyConsent><Dashboard /></RequirePrivacyConsent>} />
              <Route path="tenants" element={<RequirePrivacyConsent><Tenants /></RequirePrivacyConsent>} />
              <Route path="billing" element={<RequirePrivacyConsent><Billing /></RequirePrivacyConsent>} />
              <Route path="settings" element={<RequirePrivacyConsent><Settings /></RequirePrivacyConsent>} />
              <Route path="history" element={<RequirePrivacyConsent><History /></RequirePrivacyConsent>} />
              <Route path="backups" element={<RequirePrivacyConsent><Backups /></RequirePrivacyConsent>} />
              <Route path="archive" element={<RequirePrivacyConsent><Archive /></RequirePrivacyConsent>} />
              <Route path="security" element={<RequirePrivacyConsent><SecuritySettingsPage /></RequirePrivacyConsent>} />
              <Route path="activity" element={<RequirePrivacyConsent><ActivityPage /></RequirePrivacyConsent>} />
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
