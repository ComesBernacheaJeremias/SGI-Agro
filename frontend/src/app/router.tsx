import type { ReactNode } from 'react';
import { createBrowserRouter } from 'react-router-dom';

import { RequireAuth } from '@/app/auth/RequireAuth';
import { AppLayout } from '@/app/layout/AppLayout';
import { AssetsPage } from '@/modules/assets/AssetsPage';
import { AuditPage } from '@/modules/audit/AuditPage';
import { LoginPage } from '@/modules/auth/LoginPage';
import { CommercialPage } from '@/modules/commercial/CommercialPage';
import { CostsPage } from '@/modules/costs/CostsPage';
import { DashboardPage } from '@/modules/dashboard/DashboardPage';
import { ImportsPage } from '@/modules/imports/ImportsPage';
import { InventoryPage } from '@/modules/inventory/InventoryPage';
import { ManualPage } from '@/modules/manual/ManualPage';
import { ManufacturingPage } from '@/modules/manufacturing/ManufacturingPage';
import { MasterdataPage } from '@/modules/masterdata/MasterdataPage';
import { ProductionPage } from '@/modules/production/ProductionPage';
import { ProfilePage } from '@/modules/profile/ProfilePage';
import { ReportsPage } from '@/modules/reports/ReportsPage';
import { UsersPage } from '@/modules/users/UsersPage';

// Pantalla de cada ítem del menú (ver navigation.ts)
const PAGES: Record<string, ReactNode> = {
  '/': <DashboardPage />,
  '/costos': <CostsPage />,
  '/reportes': <ReportsPage />,
  '/importar': <ImportsPage />,
  '/produccion': <ProductionPage />,
  '/elaboracion': <ManufacturingPage />,
  '/activos': <AssetsPage />,
  '/inventario': <InventoryPage />,
  '/comercial': <CommercialPage />,
  '/maestros': <MasterdataPage />,
  '/usuarios': <UsersPage />,
  '/historial': <AuditPage />,
};

const moduleRoutes = Object.entries(PAGES).map(([path, element]) => ({ path, element }));

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  // Manual de uso: público (sirve también antes de entrar, ej. para instalar la app)
  { path: '/manual', element: <ManualPage /> },
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [...moduleRoutes, { path: '/perfil', element: <ProfilePage /> }],
  },
]);
