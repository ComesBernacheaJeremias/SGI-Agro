/**
 * Acciones que se abren con un enlace: `/pantalla?abrir=clave` (manual, tablero, avisos).
 * Un único lugar con todas; la pantalla de destino las atiende con `useOpenAction` (abre el
 * formulario o la pestaña) y `useActionTab` (elige la pestaña donde está el formulario).
 */
import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';

type ActionDef = {
  path: string;
  /** Texto del botón que lleva a la acción (ej. en el manual). */
  button: string;
  /** Solo lleva a la pantalla (no abre formulario ni pestaña): enlace sin `?abrir=`. */
  pageOnly?: true;
};

export const ACTIONS = {
  // Producción
  cultivo: { path: '/produccion', button: 'Empezar un cultivo' },
  labor: { path: '/produccion', button: 'Cargar una labor' },
  cosecha: { path: '/produccion', button: 'Cargar una cosecha' },
  // Stock y elaboración
  stock: { path: '/inventario', button: 'Ver el stock' },
  ingreso: { path: '/inventario', button: 'Cargar un ingreso' },
  egreso: { path: '/inventario', button: 'Cargar un egreso' },
  preparacion: { path: '/elaboracion', button: 'Preparar una mezcla' },
  receta: { path: '/elaboracion', button: 'Crear una receta' },
  // Comercial y caja
  compra: { path: '/comercial', button: 'Cargar una compra' },
  venta: { path: '/comercial', button: 'Cargar una venta' },
  cobro: { path: '/comercial', button: 'Registrar un cobro' },
  pago: { path: '/comercial', button: 'Registrar un pago' },
  'cuentas-corrientes': { path: '/comercial', button: 'Ver las cuentas corrientes' },
  caja: { path: '/comercial', button: 'Ver cajas y bancos' },
  movimiento: { path: '/comercial', button: 'Cargar un movimiento de caja' },
  // Máquinas
  activo: { path: '/activos', button: 'Dar de alta una máquina' },
  activos: { path: '/activos', button: 'Ir a Activos', pageOnly: true },
  // Números
  rentabilidad: { path: '/costos', button: 'Ver la rentabilidad' },
  resultado: { path: '/costos', button: 'Ver el resultado de gestión' },
  reportes: { path: '/reportes', button: 'Ir a Reportes', pageOnly: true },
  // Datos y administración
  producto: { path: '/maestros', button: 'Crear un producto' },
  tercero: { path: '/maestros', button: 'Crear un cliente o proveedor' },
  usuario: { path: '/usuarios', button: 'Crear un usuario' },
  usuarios: { path: '/usuarios', button: 'Ir a Usuarios y roles', pageOnly: true },
  perfil: { path: '/perfil', button: 'Ir a Mi perfil', pageOnly: true },
  importar: { path: '/importar', button: 'Ir a Importar datos', pageOnly: true },
  historial: { path: '/historial', button: 'Ir a Historial', pageOnly: true },
  accesos: { path: '/historial', button: 'Ver los accesos' },
} as const satisfies Record<string, ActionDef>;

export type ActionKey = keyof typeof ACTIONS;

const PARAM = 'abrir';

const isAction = (value: string | null): value is ActionKey => value !== null && value in ACTIONS;

/** Enlace a una acción: `/produccion?abrir=cosecha` (o solo la pantalla). */
export function actionUrl(key: ActionKey): string {
  const action: ActionDef = ACTIONS[key];
  return action.pageOnly ? action.path : `${action.path}?${PARAM}=${key}`;
}

/** Acción pedida en la dirección (o `null`). */
function useRequestedAction(): [ActionKey | null, () => void] {
  const [params, setParams] = useSearchParams();
  const value = params.get(PARAM);
  const clear = () =>
    setParams(
      (current) => {
        current.delete(PARAM);
        return current;
      },
      { replace: true },
    );
  return [isAction(value) ? value : null, clear];
}

/**
 * Atiende las acciones de esta pantalla: si la dirección pide una de estas, la ejecuta y la
 * saca de la dirección (al recargar no se vuelve a abrir). Las demás no las toca.
 */
export function useOpenAction(handlers: Partial<Record<ActionKey, () => void>>): void {
  const [requested, clear] = useRequestedAction();
  const latest = useRef(handlers);
  useEffect(() => {
    latest.current = handlers;
  });
  useEffect(() => {
    const handler = requested && latest.current[requested];
    if (!handler) return;
    clear();
    handler();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo cuando cambia la acción pedida
  }, [requested]);
}

/**
 * Pantallas con pestañas: elige la pestaña donde vive la acción pedida, sin consumirla
 * (la atiende el componente de esa pestaña con `useOpenAction`).
 */
export function useActionTab<T extends string>(
  tabs: Partial<Record<ActionKey, T>>,
  setTab: (tab: T) => void,
): void {
  const [requested] = useRequestedAction();
  const tab = requested ? tabs[requested] : undefined;
  const latest = useRef(setTab);
  useEffect(() => {
    latest.current = setTab;
  });
  useEffect(() => {
    if (tab) latest.current(tab);
  }, [tab]);
}
