import { Outlet, Navigate } from 'react-router';
import { Toaster } from '@/components/ui/sonner';
import Sidebar from './Sidebar';
import Header from './Header';
import { useAuth } from '@/contexts/AuthContext';
import BroadcastBanner from '@/components/BroadcastBanner';
import NotificationBanner from '@/components/NotificationBanner';
import LoadingScreen from '@shared/loading/LoadingScreen';
import { PageTransition } from '@shared/motion/PageTransition';
import { ROUTES } from '@/lib/routes';

export default function MainLayout() {
  const { isAuthenticated, isLoading } = useAuth();

  if (!isLoading && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (isLoading) {
    return <LoadingScreen isLoading={true} />;
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <BroadcastBanner healthUrl={ROUTES.HEALTHCHECK} />
        <NotificationBanner />
        <main className="flex-1 p-4 lg:p-6 overflow-y-auto">
          <PageTransition>
            <Outlet />
          </PageTransition>
        </main>
      </div>
      <Toaster position="top-right" richColors />
    </div>
  );
}
