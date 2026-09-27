/** Llamadas a la API de producción: catálogos, ciclos, labores y cuaderno de campo. */
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components, operations } from '@/api/schema';
import { createCrudResource } from '@/shared/crud/resource';

type S = components['schemas'];

export type Farm = S['FarmOut'];
export type Plot = S['PlotOut'];
export type Crop = S['CropOut'];
export type OperationType = S['OperationTypeOut'];
export type Cycle = S['CycleOut'];
export type Operation = S['OperationOut'];
export type OperationSummary = S['OperationSummaryOut'];
export type OperationIn = S['OperationIn'];
export type FieldBook = S['FieldBookOut'];

export type CyclesQuery = NonNullable<
  operations['list_cycles_api_v1_crop_cycles_get']['parameters']['query']
>;
export type OperationsQuery = NonNullable<
  operations['list_operations_api_v1_field_operations_get']['parameters']['query']
>;

export const farmsResource = createCrudResource<Farm, S['FarmCreate'], S['FarmUpdate']>({
  path: '/api/v1/farms',
  key: 'farms',
  label: 'establecimiento',
  table: 'farms',
});
export const plotsResource = createCrudResource<Plot, S['PlotCreate'], S['PlotUpdate']>({
  path: '/api/v1/plots',
  key: 'plots',
  label: 'lote',
  table: 'plots',
});
export const cropsResource = createCrudResource<Crop, S['CropCreate'], S['CropUpdate']>({
  path: '/api/v1/crops',
  key: 'crops',
  label: 'cultivo',
  table: 'crops',
});
export const operationTypesResource = createCrudResource<
  OperationType,
  S['OperationTypeCreate'],
  S['OperationTypeUpdate']
>({
  path: '/api/v1/operation-types',
  key: 'operation-types',
  label: 'tipo de labor',
  table: 'operation_types',
});

const KEYS = { cycles: 'crop-cycles', operations: 'field-operations', fieldBook: 'field-book' };

export function useProductionOptions() {
  return useQuery({
    queryKey: ['production-options'],
    queryFn: async () => unwrap(await api.GET('/api/v1/production/options')),
    staleTime: Infinity,
  });
}

export function useSeasons() {
  return useQuery({
    queryKey: ['seasons'],
    queryFn: async () => unwrap(await api.GET('/api/v1/production/seasons')),
  });
}

export function useCycles(query: CyclesQuery) {
  return useQuery({
    queryKey: [KEYS.cycles, query],
    queryFn: async () => unwrap(await api.GET('/api/v1/crop-cycles', { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

/** Ciclos en curso (para elegir en una labor). */
export function useActiveCycles() {
  return useCycles({ status: 'active', page_size: 200 });
}

export function useFieldBook(cycleId: string | null) {
  return useQuery({
    queryKey: [KEYS.fieldBook, cycleId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/crop-cycles/{id_}/field-book', {
          params: { path: { id_: cycleId as string } },
        }),
      ),
    enabled: cycleId !== null,
  });
}

export function useOperations(query: OperationsQuery) {
  return useQuery({
    queryKey: [KEYS.operations, query],
    queryFn: async () => unwrap(await api.GET('/api/v1/field-operations', { params: { query } })),
    placeholderData: keepPreviousData,
  });
}

const byId = (id: string) => ({ params: { path: { id_: id } } });

export const cyclesApi = {
  create: async (body: S['CycleCreate']) => unwrap(await api.POST('/api/v1/crop-cycles', { body })),
  update: async (id: string, body: S['CycleUpdate']) =>
    unwrap(await api.PATCH('/api/v1/crop-cycles/{id_}', { ...byId(id), body })),
  finish: async (id: string, endDate: string) =>
    unwrap(
      await api.POST('/api/v1/crop-cycles/{id_}/finish', {
        ...byId(id),
        body: { end_date: endDate },
      }),
    ),
  reopen: async (id: string, reason: string) =>
    unwrap(await api.POST('/api/v1/crop-cycles/{id_}/reopen', { ...byId(id), body: { reason } })),
};

export const operationsApi = {
  get: async (id: string) => unwrap(await api.GET('/api/v1/field-operations/{id_}', byId(id))),
  create: async (body: OperationIn) => unwrap(await api.POST('/api/v1/field-operations', { body })),
  update: async (id: string, body: OperationIn) =>
    unwrap(await api.PUT('/api/v1/field-operations/{id_}', { ...byId(id), body })),
  cancel: async (id: string) =>
    unwrap(await api.POST('/api/v1/field-operations/{id_}/cancel', byId(id))),
};

/** Después de guardar: refresca ciclos, labores, cuaderno y todo lo de inventario. */
export function useInvalidateProduction() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      [...Object.values(KEYS), 'stock', 'stock-documents', 'stock-alerts', 'kardex'].map((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    );
}
