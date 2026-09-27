/** Menú principal: un único lugar donde se declaran los módulos (ruta, nombre, ícono, etapa). */
import {
  IconBuildingWarehouse,
  IconCash,
  IconChartBar,
  IconDatabase,
  IconFileImport,
  IconFlask,
  IconHistory,
  IconLayoutDashboard,
  IconPlant2,
  IconReport,
  IconTractor,
  IconUsers,
  type Icon,
} from '@tabler/icons-react';

export type NavItem = {
  path: string;
  label: string;
  icon: Icon;
  /** Etapa del roadmap en que se implementa (mientras tanto muestra "Próximamente"). */
  stage: string;
  /** Permiso necesario para ver el ítem (sin permiso: oculto). */
  permission?: string;
};

export const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Tablero', icon: IconLayoutDashboard, stage: 'F5' },
  {
    path: '/produccion',
    label: 'Producción',
    icon: IconPlant2,
    stage: 'F3',
    permission: 'production:read',
  },
  {
    path: '/elaboracion',
    label: 'Elaboración',
    icon: IconFlask,
    stage: 'F3',
    permission: 'manufacturing:read',
  },
  {
    path: '/inventario',
    label: 'Inventario',
    icon: IconBuildingWarehouse,
    stage: 'F2',
    permission: 'inventory:read',
  },
  {
    path: '/comercial',
    label: 'Comercial y caja',
    icon: IconCash,
    stage: 'F4',
    permission: 'commercial:read',
  },
  {
    path: '/activos',
    label: 'Activos',
    icon: IconTractor,
    stage: 'F3',
    permission: 'assets:read',
  },
  {
    path: '/costos',
    label: 'Costos y rentabilidad',
    icon: IconChartBar,
    stage: 'F5',
    permission: 'costs:read',
  },
  { path: '/reportes', label: 'Reportes', icon: IconReport, stage: 'F5' },
  {
    path: '/maestros',
    label: 'Maestros',
    icon: IconDatabase,
    stage: 'F1',
    permission: 'masterdata:read',
  },
  { path: '/importar', label: 'Importar datos', icon: IconFileImport, stage: 'F7' },
  {
    path: '/usuarios',
    label: 'Usuarios y roles',
    icon: IconUsers,
    stage: 'F1',
    permission: 'users:read',
  },
  {
    path: '/historial',
    label: 'Historial',
    icon: IconHistory,
    stage: 'F1',
    permission: 'audit:read',
  },
];
