/**
 * Estado de la sesión (fuera de React para que el cliente de API también lo lea).
 * El access token vive solo en memoria; la sesión larga está en una cookie HttpOnly.
 */
import { useSyncExternalStore } from 'react';

import type { components } from '@/api/schema';

export type SessionUser = components['schemas']['MeOut'];

export type SessionState =
  | { status: 'checking' }
  | { status: 'anonymous' }
  | { status: 'authenticated'; user: SessionUser; accessToken: string };

let state: SessionState = { status: 'checking' };

const USER_KEY = 'sgi.user';

function rememberUser(user: SessionUser | null): void {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  } catch {
    // almacenamiento no disponible: sin carga sin conexión
  }
}

function rememberedUser(): SessionUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as SessionUser) : null;
  } catch {
    return null;
  }
}
const listeners = new Set<() => void>();

function setState(next: SessionState): void {
  state = next;
  listeners.forEach((listener) => listener());
}

export const sessionStore = {
  get: (): SessionState => state,
  accessToken: (): string | null => (state.status === 'authenticated' ? state.accessToken : null),
  signIn: (user: SessionUser, accessToken: string): void => {
    rememberUser(user);
    setState({ status: 'authenticated', user, accessToken });
  },
  signOut: (): void => {
    rememberUser(null);
    setState({ status: 'anonymous' });
  },
  /** Sin señal al abrir la app: entra con el último usuario (sin token hasta reconectar). */
  signInOffline: (): boolean => {
    const user = rememberedUser();
    if (user) setState({ status: 'authenticated', user, accessToken: '' });
    return user !== null;
  },
  subscribe: (listener: () => void): (() => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};

export function useSession(): SessionState {
  return useSyncExternalStore(sessionStore.subscribe, sessionStore.get);
}

/** `const can = useCan(); can('users:manage')` → el usuario tiene ese permiso. */
export function useCan(): (permission: string) => boolean {
  const session = useSession();
  return (permission) =>
    session.status === 'authenticated' && session.user.permissions.includes(permission);
}
