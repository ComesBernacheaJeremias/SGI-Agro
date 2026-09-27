/** Activos: recurso CRUD y opciones (tipos, medidores, estados). */
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { createCrudResource } from '@/shared/crud/resource';
import { formatDate } from '@/shared/format/date';
import { formatNumber } from '@/shared/format/number';

type S = components['schemas'];

export type Asset = S['AssetOut'];

export const assetsResource = createCrudResource<Asset, S['AssetCreate'], S['AssetUpdate']>({
  path: '/api/v1/assets',
  key: 'assets',
  label: 'activo',
  table: 'assets',
});

export function useAssetOptions() {
  return useQuery({
    queryKey: ['asset-options'],
    queryFn: async () => unwrap(await api.GET('/api/v1/assets-options')),
    staleTime: Infinity,
  });
}

/** "h" o "km" según el medidor del activo. */
export const meterUnit = (meter: string) => (meter === 'km' ? 'km' : 'h');

// --- Uso y mantenimiento (F6) ---

export type Reading = S['ReadingOut'];
export type Plan = S['PlanOut'];
export type PlanStatus = S['PlanStatusOut'];
export type Maintenance = S['MaintenanceOut'];
export type MaintenanceIn = S['MaintenanceIn'];
export type AssetSheet = S['AssetSheetOut'];

export const readingsResource = createCrudResource<Reading, S['ReadingCreate'], S['ReadingUpdate']>(
  {
    path: '/api/v1/meter-readings',
    key: 'meter-readings',
    label: 'lectura',
    table: 'asset_meter_readings',
  },
);

export const plansResource = createCrudResource<Plan, S['PlanCreate'], S['PlanUpdate']>({
  path: '/api/v1/maintenance-plans',
  key: 'maintenance-plans',
  label: 'plan',
  table: 'maintenance_plans',
});

export function useAssetSheet(
  assetId: string | null,
  dateFrom: string | null,
  dateTo: string | null,
) {
  return useQuery({
    queryKey: ['asset-sheet', assetId, dateFrom, dateTo],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/asset-sheets/{id_}', {
          params: {
            path: { id_: assetId as string },
            query: { date_from: dateFrom, date_to: dateTo },
          },
        }),
      ),
    enabled: assetId !== null,
    placeholderData: keepPreviousData,
  });
}

export function useMaintenanceAlerts(enabled = true) {
  return useQuery({
    queryKey: ['maintenance-alerts'],
    queryFn: async () => unwrap(await api.GET('/api/v1/maintenance-alerts')),
    enabled,
    refetchInterval: 5 * 60_000,
  });
}

const byId = (id: string) => ({ params: { path: { id_: id } } });

export const maintenancesApi = {
  create: async (body: MaintenanceIn) => unwrap(await api.POST('/api/v1/maintenances', { body })),
  update: async (id: string, body: MaintenanceIn) =>
    unwrap(await api.PUT('/api/v1/maintenances/{id_}', { ...byId(id), body })),
  cancel: async (id: string) =>
    unwrap(await api.POST('/api/v1/maintenances/{id_}/cancel', byId(id))),
};

/** Después de guardar lecturas, planes o mantenimientos. */
export function useInvalidateAssets() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      [
        'asset-sheet',
        'maintenance-alerts',
        'maintenance-plans',
        'meter-readings',
        'dashboard',
        'reports',
        'stock',
        'stock-alerts',
        'kardex',
      ].map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
    );
}

export const PLAN_STATE = {
  ok: { label: 'Al día', color: 'green' },
  upcoming: { label: 'Próximo', color: 'orange' },
  overdue: { label: 'Vencido', color: 'red' },
} as const;

/** "Tractor 1 · Cambio de aceite: vencido (a las 1.250 h o el 01/03/2027)". */
export function planAlertText(p: PlanStatus): string {
  const parts = [
    p.due_reading && `a las ${formatNumber(p.due_reading, 'quantity')} ${p.unit}`,
    p.due_date && `el ${formatDate(p.due_date)}`,
  ].filter(Boolean);
  return `${p.asset.name} · ${p.plan.name}: ${PLAN_STATE[p.state].label.toLowerCase()} (${parts.join(' o ')})`;
}
