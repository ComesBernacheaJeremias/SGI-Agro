/** Estado de la conexión y caché persistente de consultas (para usar la app sin señal). */
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import type { Query } from '@tanstack/react-query';
import { createStore, del, get, set } from 'idb-keyval';
import { useSyncExternalStore } from 'react';

function subscribe(listener: () => void): () => void {
  window.addEventListener('online', listener);
  window.addEventListener('offline', listener);
  return () => {
    window.removeEventListener('online', listener);
    window.removeEventListener('offline', listener);
  };
}

/** `true` si el navegador tiene conexión. */
export function useOnline(): boolean {
  return useSyncExternalStore(subscribe, () => navigator.onLine);
}

const cache = createStore('sgi-offline', 'queries');

/** Las consultas se guardan en el dispositivo (IndexedDB) y se ven aunque no haya señal. */
export const queryPersister = createAsyncStoragePersister({
  storage: {
    getItem: (key) => get<string>(key, cache).then((v) => v ?? null),
    setItem: (key, value) => set(key, value, cache),
    removeItem: (key) => del(key, cache),
  },
});

/** Lo que no vale la pena guardar para usar sin conexión (pesado o que cambia siempre). */
const NOT_PERSISTED = new Set(['reports', 'audit', 'kardex', 'imports', 'costs', 'dashboard']);

export const PERSIST_OPTIONS = {
  persister: queryPersister,
  maxAge: 7 * 24 * 60 * 60 * 1000, // 7 días
  buster: 'v1',
  dehydrateOptions: {
    shouldDehydrateQuery: (query: Query) =>
      query.state.status === 'success' && !NOT_PERSISTED.has(String(query.queryKey[0])),
  },
};
