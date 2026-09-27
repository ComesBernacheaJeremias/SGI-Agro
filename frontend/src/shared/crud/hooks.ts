/** Hooks genéricos para listar y modificar un recurso (con caché, avisos y confirmaciones). */
import { useDebouncedValue } from '@mantine/hooks';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import type { ActiveFilter, Entity, ListParams, Resource } from './types';

const PAGE_SIZE = 50;

/** Estado de un listado: búsqueda (con demora), activos/inactivos, orden y página. */
export function useListState(defaultSort?: string) {
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebouncedValue(search, 300);
  const [active, setActive] = useState<ActiveFilter>('true');
  const [sort, setSort] = useState<string | undefined>(defaultSort);
  const [page, setPage] = useState(1);

  const params: ListParams = {
    q: debouncedSearch || undefined,
    active,
    sort,
    page,
    page_size: PAGE_SIZE,
  };

  return {
    params,
    search,
    setSearch: (value: string) => {
      setSearch(value);
      setPage(1);
    },
    active,
    setActive: (value: ActiveFilter) => {
      setActive(value);
      setPage(1);
    },
    sort,
    setSort,
    page,
    setPage,
  };
}

export type ListState = ReturnType<typeof useListState>;

export function useResourceList<T extends Entity, C, U>(
  resource: Resource<T, C, U>,
  params: ListParams,
) {
  return useQuery({
    queryKey: [resource.key, 'list', params],
    queryFn: () => resource.list(params),
    placeholderData: keepPreviousData,
  });
}

/** Alta, edición (con "¿Estás seguro?") y activación/desactivación de un recurso. */
export function useResourceMutations<T extends Entity, C, U>(resource: Resource<T, C, U>) {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: [resource.key] });

  const create = useMutation({
    mutationFn: (body: C) => resource.create(body),
    onSuccess: () => {
      notifySuccess(`Se creó el ${resource.label}.`);
      void invalidate();
    },
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: U }) => resource.update(id, body),
    onSuccess: () => {
      notifySuccess('Cambios guardados.');
      void invalidate();
    },
  });

  const setActive = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => {
      if (!resource.setActive) throw new Error('El recurso no admite activar/desactivar.');
      return resource.setActive(id, active);
    },
    onSuccess: (_data, { active }) => {
      notifySuccess(active ? 'Reactivado.' : 'Desactivado.');
      void invalidate();
    },
    onError: notifyError,
  });

  async function toggleActive(id: string, name: string, active: boolean) {
    const confirmed = await confirmAction({
      message: active
        ? `Se va a reactivar "${name}".`
        : `Se va a desactivar "${name}". Podés reactivarlo más adelante.`,
      confirmLabel: active ? 'Reactivar' : 'Desactivar',
      danger: !active,
    });
    if (confirmed) setActive.mutate({ id, active });
  }

  return { create, update, setActive, toggleActive };
}
