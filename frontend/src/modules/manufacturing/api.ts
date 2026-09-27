/** Llamadas a la API de elaboración: recetas y preparaciones. */
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components, operations } from '@/api/schema';
import { createCrudResource } from '@/shared/crud/resource';

type S = components['schemas'];

export type Recipe = S['RecipeOut'];
export type Order = S['OrderOut'];
export type OrderIn = S['OrderIn'];
export type ComponentCheck = S['ComponentCheckOut'];
export type OrdersQuery = NonNullable<
  operations['list_orders_api_v1_production_orders_get']['parameters']['query']
>;

export const recipesResource = createCrudResource<Recipe, S['RecipeCreate'], S['RecipeUpdate']>({
  path: '/api/v1/recipes',
  key: 'recipes',
  label: 'receta',
  table: 'recipes',
});

export function useOrders(query: OrdersQuery) {
  return useQuery({
    queryKey: ['production-orders', query],
    queryFn: async () => unwrap(await api.GET('/api/v1/production-orders', { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

const byId = (id: string) => ({ params: { path: { id_: id } } });

export const ordersApi = {
  check: async (body: S['OrderCheckIn']) =>
    unwrap(await api.POST('/api/v1/production-orders/check', { body })),
  create: async (body: OrderIn) => unwrap(await api.POST('/api/v1/production-orders', { body })),
  update: async (id: string, body: OrderIn) =>
    unwrap(await api.PUT('/api/v1/production-orders/{id_}', { ...byId(id), body })),
  cancel: async (id: string) =>
    unwrap(await api.POST('/api/v1/production-orders/{id_}/cancel', byId(id))),
};

export function useInvalidateManufacturing() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      ['production-orders', 'recipes', 'stock', 'stock-documents', 'stock-alerts', 'kardex'].map(
        (key) => queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    );
}
