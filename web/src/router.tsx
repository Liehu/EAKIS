import { createBrowserRouter } from 'react-router-dom';
import AppLayout from '@/components/Layout/AppLayout';
import Dashboard from '@/pages/Dashboard';
import Keywords from '@/pages/Keywords';
import Assets from '@/pages/Assets';
import Interfaces from '@/pages/Interfaces';
import Pentest from '@/pages/Pentest';
import Vulnerabilities from '@/pages/Vulnerabilities';
import Reports from '@/pages/Reports';
import Settings from '@/pages/Settings';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'keywords', element: <Keywords /> },
      { path: 'assets', element: <Assets /> },
      { path: 'interfaces', element: <Interfaces /> },
      { path: 'pentest', element: <Pentest /> },
      { path: 'vulnerabilities', element: <Vulnerabilities /> },
      { path: 'reports', element: <Reports /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
