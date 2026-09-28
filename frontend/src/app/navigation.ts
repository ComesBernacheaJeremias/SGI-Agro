/** Menú principal: un único lugar donde se declaran los módulos (ruta, nombre, ícono, sección). */
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

export type NavSection = 'daily' | 'analysis' | 'admin';

export const NAV_SECTIONS: { key: NavSection; label: string }[] = [
  { key: 'daily', label: 'Día a día' },
  { key: 'analysis', label: 'Análisis' },
  { key: 'admin', label: 'Administración' },
];

export type NavItem = {
  path: string;
  label: string;
  icon: Icon;
  section: NavSection;
  /** Permiso necesario para ver el ítem (sin permiso: oculto). */
  permission?: string;
};

export const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Tablero', icon: IconLayoutDashboard, section: 'daily' },
  {
    path: '/produccion',
    label: 'Producción',
    icon: IconPlant2,
    section: 'daily',
    permission: 'production:read',
  },
  {
    path: '/elaboracion',
    label: 'Elaboración',
    icon: IconFlask,
    section: 'daily',
    permission: 'manufacturing:read',
  },
  {
    path: '/inventario',
    label: 'Inventario',
    icon: IconBuildingWarehouse,
    section: 'daily',
    permission: 'inventory:read',
  },
  {
    path: '/comercial',
    label: 'Comercial y caja',
    icon: IconCash,
    section: 'daily',
    permission: 'commercial:read',
  },
  {
    path: '/activos',
    label: 'Activos',
    icon: IconTractor,
    section: 'daily',
    permission: 'assets:read',
  },
  {
    path: '/costos',
    label: 'Costos y rentabilidad',
    icon: IconChartBar,
    section: 'analysis',
    permission: 'costs:read',
  },
  { path: '/reportes', label: 'Reportes', icon: IconReport, section: 'analysis' },
  {
    path: '/maestros',
    label: 'Maestros',
    icon: IconDatabase,
    section: 'admin',
    permission: 'masterdata:read',
  },
  { path: '/importar', label: 'Importar datos', icon: IconFileImport, section: 'admin' },
  {
    path: '/usuarios',
    label: 'Usuarios y roles',
    icon: IconUsers,
    section: 'admin',
    permission: 'users:read',
  },
  {
    path: '/historial',
    label: 'Historial',
    icon: IconHistory,
    section: 'admin',
    permission: 'audit:read',
  },
];
