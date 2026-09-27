/** Llamadas a la API de inventario y avisos de stock mínimo. */
import { notifications } from '@mantine/notifications';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components, operations } from '@/api/schema';
import { formatNumber } from '@/shared/format/number';

type S = components['schemas'];

export type StockRow = S['StockRowOut'];
export type StockAlert = S['StockAlertOut'];
export type DocumentSummary = S['DocumentSummaryOut'];
export type StockDocument = S['DocumentOut'];
export type DocumentIn = S['DocumentIn'];
export type DocumentType = S['DocumentType'];
export type Kardex = S['KardexOut'];

export type StockQuery = NonNullable<
  operations['list_stock_api_v1_stock_get']['parameters']['query']
>;
export type DocumentsQuery = NonNullable<
  operations['list_documents_api_v1_stock_documents_get']['parameters']['query']
>;
export type KardexQuery = operations['kardex_api_v1_stock_kardex_get']['parameters']['query'];

const KEYS = {
  stock: 'stock',
  documents: 'stock-documents',
  alerts: 'stock-alerts',
  kardex: 'kardex',
};

export function useInventoryOptions() {
  return useQuery({
    queryKey: ['inventory-options'],
    queryFn: async () => unwrap(await api.GET('/api/v1/stock/options')),
    staleTime: Infinity,
  });
}

export function useStock(query: StockQuery) {
  return useQuery({
    queryKey: [KEYS.stock, query],
    queryFn: async () => unwrap(await api.GET('/api/v1/stock', { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

export function useStockAlerts(enabled: boolean) {
  return useQuery({
    queryKey: [KEYS.alerts],
    queryFn: async () => unwrap(await api.GET('/api/v1/stock/alerts')),
    enabled,
    refetchInterval: 5 * 60_000,
  });
}

export function useDocuments(query: DocumentsQuery) {
  return useQuery({
    queryKey: [KEYS.documents, 'list', query],
    queryFn: async () => unwrap(await api.GET('/api/v1/stock-documents', { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

export function useKardex(query: KardexQuery | null) {
  return useQuery({
    queryKey: [KEYS.kardex, query],
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/stock/kardex', { params: { query: query as KardexQuery } })),
    enabled: query !== null,
  });
}

export async function fetchDocument(id: string): Promise<StockDocument> {
  return unwrap(await api.GET('/api/v1/stock-documents/{id_}', { params: { path: { id_: id } } }));
}

const byId = (id: string) => ({ params: { path: { id_: id } } });

export const documentsApi = {
  create: async (body: DocumentIn) => unwrap(await api.POST('/api/v1/stock-documents', { body })),
  update: async (id: string, body: DocumentIn) =>
    unwrap(await api.PUT('/api/v1/stock-documents/{id_}', { ...byId(id), body })),
  cancel: async (id: string) =>
    unwrap(await api.POST('/api/v1/stock-documents/{id_}/cancel', byId(id))),
};

/** Después de guardar: refresca stock, comprobantes, alertas y kardex. */
export function useInvalidateInventory() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      Object.values(KEYS).map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
    );
}

/** Aviso "Necesitás comprar" con los productos que quedaron en su mínimo o por debajo. */
export function notifyStockAlerts(alerts: StockAlert[]): void {
  if (alerts.length === 0) return;
  notifications.show({
    color: 'orange',
    title: 'Necesitás comprar',
    autoClose: 10_000,
    message: alerts.map(alertText).join(' · '),
  });
}

export function alertText(a: StockAlert): string {
  const q = (value: string) => `${formatNumber(value, 'quantity')} ${a.unit}`;
  return `${a.product.name}: hay ${q(a.quantity)}, mínimo ${q(a.min_stock)} (faltan ${q(a.missing)})`;
}
