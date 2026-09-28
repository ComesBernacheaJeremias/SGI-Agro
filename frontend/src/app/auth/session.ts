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

const listeners = new Set<() => void>();

function setState(next: SessionState): void {
  state = next;
  listeners.forEach((listener) => listener());
}

export const sessionStore = {
  get: (): SessionState => state,
  accessToken: (): string | null => (state.status === 'authenticated' ? state.accessToken : null),
  signIn: (user: SessionUser, accessToken: string): void => {
    setState({ status: 'authenticated', user, accessToken });
  },
  signOut: (): void => {
    setState({ status: 'anonymous' });
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
