import { Button, Group } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { Fragment, type ReactNode, useState } from 'react';

import { type Column, DataTable } from './DataTable';
import { type ListState, useListState, useResourceList } from './hooks';
import type { Entity, Resource } from './types';

export type DrawerProps<T> = { record: T | null; opened: boolean; onClose: () => void };

type Props<T extends Entity, C, U> = {
  resource: Resource<T, C, U>;
  columns: Column<T>[];
  /** Texto del botón de alta (sin botón si no se pasa o no hay permiso). */
  newLabel?: string;
  canCreate: boolean;
  defaultSort?: string;
  searchPlaceholder?: string;
  /** Filtros propios: reciben el estado del listado (para volver a la página 1). */
  filters?: (list: ListState) => ReactNode;
  /** Parámetros extra de la consulta (valores de los filtros propios). */
  extraParams?: Record<string, unknown>;
  renderDrawer: (props: DrawerProps<T>) => ReactNode;
};

/** Pestaña estándar de un maestro: botón "Nuevo" + tabla + panel de alta/edición. */
export function CrudTab<T extends Entity, C, U>({
  resource,
  columns,
  newLabel,
  canCreate,
  defaultSort,
  searchPlaceholder,
  filters,
  extraParams,
  renderDrawer,
}: Props<T, C, U>) {
  const list = useListState(defaultSort);
  const { data, isFetching } = useResourceList(resource, { ...list.params, ...extraParams });
  const [record, setRecord] = useState<T | null>(null);
  const [opened, setOpened] = useState(false);
  // Cada apertura monta un panel nuevo: su estado interno arranca limpio
  const [session, setSession] = useState(0);

  function open(row: T | null) {
    setRecord(row);
    setOpened(true);
    setSession((n) => n + 1);
  }

  return (
    <>
      {newLabel && canCreate && (
        <Group justify="flex-end" mb="sm">
          <Button leftSection={<IconPlus size={16} />} onClick={() => open(null)}>
            {newLabel}
          </Button>
        </Group>
      )}
      <DataTable
        columns={columns}
        list={list}
        data={data}
        loading={isFetching}
        onRowClick={open}
        searchPlaceholder={searchPlaceholder}
        filters={filters?.(list)}
      />
      <Fragment key={session}>
        {renderDrawer({ record, opened, onClose: () => setOpened(false) })}
      </Fragment>
    </>
  );
}
