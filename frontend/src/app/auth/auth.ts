/** Acciones de sesión: login, logout y restaurar la sesión al abrir la app. */
import { api, refreshSession } from '@/api/client';
import { unwrap } from '@/api/errors';

import { sessionStore } from './session';

export async function login(username: string, password: string): Promise<void> {
  const data = unwrap(await api.POST('/api/v1/auth/login', { body: { username, password } }));
  sessionStore.signIn(data.user, data.access_token);
}

export async function logout(): Promise<void> {
  try {
    await api.POST('/api/v1/auth/logout');
  } finally {
    sessionStore.signOut();
  }
}

/** Al cargar la app: si hay cookie de sesión vigente, entra sin pedir contraseña. */
export async function restoreSession(): Promise<void> {
  await refreshSession();
}
