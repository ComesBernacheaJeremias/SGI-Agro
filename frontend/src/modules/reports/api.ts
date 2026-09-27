/** Reportes (catálogo, datos y exportación), costos de un ciclo y tablero. */
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import { saveFile } from '@/api/download';
import { unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';

type S = components['schemas'];

export type ReportInfo = S['ReportInfo'];
export type ReportFilter = S['ReportFilter'];
export type TableReport = S['TableReport'];
export type ReportColumn = S['ReportColumn'];
export type ReportRow = S['ReportRow'];
export type ReportLink = S['ReportLink'];
export type CycleCost = S['CycleCostOut'];
export type Dashboard = S['DashboardOut'];
export type ResultSummary = S['ResultOut'];

/** Valores de los filtros (nombre del parámetro → valor). */
export type ReportParams = Record<string, string | null>;

const clean = (params: ReportParams) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== null && v !== ''));

export function useReportCatalog() {
  return useQuery({
    queryKey: ['reports', 'catalog'],
    queryFn: async () => unwrap(await api.GET('/api/v1/reports')),
    staleTime: Infinity,
  });
}

export function useReport(key: string, params: ReportParams, enabled = true) {
  return useQuery({
    queryKey: ['reports', key, params],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/reports/{key}', {
          params: { path: { key }, query: clean(params) },
        }),
      ),
    placeholderData: keepPreviousData,
    enabled,
    retry: false,
  });
}

/** Descarga el reporte en Excel o PDF (con la sesión del usuario). */
export async function downloadReport(key: string, params: ReportParams, format: 'xlsx' | 'pdf') {
  const result = await api.GET('/api/v1/reports/{key}/export', {
    params: { path: { key }, query: { ...clean(params), format } },
    parseAs: 'blob',
  });
  saveFile(result, `${key}.${format}`);
}

/** Texto de una celda según el tipo de columna (mismas reglas que el Excel/PDF). */
export function formatCell(value: unknown, kind: ReportColumn['kind']): string {
  if (value === null || value === undefined || value === '') return '';
  switch (kind) {
    case 'money':
      return formatMoney(value as string);
    case 'quantity':
      return formatNumber(value as string, 'quantity');
    case 'percent':
      return `${formatNumber(value as string, 'quantity')} %`;
    case 'date':
      return formatDate(value as string);
    default:
      return String(value);
  }
}

export function useCycleCost(cycleId: string | null) {
  return useQuery({
    queryKey: ['costs', 'cycle', cycleId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/costs/cycles/{id_}', {
          params: { path: { id_: cycleId as string } },
        }),
      ),
    enabled: cycleId !== null,
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => unwrap(await api.GET('/api/v1/dashboard')),
  });
}
