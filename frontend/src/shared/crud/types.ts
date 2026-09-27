/** Tipos comunes de listados paginados y recursos editables. */

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type ActiveFilter = 'true' | 'false' | 'all';

export type ListParams = {
  q?: string;
  active?: ActiveFilter;
  sort?: string;
  page?: number;
  page_size?: number;
};

export type Entity = { id: string };

/**
 * Descripción de un recurso de la API (usuarios, productos…).
 * Cada módulo lo arma con llamadas tipadas; los hooks y componentes genéricos lo consumen.
 */
export type Resource<T extends Entity, C, U> = {
  /** Clave para la caché (ej. 'users') */
  key: string;
  /** Nombre en singular para mensajes (ej. 'usuario') */
  label: string;
  /** Tabla en la base, para el historial (ej. 'users') */
  table: string;
  list: (params: ListParams) => Promise<Page<T>>;
  get?: (id: string) => Promise<T>;
  create: (body: C) => Promise<T>;
  update: (id: string, body: U) => Promise<T>;
  setActive?: (id: string, active: boolean) => Promise<T>;
};
