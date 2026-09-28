/**
 * Cliente tipado de la API (tipos generados con `npm run gen:api`).
 * Agrega el token a cada request y, si vence (401), renueva la sesión una vez y reintenta.
 */
import createClient from 'openapi-fetch';

import { sessionStore } from '@/app/auth/session';

import type { components, paths } from './schema';

type TokenResponse = components['schemas']['TokenResponse'];

const AUTH_PATH = '/api/v1/auth/';

let refreshInFlight: Promise<boolean> | null = null;

/** Renueva la sesión con la cookie. Si hay varias llamadas a la vez, comparten un solo refresh. */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= fetch(`${AUTH_PATH}refresh`, { method: 'POST' })
    .then(async (response) => {
      if (!response.ok) {
        sessionStore.signOut();
        return false;
      }
      const body = (await response.json()) as TokenResponse;
      sessionStore.signIn(body.user, body.access_token);
      return true;
    })
    .catch(() => {
      // Sin red: al abrir la app va al login; con la sesión abierta, se sigue (el pedido falla)
      if (sessionStore.get().status === 'checking') sessionStore.signOut();
      return false;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

function withToken(request: Request): Request {
  const token = sessionStore.accessToken();
  if (token) request.headers.set('Authorization', `Bearer ${token}`);
  return request;
}

async function authFetch(request: Request): Promise<Response> {
  const retry = request.clone();
  const response = await fetch(withToken(request));
  const isAuthEndpoint = new URL(request.url).pathname.startsWith(AUTH_PATH);
  if (response.status !== 401 || isAuthEndpoint) return response;
  return (await refreshSession()) ? fetch(withToken(retry)) : response;
}

export const api = createClient<paths>({ baseUrl: window.location.origin, fetch: authFetch });
