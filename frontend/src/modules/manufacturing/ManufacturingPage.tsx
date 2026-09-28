import { Badge, Button, Tabs } from '@mantine/core';
import { useState } from 'react';

import { useCan } from '@/app/auth/session';
import { type Column, DataTable } from '@/shared/crud/DataTable';
import { useListState } from '@/shared/crud/hooks';
import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { PageHeader } from '@/shared/ui/PageHeader';

import { type Order, useOrders } from './api';
import { OrderDrawer } from './OrderDrawer';
import { RecipesTab } from './RecipesTab';

function OrdersTab({ onOpen }: { onOpen: (order: Order) => void }) {
  const list = useListState();
  const { data, isFetching } = useOrders({ page: list.page, page_size: 50 });
  const columns: Column<Order>[] = [
    { key: 'date', header: 'Fecha', nowrap: true, render: (o) => formatDate(o.date) },
    { key: 'number', header: 'Número', nowrap: true, hideOnMobile: true },
    { key: 'recipe', header: 'Producto', render: (o) => o.recipe.name },
    {
      key: 'quantity',
      header: 'Cantidad',
      align: 'right',
      render: (o) => `${formatNumber(o.quantity, 'quantity')} ${o.unit.code}`,
    },
    {
      key: 'unit_cost',
      header: 'Costo unit.',
      align: 'right',
      render: (o) => formatMoney(o.unit_cost),
    },
    {
      key: 'status',
      header: '',
      render: (o) =>
        (o.status === 'cancelled' && (
          <Badge color="red" variant="light">
            Anulada
          </Badge>
        )) ||
        (o.parent_id && <Badge variant="light">Automática</Badge>),
    },
  ];
  return (
    <DataTable
      columns={columns}
      list={list}
      data={data}
      loading={isFetching}
      onRowClick={onOpen}
      showSearch={false}
      showActiveFilter={false}
    />
  );
}

export function ManufacturingPage() {
  const canWrite = useCan()('manufacturing:write');
  const [order, setOrder] = useState<{ record: Order | null } | null>(null);
  return (
    <>
      <PageHeader
        title="Elaboración"
        actions={
          canWrite && <Button onClick={() => setOrder({ record: null })}>Nueva preparación</Button>
        }
      />
      <Tabs defaultValue="orders" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="orders">Preparaciones</Tabs.Tab>
          <Tabs.Tab value="recipes">Recetas</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="orders">
          <OrdersTab onOpen={(record) => setOrder({ record })} />
        </Tabs.Panel>
        <Tabs.Panel value="recipes">
          <RecipesTab />
        </Tabs.Panel>
      </Tabs>
      <OrderDrawer
        order={order?.record ?? null}
        opened={order !== null}
        onClose={() => setOrder(null)}
      />
    </>
  );
}
