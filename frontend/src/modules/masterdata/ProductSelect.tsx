import { Select, type SelectProps } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { useOnline } from '@/app/offline/network';

import { type Product, productsResource } from './api';

const normalizeText = (text: string) =>
  text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

type Props = Omit<SelectProps, 'data' | 'value' | 'onChange' | 'searchable'> & {
  value: Product | null;
  onChange: (product: Product | null) => void;
  /** Excluir servicios (no manejan stock). */
  stockOnly?: boolean;
  /** Solo productos de estos tipos (ej. ['own_produce']). */
  types?: Product['type'][];
};

/**
 * Buscador de productos: consulta al servidor mientras se escribe (funciona con miles de
 * productos). Devuelve el producto completo (unidad y equivalencias incluidas).
 */
export function ProductSelect({ value, onChange, stockOnly = false, types, ...props }: Props) {
  const [search, setSearch] = useState('');
  const [debounced] = useDebouncedValue(search, 250);
  // Con un solo tipo, se filtra en el servidor (así no se pierden resultados por el límite)
  const serverType = types?.length === 1 ? types[0] : undefined;
  const { data } = useQuery({
    queryKey: [productsResource.key, 'select', debounced, serverType],
    queryFn: () => {
      const params = { q: debounced || undefined, page_size: 30, type: serverType };
      return productsResource.list(params);
    },
  });

  // Sin conexión: se busca en la lista completa guardada en el dispositivo
  const online = useOnline();
  const cached = useQueryClient().getQueryData<Product[]>([productsResource.key, 'all-active']);
  const source =
    online || !cached
      ? (data?.items ?? [])
      : cached.filter((p) =>
          normalizeText(`${p.code} ${p.name}`).includes(normalizeText(debounced)),
        );
  const found = source.filter(
    (p) => (!stockOnly || p.type !== 'service') && (!types || types.includes(p.type)),
  );
  // El seleccionado siempre está en la lista, aunque no coincida con la búsqueda actual
  const options = value && !found.some((p) => p.id === value.id) ? [value, ...found] : found;

  return (
    <Select
      {...props}
      searchable
      clearable
      nothingFoundMessage="Sin resultados"
      value={value?.id ?? null}
      searchValue={search}
      onSearchChange={setSearch}
      data={options.map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
      onChange={(id) => onChange(options.find((p) => p.id === id) ?? null)}
    />
  );
}
