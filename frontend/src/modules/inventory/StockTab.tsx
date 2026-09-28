import { Badge, Group, Select, Stack, Switch, Text } from '@mantine/core';

import { categoriesResource, useActiveList, warehousesResource } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { type Column, DataTable } from '@/shared/crud/DataTable';
import { useListState } from '@/shared/crud/hooks';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { useState } from 'react';

import { ownProduceNote, STOCK_ALERT_COLOR, type StockRow, useStock } from './api';
import { EstimatedValue } from './EstimatedValue';

type Row = StockRow & { id: string };

type Props = { onOpenKardex: (productId: string) => void };

export function StockTab({ onOpenKardex }: Props) {
  const list = useListState();
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const { data: categories = [] } = useActiveList(categoriesResource);
  const [warehouseId, setWarehouseId] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [at, setAt] = useState<string | null>(null);
  const [byWarehouse, setByWarehouse] = useState(false);
  const [belowMin, setBelowMin] = useState(false);

  const { data, isFetching } = useStock({
    q: list.params.q,
    page: list.page,
    page_size: 50,
    warehouse_id: warehouseId ?? undefined,
    category_id: categoryId ?? undefined,
    at: at ?? undefined,
    by_warehouse: byWarehouse,
    below_min: belowMin,
  });
  const rows: Row[] | undefined = data?.items.map((r) => ({
    ...r,
    id: `${r.product.id}-${r.warehouse?.id ?? 'total'}`,
  }));
  const showWarehouse = byWarehouse || warehouseId !== null;
  const reset =
    <V,>(setter: (v: V) => void) =>
    (v: V) => {
      setter(v);
      list.setPage(1);
    };

  const columns: Column<Row>[] = [
    {
      key: 'code',
      header: 'Código',
      nowrap: true,
      render: (r) => r.product.code,
      hideOnMobile: true,
    },
    {
      key: 'product',
      header: 'Producto',
      render: (r) => (
        <Group gap={6} wrap="nowrap">
          {r.product.name}
          {r.below_min && (
            <Badge color={STOCK_ALERT_COLOR} size="xs">
              Bajo mínimo
            </Badge>
          )}
        </Group>
      ),
    },
    ...(showWarehouse
      ? [{ key: 'warehouse', header: 'Almacén', render: (r: Row) => r.warehouse?.name ?? '' }]
      : []),
    {
      key: 'quantity',
      header: 'Cantidad',
      align: 'right',
      render: (r) => `${formatNumber(r.quantity, 'quantity')} ${r.unit}`,
    },
    {
      key: 'avg_cost',
      header: 'Costo prom.',
      align: 'right',
      hideOnMobile: true,
      // Producción propia: no tiene costo promedio (su costo está en el ciclo)
      render: (r) => (r.estimated_value != null ? '—' : formatMoney(r.avg_cost)),
    },
    {
      key: 'value',
      header: 'Valor',
      align: 'right',
      render: (r) =>
        r.estimated_value != null ? (
          <EstimatedValue value={r.estimated_value} provisional={r.estimated_provisional} />
        ) : (
          formatMoney(r.value)
        ),
    },
  ];
  const own = data && ownProduceNote(data.own_produce_value, data.own_produce_provisional);

  return (
    <>
      <DataTable
        columns={columns}
        list={list}
        data={data && rows ? { ...data, items: rows } : undefined}
        loading={isFetching}
        onRowClick={(r) => onOpenKardex(r.product.id)}
        searchPlaceholder="Buscar producto…"
        showActiveFilter={false}
        filters={
          <>
            <Select
              placeholder="Almacén"
              data={warehouses.map((w) => ({ value: w.id, label: w.name }))}
              value={warehouseId}
              onChange={reset(setWarehouseId)}
              clearable
              w={180}
            />
            <Select
              placeholder="Categoría"
              data={categories.map((c) => ({ value: c.id, label: c.path }))}
              value={categoryId}
              onChange={reset(setCategoryId)}
              searchable
              clearable
              w={200}
            />
            <DateInput placeholder="A fecha (hoy)" value={at} onChange={reset(setAt)} w={150} />
            <Switch
              label="Por almacén"
              checked={byWarehouse}
              onChange={(e) => reset(setByWarehouse)(e.currentTarget.checked)}
            />
            <Switch
              label="Bajo mínimo"
              color={STOCK_ALERT_COLOR}
              checked={belowMin}
              onChange={(e) => reset(setBelowMin)(e.currentTarget.checked)}
            />
          </>
        }
      />
      {data && data.items.length > 0 && (
        <Stack gap={0} align="flex-end" mt={4}>
          <Text size="sm">
            Valor total:{' '}
            <b>{formatMoney(Number(data.total_value) + Number(data.own_produce_value))}</b>
          </Text>
          {own && (
            <Text size="xs" c="dimmed">
              {own}
            </Text>
          )}
        </Stack>
      )}
    </>
  );
}
