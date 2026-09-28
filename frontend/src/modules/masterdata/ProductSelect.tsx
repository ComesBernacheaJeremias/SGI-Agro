import { Select, type SelectProps } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { type Product, productsResource } from './api';

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
  // Los tipos se filtran en el servidor (así no se pierden resultados por el límite)
  const { data } = useQuery({
    queryKey: [productsResource.key, 'select', debounced, types],
    queryFn: () => {
      const params = { q: debounced || undefined, page_size: 30, type: types };
      return productsResource.list(params);
    },
  });

  const found = (data?.items ?? []).filter((p) => !stockOnly || p.type !== 'service');
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
