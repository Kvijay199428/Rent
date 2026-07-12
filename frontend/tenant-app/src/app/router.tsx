import { createBrowserRouter } from 'react-router-dom';
import PublicTenantPage from '../pages/PublicTenantPage';

export const router = createBrowserRouter([
  {
    path: '/t/:view_token',
    element: <PublicTenantPage />
  },
], {
  basename: "/rent/t",
});
