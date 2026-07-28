import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
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
import Login from './pages/Login';
import AdminSetupPage from './pages/AdminSetupPage';
import { APP_BASE } from './lib/runtime';

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
            <Route path="/admin/login" element={<Login />} />
            <Route path="/admin/setup" element={<AdminSetupPage />} />
            
            {/* Protected Routes inside MainLayout — no UUID prefix */}
            <Route element={<MainLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/tenants" element={<Tenants />} />
              <Route path="/billing" element={<Billing />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/history" element={<History />} />
              <Route path="/backups" element={<Backups />} />
              <Route path="/archive" element={<Archive />} />
              <Route path="/security" element={<SecuritySettingsPage />} />
              <Route path="/activity" element={<ActivityPage />} />
            </Route>

            {/* Protected Routes with UUID prefix — for when basename doesn't include UUID */}
            <Route path="/:uuid" element={<MainLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="tenants" element={<Tenants />} />
              <Route path="billing" element={<Billing />} />
              <Route path="settings" element={<Settings />} />
              <Route path="history" element={<History />} />
              <Route path="backups" element={<Backups />} />
              <Route path="archive" element={<Archive />} />
              <Route path="security" element={<SecuritySettingsPage />} />
              <Route path="activity" element={<ActivityPage />} />
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
