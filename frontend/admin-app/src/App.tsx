import { Routes, Route, Navigate } from "react-router";
import { useAuth, AuthProvider } from "./contexts/AuthContext";
import BroadcastBanner from "@shared/BroadcastBanner";
import LoadingScreen from "@shared/loading/LoadingScreen";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import LandlordsPage from "./pages/LandlordsPage";
import LandlordDetailPage from "./pages/LandlordDetailPage";
import DataExplorerPage from "./pages/DataExplorerPage";
import SettingsPage from "./pages/SettingsPage";
import AuditLogsPage from "./pages/AuditLogsPage";
import FeedbackInboxPage from "./pages/FeedbackInboxPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { admin, loading } = useAuth();
  if (loading) {
    return <LoadingScreen isLoading={true} />;
  }
  if (!admin) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
      <Route path="/landlords" element={<RequireAuth><LandlordsPage /></RequireAuth>} />
      <Route path="/landlords/:id" element={<RequireAuth><LandlordDetailPage /></RequireAuth>} />
      <Route path="/explorer" element={<RequireAuth><DataExplorerPage /></RequireAuth>} />
      <Route path="/feedback" element={<RequireAuth><FeedbackInboxPage /></RequireAuth>} />
      <Route path="/audit-logs" element={<RequireAuth><AuditLogsPage /></RequireAuth>} />
      <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BroadcastBanner />
      <AppRoutes />
    </AuthProvider>
  );
}
