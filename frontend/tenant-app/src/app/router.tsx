import { createBrowserRouter } from 'react-router-dom';
import PublicTenantPage from '../pages/PublicTenantPage';

export const router = createBrowserRouter([
  {
    path: '/:tenantId/:viewToken',
    element: <PublicTenantPage />
  },
], {
  basename: "/rent/t",
});
