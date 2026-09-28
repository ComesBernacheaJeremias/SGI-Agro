/** Aviso de conexión: sin internet no se puede guardar (se sigue con los datos del celular). */
import { Badge, Tooltip } from '@mantine/core';
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
function useOnline(): boolean {
  return useSyncExternalStore(subscribe, () => navigator.onLine);
}

export function OfflineBadge() {
  if (useOnline()) return null;
  return (
    <Tooltip label="No se puede guardar hasta que vuelva la conexión. Podés usar los datos del celular.">
      <Badge color="red">Sin conexión</Badge>
    </Tooltip>
  );
}
