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
import AdminLoginPage from './pages/AdminLoginPage';
import AdminSetupPage from './pages/AdminSetupPage';
import SecuritySettingsPage from './pages/SecuritySettingsPage';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter basename="/rent/admin">
          <Routes>
            {/* Public/Auth Routes */}
            <Route path="/login" element={<AdminLoginPage />} />
            <Route path="/setup" element={<AdminSetupPage />} />
            
            {/* Protected Routes inside MainLayout */}
            <Route element={<MainLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/tenants" element={<Tenants />} />
              <Route path="/billing" element={<Billing />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/history" element={<History />} />
              <Route path="/backups" element={<Backups />} />
              <Route path="/archive" element={<Archive />} />
              <Route path="/security" element={<SecuritySettingsPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Toaster position="top-right" />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
