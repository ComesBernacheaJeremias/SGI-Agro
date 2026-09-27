/** Llamadas a la API de Comercial y caja. */
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components, operations } from '@/api/schema';
import { createCrudResource } from '@/shared/crud/resource';

type S = components['schemas'];

export type Direction = S['Direction'];
export type CommercialDocument = S['CommercialDocumentOut'];
export type DocumentSummary = S['CommercialDocumentSummaryOut'];
export type DocumentIn = S['CommercialDocumentIn'];
export type Payment = S['PaymentOut'];
export type PaymentIn = S['PaymentIn'];
export type Balance = S['BalanceOut'];
export type CashMovement = S['CashMovementOut'];
export type CashMovementIn = S['CashMovementIn'];
export type ExpenseCategory = S['ExpenseCategoryOut'];
export type CashAccount = S['CashAccountOut'];

export type DocumentsQuery =
  operations['list_documents_api_v1_commercial_documents_get']['parameters']['query'];
export type PaymentsQuery = operations['list_payments_api_v1_payments_get']['parameters']['query'];
export type MovementsQuery = NonNullable<
  operations['list_movements_api_v1_cash_movements_get']['parameters']['query']
>;

export const expenseCategoriesResource = createCrudResource<
  ExpenseCategory,
  S['ExpenseCategoryIn'],
  S['ExpenseCategoryUpdate']
>({
  path: '/api/v1/expense-categories',
  key: 'expense-categories',
  label: 'categoría de gasto',
  table: 'expense_categories',
});

export const cashAccountsResource = createCrudResource<
  CashAccount,
  S['CashAccountIn'],
  S['CashAccountUpdate']
>({
  path: '/api/v1/cash-accounts',
  key: 'cash-accounts',
  label: 'cuenta',
  table: 'cash_accounts',
});

/** Textos según la operación: compra/proveedor/pago o venta/cliente/cobro. */
export const DIRECTION_TEXT = {
  purchase: { document: 'Compra', party: 'Proveedor', payment: 'Pago', payments: 'Pagos' },
  sale: { document: 'Venta', party: 'Cliente', payment: 'Cobro', payments: 'Cobros' },
} as const;

const KEYS = {
  documents: 'commercial-documents',
  payments: 'payments',
  accounts: 'current-accounts',
  cash: 'cash',
};

export function useCommercialOptions() {
  return useQuery({
    queryKey: ['commercial-options'],
    queryFn: async () => unwrap(await api.GET('/api/v1/commercial-options')),
    staleTime: Infinity,
  });
}

export function useDocuments(query: DocumentsQuery, enabled = true) {
  return useQuery({
    queryKey: [KEYS.documents, query],
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/commercial-documents', { params: { query } })),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: [KEYS.documents, 'detail', id],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/commercial-documents/{id_}', {
          params: { path: { id_: id as string } },
        }),
      ),
    enabled: id !== null,
  });
}

export function usePayments(query: PaymentsQuery) {
  return useQuery({
    queryKey: [KEYS.payments, query],
    queryFn: async () => unwrap(await api.GET('/api/v1/payments', { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

export function usePayment(id: string | null) {
  return useQuery({
    queryKey: [KEYS.payments, 'detail', id],
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/payments/{id_}', { params: { path: { id_: id as string } } })),
    enabled: id !== null,
  });
}

export function useBalances(direction: Direction) {
  return useQuery({
    queryKey: [KEYS.accounts, direction],
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/current-accounts', { params: { query: { direction } } })),
  });
}

export function useLedger(partyId: string | null, direction: Direction) {
  return useQuery({
    queryKey: [KEYS.accounts, direction, partyId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/current-accounts/{party_id}', {
          params: { path: { party_id: partyId as string }, query: { direction } },
        }),
      ),
    enabled: partyId !== null,
  });
}

/** Saldos de cajas y bancos (hoy o a una fecha). */
export function useCashBalances(at: string | null = null) {
  return useQuery({
    queryKey: [KEYS.cash, 'balances', at],
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/cash/balances', { params: { query: { at } } })),
  });
}

export function useCashStatement(accountId: string | null, dateFrom: string | null) {
  return useQuery({
    queryKey: [KEYS.cash, 'statement', accountId, dateFrom],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/cash/accounts/{id_}/statement', {
          params: { path: { id_: accountId as string }, query: { date_from: dateFrom } },
        }),
      ),
    enabled: accountId !== null,
  });
}

export function useMovement(id: string | null) {
  return useQuery({
    queryKey: [KEYS.cash, 'movements', 'detail', id],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/cash/movements/{id_}', {
          params: { path: { id_: id as string } },
        }),
      ),
    enabled: id !== null,
  });
}

export function useMovements(query: MovementsQuery) {
  return useQuery({
    queryKey: [KEYS.cash, 'movements', query],
    queryFn: async () => unwrap(await api.GET('/api/v1/cash/movements', { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

const byId = (id: string) => ({ params: { path: { id_: id } } });

export const documentsApi = {
  create: async (body: DocumentIn) =>
    unwrap(await api.POST('/api/v1/commercial-documents', { body })),
  update: async (id: string, body: DocumentIn) =>
    unwrap(await api.PUT('/api/v1/commercial-documents/{id_}', { ...byId(id), body })),
  cancel: async (id: string) =>
    unwrap(await api.POST('/api/v1/commercial-documents/{id_}/cancel', byId(id))),
};

export const paymentsApi = {
  create: async (body: PaymentIn) => unwrap(await api.POST('/api/v1/payments', { body })),
  update: async (id: string, body: PaymentIn) =>
    unwrap(await api.PUT('/api/v1/payments/{id_}', { ...byId(id), body })),
  cancel: async (id: string) => unwrap(await api.POST('/api/v1/payments/{id_}/cancel', byId(id))),
};

export const movementsApi = {
  create: async (body: CashMovementIn) =>
    unwrap(await api.POST('/api/v1/cash/movements', { body })),
  update: async (id: string, body: CashMovementIn) =>
    unwrap(await api.PUT('/api/v1/cash/movements/{id_}', { ...byId(id), body })),
  cancel: async (id: string) =>
    unwrap(await api.POST('/api/v1/cash/movements/{id_}/cancel', byId(id))),
};

/** Después de guardar: todo lo que puede haber cambiado (saldos, stock, costos de ciclos). */
export function useInvalidateCommercial() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      [
        ...Object.values(KEYS),
        'stock',
        'stock-documents',
        'stock-alerts',
        'kardex',
        'crop-cycles',
        'reports',
        'costs',
        'dashboard',
      ].map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
    );
}
