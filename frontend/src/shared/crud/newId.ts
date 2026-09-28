import { useState } from 'react';

/**
 * Id de un alta generado en el dispositivo; se renueva cada vez que se abre el formulario.
 * Si se corta la red justo al guardar y se reintenta, el servidor reconoce el id y no duplica.
 */
export function useNewId(opened: boolean): string {
  const [state, setState] = useState(() => ({ opened, id: crypto.randomUUID() }));
  if (opened !== state.opened) {
    setState({ opened, id: opened ? crypto.randomUUID() : state.id });
  }
  return state.id;
}
