/**
 * Fábrica de recursos para endpoints generados con `crud_router` del backend:
 *   GET/POST {path} · PATCH {path}/{id_} · POST {path}/{id_}/activate|deactivate
 * Los tipos de la entidad (T, C, U) vienen del esquema OpenAPI generado.
 */
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';

import type { Entity, Page, Resource } from './types';

type Config = {
  /** Ej. '/api/v1/products' */
  path: string;
  key: string;
  label: string;
  table: string;
};

// openapi-fetch tipa cada ruta literal; acá la ruta es un parámetro, por eso el cliente
// se usa sin tipos de ruta (`untyped`) y los resultados se tipan con T.
const untyped = api as unknown as {
  GET: (
    path: string,
    init?: object,
  ) => Promise<{ data?: unknown; error?: unknown; response: Response }>;
  POST: (
    path: string,
    init?: object,
  ) => Promise<{ data?: unknown; error?: unknown; response: Response }>;
  PATCH: (
    path: string,
    init?: object,
  ) => Promise<{ data?: unknown; error?: unknown; response: Response }>;
};

export function createCrudResource<T extends Entity, C, U>({
  path,
  key,
  label,
  table,
}: Config): Resource<T, C, U> & {
  get: (id: string) => Promise<T>;
  setActive: (id: string, active: boolean) => Promise<T>;
} {
  const byId = (id: string) => ({ params: { path: { id_: id } } });
  return {
    key,
    label,
    table,
    get: async (id) => unwrap(await untyped.GET(`${path}/{id_}`, byId(id))) as T,
    list: async (params) =>
      unwrap(await untyped.GET(path, { params: { query: params } })) as Page<T>,
    create: async (body) => unwrap(await untyped.POST(path, { body })) as T,
    update: async (id, body) =>
      unwrap(await untyped.PATCH(`${path}/{id_}`, { ...byId(id), body })) as T,
    setActive: async (id, active) =>
      unwrap(
        await untyped.POST(`${path}/{id_}/${active ? 'activate' : 'deactivate'}`, byId(id)),
      ) as T,
  };
}
