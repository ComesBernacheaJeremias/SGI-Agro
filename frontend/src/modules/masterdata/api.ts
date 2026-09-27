/** Recursos y datos auxiliares de los maestros. */
import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { createCrudResource } from '@/shared/crud/resource';

type S = components['schemas'];

export type Unit = S['UnitOut'];
export type Category = S['CategoryOut'];
export type Product = S['ProductOut'];
export type Party = S['PartyOut'];
export type Warehouse = S['WarehouseOut'];
export type Option = S['Option'];

export const unitsResource = createCrudResource<Unit, S['UnitCreate'], S['UnitUpdate']>({
  path: '/api/v1/units',
  key: 'units',
  label: 'unidad',
  table: 'units',
});

export const categoriesResource = createCrudResource<
  Category,
  S['CategoryCreate'],
  S['CategoryUpdate']
>({
  path: '/api/v1/product-categories',
  key: 'product-categories',
  label: 'categoría',
  table: 'product_categories',
});

export const productsResource = createCrudResource<Product, S['ProductCreate'], S['ProductUpdate']>(
  { path: '/api/v1/products', key: 'products', label: 'producto', table: 'products' },
);

export const partiesResource = createCrudResource<Party, S['PartyCreate'], S['PartyUpdate']>({
  path: '/api/v1/parties',
  key: 'parties',
  label: 'cliente/proveedor',
  table: 'parties',
});

export const warehousesResource = createCrudResource<
  Warehouse,
  S['WarehouseCreate'],
  S['WarehouseUpdate']
>({ path: '/api/v1/warehouses', key: 'warehouses', label: 'almacén', table: 'warehouses' });

/** Opciones de desplegables con sus etiquetas en español (vienen del backend). */
export function useMasterdataOptions() {
  return useQuery({
    queryKey: ['masterdata-options'],
    queryFn: async () => unwrap(await api.GET('/api/v1/masterdata/options')),
    staleTime: Infinity,
  });
}

/** Etiqueta de un valor dentro de una lista de opciones. */
export function labelOf(options: Option[] | undefined, value: string | null | undefined): string {
  return options?.find((o) => o.value === value)?.label ?? value ?? '';
}

/** Todos los registros activos de un recurso (para desplegables: unidades, categorías…). */
export function useActiveList<T>(resource: {
  key: string;
  list: (p: object) => Promise<{ items: T[] }>;
}) {
  return useQuery({
    queryKey: [resource.key, 'all-active'],
    queryFn: async () => (await resource.list({ active: 'true', page_size: 200 })).items,
  });
}
