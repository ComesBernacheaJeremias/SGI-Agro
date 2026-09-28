/** Llamadas a la API de usuarios, roles y permisos. */
import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import type { Resource } from '@/shared/crud/types';

export type User = components['schemas']['UserOut'];
export type UserCreate = components['schemas']['UserCreate'];
export type UserUpdate = components['schemas']['UserUpdate'];
export type Role = components['schemas']['RoleOut'];
export type RoleCreate = components['schemas']['RoleCreate'];
export type RoleUpdate = components['schemas']['RoleUpdate'];
export type PermissionGroup = components['schemas']['PermissionGroupOut'];

const byId = (id: string) => ({ params: { path: { id_: id } } });

export const usersResource: Resource<User, UserCreate, UserUpdate> = {
  key: 'users',
  label: 'usuario',
  table: 'users',
  list: async (params) => unwrap(await api.GET('/api/v1/users', { params: { query: params } })),
  create: async (body) => unwrap(await api.POST('/api/v1/users', { body })),
  update: async (id, body) => unwrap(await api.PATCH('/api/v1/users/{id_}', { ...byId(id), body })),
  setActive: async (id, active) =>
    unwrap(
      active
        ? await api.POST('/api/v1/users/{id_}/activate', byId(id))
        : await api.POST('/api/v1/users/{id_}/deactivate', byId(id)),
    ),
};

/** Cierra todas las sesiones abiertas del usuario (ej. celular perdido). */
export async function revokeSessions(id: string): Promise<void> {
  const result = await api.POST('/api/v1/users/{id_}/revoke-sessions', byId(id));
  if (result.error !== undefined) unwrap(result);
}

export async function resetPassword(id: string, password: string): Promise<void> {
  const result = await api.POST('/api/v1/users/{id_}/reset-password', {
    ...byId(id),
    body: { password },
  });
  if (result.error !== undefined) unwrap(result);
}

export const ROLES_KEY = 'roles';

export function useRoles() {
  return useQuery({
    queryKey: [ROLES_KEY],
    queryFn: async () => unwrap(await api.GET('/api/v1/roles')),
  });
}

export function usePermissionGroups() {
  return useQuery({
    queryKey: ['permissions'],
    queryFn: async () => unwrap(await api.GET('/api/v1/permissions')),
    staleTime: Infinity,
  });
}

export const rolesApi = {
  create: async (body: RoleCreate) => unwrap(await api.POST('/api/v1/roles', { body })),
  update: async (id: string, body: RoleUpdate) =>
    unwrap(await api.PATCH('/api/v1/roles/{id_}', { ...byId(id), body })),
  remove: async (id: string) => {
    const result = await api.DELETE('/api/v1/roles/{id_}', byId(id));
    if (result.error !== undefined) unwrap(result);
  },
};
