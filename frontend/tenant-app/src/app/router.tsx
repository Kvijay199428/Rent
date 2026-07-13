import { createBrowserRouter } from 'react-router-dom';
import PublicTenantPage from '../pages/PublicTenantPage';

export const router = createBrowserRouter([
  {
    path: '/t/:viewToken',
    element: <PublicTenantPage />
  },
], {
  basename: "/rent/t",
});
