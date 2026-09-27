import {
  Box,
  Group,
  LoadingOverlay,
  Pagination,
  ScrollArea,
  SegmentedControl,
  Table,
  Text,
  TextInput,
  UnstyledButton,
} from '@mantine/core';
import { IconArrowDown, IconArrowUp, IconSearch } from '@tabler/icons-react';
import type { ReactNode } from 'react';

import type { ListState } from './hooks';
import type { ActiveFilter, Entity, Page } from './types';

export type Column<T> = {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  /** Permite ordenar por esta columna (usa `key` como campo de orden en la API). */
  sortable?: boolean;
  align?: 'left' | 'right' | 'center';
  /** Ocultar en pantallas chicas (celular). */
  hideOnMobile?: boolean;
};

type Props<T extends Entity> = {
  columns: Column<T>[];
  list: ListState;
  data: Page<T> | undefined;
  loading: boolean;
  onRowClick?: (row: T) => void;
  searchPlaceholder?: string;
  showSearch?: boolean;
  showActiveFilter?: boolean;
  /** Filtros extra propios de la pantalla (se muestran junto a la búsqueda). */
  filters?: ReactNode;
};

/** Tabla estándar de listados: búsqueda, activos/inactivos, orden, paginación. */
export function DataTable<T extends Entity>({
  columns,
  list,
  data,
  loading,
  onRowClick,
  searchPlaceholder = 'Buscar…',
  showSearch = true,
  showActiveFilter = true,
  filters,
}: Props<T>) {
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  function toggleSort(key: string) {
    list.setSort(list.sort === key ? `-${key}` : key);
  }

  return (
    <Box>
      <Group mb="sm" justify="space-between" wrap="wrap">
        <Group gap="sm" wrap="wrap" style={{ flexGrow: 1 }}>
          {showSearch && (
            <TextInput
              placeholder={searchPlaceholder}
              leftSection={<IconSearch size={16} />}
              value={list.search}
              onChange={(e) => list.setSearch(e.currentTarget.value)}
              w={{ base: '100%', sm: 320 }}
            />
          )}
          {filters}
        </Group>
        {showActiveFilter && (
          <SegmentedControl
            size="xs"
            value={list.active}
            onChange={(value) => list.setActive(value as ActiveFilter)}
            data={[
              { value: 'true', label: 'Activos' },
              { value: 'false', label: 'Inactivos' },
              { value: 'all', label: 'Todos' },
            ]}
          />
        )}
      </Group>

      <Box pos="relative">
        <LoadingOverlay visible={loading} zIndex={1} overlayProps={{ blur: 1 }} />
        <ScrollArea>
          <Table striped highlightOnHover={Boolean(onRowClick)} verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                {columns.map((col) => (
                  <Table.Th
                    key={col.key}
                    ta={col.align}
                    visibleFrom={col.hideOnMobile ? 'sm' : undefined}
                  >
                    {col.sortable ? (
                      <UnstyledButton onClick={() => toggleSort(col.key)} fw={600} fz="sm">
                        <Group gap={4} wrap="nowrap">
                          {col.header}
                          {list.sort === col.key && <IconArrowUp size={14} />}
                          {list.sort === `-${col.key}` && <IconArrowDown size={14} />}
                        </Group>
                      </UnstyledButton>
                    ) : (
                      col.header
                    )}
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.items.map((row) => (
                <Table.Tr
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={onRowClick ? { cursor: 'pointer' } : undefined}
                >
                  {columns.map((col) => (
                    <Table.Td
                      key={col.key}
                      ta={col.align}
                      visibleFrom={col.hideOnMobile ? 'sm' : undefined}
                    >
                      {col.render
                        ? col.render(row)
                        : String((row as Record<string, unknown>)[col.key] ?? '')}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollArea>
        {data && data.items.length === 0 && (
          <Text c="dimmed" ta="center" py="lg">
            No hay registros para mostrar.
          </Text>
        )}
      </Box>

      {data && (
        <Group justify="space-between" mt="sm">
          <Text size="sm" c="dimmed">
            {data.total} {data.total === 1 ? 'registro' : 'registros'}
          </Text>
          {totalPages > 1 && (
            <Pagination size="sm" total={totalPages} value={list.page} onChange={list.setPage} />
          )}
        </Group>
      )}
    </Box>
  );
}
