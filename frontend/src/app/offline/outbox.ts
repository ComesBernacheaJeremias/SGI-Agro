/**
 * Cola de envíos pendientes de la carga sin conexión (ADR-006), guardada en IndexedDB.
 *
 * Solo altas de labores/cosechas, comprobantes de stock y preparaciones. Cada registro lleva
 * el `id` generado en el dispositivo: reenviarlo no duplica (el servidor devuelve el existente).
 * Al sincronizar: OK → se saca de la cola; error de negocio (ej. stock insuficiente) → queda
 * "con error" para que el usuario lo vea y lo descarte; sin red → se reintenta después.
 */
import { createStore, del, entries, set } from 'idb-keyval';

import { api } from '@/api/client';
import { ApiError, unwrap } from '@/api/errors';

export type OutboxKind = 'field_operation' | 'stock_document' | 'production_order';

export type OutboxItem = {
  id: string;
  kind: OutboxKind;
  path: string;
  body: Record<string, unknown>;
  /** Para mostrar en la lista: "Labor · Aplicación · 27/09/2026". */
  label: string;
  createdAt: string;
  status: 'pending' | 'error';
  error?: string;
};

const store = createStore('sgi-offline', 'outbox');
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((listener) => listener());

export const outbox = {
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  async list(): Promise<OutboxItem[]> {
    const items = (await entries<string, OutboxItem>(store)).map(([, item]) => item);
    return items.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  },

  async add(item: Omit<OutboxItem, 'createdAt' | 'status'>): Promise<void> {
    await set(item.id, { ...item, createdAt: new Date().toISOString(), status: 'pending' }, store);
    notify();
  },

  async discard(id: string): Promise<void> {
    await del(id, store);
    notify();
  },
};

/** Sin red (el servidor no respondió): distinto de un error que devolvió la API. */
export function isNetworkError(err: unknown): boolean {
  return err instanceof TypeError || (err instanceof ApiError && err.status === 0);
}

const untyped = api as unknown as {
  POST: (
    path: string,
    init?: object,
  ) => Promise<{ data?: unknown; error?: unknown; response: Response }>;
};

let syncing: Promise<number> | null = null;

/** Envía los pendientes en orden. Devuelve cuántos se enviaron bien. */
export function syncOutbox(): Promise<number> {
  syncing ??= (async () => {
    let sent = 0;
    for (const item of await outbox.list()) {
      if (item.status !== 'pending') continue;
      try {
        unwrap(await untyped.POST(item.path, { body: item.body }));
        await del(item.id, store);
        sent += 1;
      } catch (err) {
        if (isNetworkError(err)) break; // sigue sin señal: se reintenta más tarde
        const message = err instanceof Error ? err.message : 'No se pudo enviar.';
        await set(item.id, { ...item, status: 'error', error: message }, store);
      }
      notify();
    }
    return sent;
  })().finally(() => {
    syncing = null;
  });
  return syncing;
}
