import { Badge } from '@mantine/core';

import type { Column } from './DataTable';

/** Columna "Estado": Activo / Inactivo (útil con el filtro "Todos"). */
export function activeColumn<T extends { is_active: boolean }>(): Column<T> {
  return {
    key: 'is_active',
    header: 'Estado',
    render: (row) => (
      <Badge color={row.is_active ? 'green' : 'gray'} variant="light">
        {row.is_active ? 'Activo' : 'Inactivo'}
      </Badge>
    ),
  };
}
