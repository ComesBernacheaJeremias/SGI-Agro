/** Llamadas a la API de inventario y avisos de stock mínimo. */
import { notifications } from '@mantine/notifications';
import {
  keepPreviousData,
  type QueryClient,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components, operations } from '@/api/schema';
import { formatMoney, formatNumber } from '@/shared/format/number';

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

/** Stock de un producto en cada almacén, de mayor a menor (para proponer de dónde sacarlo). */
const productStockQuery = (productId: string) => ({
  queryKey: [KEYS.stock, 'by-warehouse', productId],
  queryFn: async () => {
    const query = { product_id: productId, by_warehouse: true };
    const page = unwrap(await api.GET('/api/v1/stock', { params: { query } }));
    return page.items.sort((a, b) => Number(b.quantity) - Number(a.quantity));
  },
  staleTime: 30_000,
});

export function useProductStock(productId: string | null) {
  return useQuery({ ...productStockQuery(productId ?? ''), enabled: productId !== null });
}

/**
 * Almacén a proponer para sacar el producto: el que más stock tiene, si en el elegido no hay.
 * `null` = dejar el elegido (tiene stock, no hay en ninguno o no hay conexión).
 */
export async function suggestWarehouse(
  queryClient: QueryClient,
  productId: string,
  currentId: string | null,
): Promise<string | null> {
  if (!navigator.onLine) return null;
  try {
    const rows = await queryClient.fetchQuery(productStockQuery(productId));
    const available = rows.filter((r) => Number(r.quantity) > 0);
    if (available.some((r) => r.warehouse?.id === currentId)) return null;
    return available[0]?.warehouse?.id ?? null;
  } catch {
    return null;
  }
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

/** Color de los faltantes de stock (ámbar), en todo el sistema. */
export const STOCK_ALERT_COLOR = 'yellow';

/** Aviso "Necesitás comprar" con los productos que quedaron por debajo de su mínimo. */
export function notifyStockAlerts(alerts: StockAlert[]): void {
  if (alerts.length === 0) return;
  notifications.show({
    color: STOCK_ALERT_COLOR,
    title: 'Necesitás comprar',
    autoClose: 10_000,
    message: alerts.map(alertText).join(' · '),
  });
}

/**
 * "Incluye $ 2.000,00 de producción propia (costo del ciclo, provisorio)".
 * Ese valor es solo informativo (ADR-012): el stock contable la tiene a costo cero.
 */
export function ownProduceNote(value: string | number, provisional: boolean): string | null {
  if (Number(value) === 0) return null;
  const detail = provisional ? 'costo del cultivo, provisorio' : 'costo del cultivo';
  return `Incluye ${formatMoney(value)} de producción propia (${detail})`;
}

export function alertText(a: StockAlert): string {
  const q = (value: string) => `${formatNumber(value, 'quantity')} ${a.unit}`;
  return `${a.product.name}: hay ${q(a.quantity)}, mínimo ${q(a.min_stock)} (faltan ${q(a.missing)})`;
}
