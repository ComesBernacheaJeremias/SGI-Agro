import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Select,
  SimpleGrid,
  Table,
  Text,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { useEffect } from 'react';

import { useCan } from '@/app/auth/session';
import { notifyStockAlerts } from '@/modules/inventory/api';
import { useActiveList, warehousesResource } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';
import { useNewId } from '@/shared/crud/newId';

import { type Order, ordersApi, recipesResource, useInvalidateManufacturing } from './api';

type Values = {
  date: string | null;
  recipe_id: string | null;
  quantity: string | null;
  components_warehouse_id: string | null;
  target_warehouse_id: string | null;
  prepare_missing: boolean;
  notes: string;
};

type Props = { order: Order | null; opened: boolean; onClose: () => void };

export function OrderDrawer({ order, opened, onClose }: Props) {
  const can = useCan();
  const newId = useNewId(opened);
  const invalidate = useInvalidateManufacturing();
  const { data: recipes = [] } = useActiveList(recipesResource);
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const readOnly = !can('manufacturing:write') || order?.status === 'cancelled';

  const form = useForm<Values>({
    initialValues: {
      date: dayjs().format('YYYY-MM-DD'),
      recipe_id: null,
      quantity: null,
      components_warehouse_id: null,
      target_warehouse_id: null,
      prepare_missing: false,
      notes: '',
    },
    validate: {
      date: (v) => (v ? null : 'Obligatorio'),
      recipe_id: (v) => (v ? null : 'Obligatorio'),
      quantity: (v) => (v && Number(v) > 0 ? null : 'Obligatorio'),
      components_warehouse_id: (v) => (v ? null : 'Obligatorio'),
      target_warehouse_id: (v) => (v ? null : 'Obligatorio'),
    },
  });

  useEffect(() => {
    if (!opened) return;
    const first = warehouses[0]?.id ?? null;
    const values: Values = order
      ? {
          date: order.date,
          recipe_id: order.recipe.id,
          quantity: order.quantity,
          components_warehouse_id: order.components_warehouse.id,
          target_warehouse_id: order.target_warehouse.id,
          prepare_missing: false,
          notes: order.notes,
        }
      : {
          date: dayjs().format('YYYY-MM-DD'),
          recipe_id: null,
          quantity: null,
          components_warehouse_id: first,
          target_warehouse_id: first,
          prepare_missing: false,
          notes: '',
        };
    form.setValues(values);
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- al abrir
  }, [opened, order]);

  const v = form.values;
  const recipe = recipes.find((r) => r.id === v.recipe_id);
  const canCheck =
    !order &&
    v.recipe_id &&
    v.quantity &&
    Number(v.quantity) > 0 &&
    v.components_warehouse_id &&
    v.date;
  const { data: check } = useQuery({
    queryKey: [
      'production-orders',
      'check',
      v.recipe_id,
      v.quantity,
      v.components_warehouse_id,
      v.date,
    ],
    queryFn: () =>
      ordersApi.check({
        recipe_id: v.recipe_id as string,
        quantity: v.quantity as string,
        components_warehouse_id: v.components_warehouse_id as string,
        date: v.date as string,
      }),
    enabled: opened && Boolean(canCheck),
  });
  const missing = (check ?? []).filter((c) => Number(c.missing) > 0);
  const missingInputs = missing.filter((c) => !c.can_prepare);
  const missingPreparable = missing.filter((c) => c.can_prepare);

  async function submit(values: Values) {
    const body = {
      date: values.date as string,
      recipe_id: values.recipe_id as string,
      quantity: values.quantity as string,
      components_warehouse_id: values.components_warehouse_id as string,
      target_warehouse_id: values.target_warehouse_id as string,
      prepare_missing: values.prepare_missing,
      notes: values.notes,
    };
    const saved = order
      ? await ordersApi.update(order.id, body)
      : await ordersApi.create({ ...body, id: newId });
    const extra = saved.prepared.length
      ? ` También se prepararon: ${saved.prepared.map((o) => `${o.recipe.name} (${formatNumber(o.quantity, 'quantity')} ${o.unit.code})`).join(', ')}.`
      : '';
    notifySuccess(`Preparación ${saved.order.number} guardada.${extra}`);
    notifyStockAlerts(saved.alerts);
    await invalidate();
  }

  async function cancelOrder() {
    if (!order) return;
    const ok = await confirmAction({
      message: `Se va a anular la preparación ${order.number}.`,
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!ok) return;
    try {
      const result = await ordersApi.cancel(order.id);
      notifySuccess('Preparación anulada.');
      notifyStockAlerts(result.alerts);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  const warehouseOptions = warehouses.map((w) => ({ value: w.id, label: w.name }));

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={order ? `Preparación ${order.number}` : 'Nueva preparación'}
      form={form}
      isEdit={order !== null}
      onSubmit={submit}
      readOnly={readOnly}
      size="lg"
      extraActions={
        order && (
          <>
            <HistoryButton table="production_orders" recordId={order.id} />
            {order.status === 'active' && can('manufacturing:write') && (
              <Button variant="subtle" color="red" onClick={cancelOrder}>
                Anular
              </Button>
            )}
          </>
        )
      }
    >
      {order?.status === 'cancelled' && <Badge color="red">Anulada</Badge>}
      <SimpleGrid cols={2}>
        <DateInput label="Fecha" required disabled={readOnly} {...form.getInputProps('date')} />
        <Select
          label="Receta"
          required
          searchable
          data={recipes.map((r) => ({ value: r.id, label: r.name }))}
          disabled={readOnly || order !== null}
          {...form.getInputProps('recipe_id')}
        />
        <NumberInput
          label={`Cantidad a preparar${recipe ? ` (${recipe.yield_unit.code})` : ''}`}
          required
          kind="quantity"
          disabled={readOnly}
          {...form.getInputProps('quantity')}
        />
        <div />
        <Select
          label="Almacén de componentes"
          required
          data={warehouseOptions}
          disabled={readOnly}
          {...form.getInputProps('components_warehouse_id')}
        />
        <Select
          label="Almacén destino"
          required
          data={warehouseOptions}
          disabled={readOnly}
          {...form.getInputProps('target_warehouse_id')}
        />
      </SimpleGrid>

      {check && check.length > 0 && (
        <Table withTableBorder striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Componente</Table.Th>
              <Table.Th ta="right">Necesario</Table.Th>
              <Table.Th ta="right">Disponible</Table.Th>
              <Table.Th ta="right">Falta</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {check.map((c) => (
              <Table.Tr key={c.product.id}>
                <Table.Td>{c.product.name}</Table.Td>
                <Table.Td ta="right">{`${formatNumber(c.required, 'quantity')} ${c.unit}`}</Table.Td>
                <Table.Td ta="right">{`${formatNumber(c.available, 'quantity')} ${c.unit}`}</Table.Td>
                <Table.Td ta="right" c={Number(c.missing) > 0 ? 'red' : undefined}>
                  {Number(c.missing) > 0 ? `${formatNumber(c.missing, 'quantity')} ${c.unit}` : '—'}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      {missingInputs.length > 0 && (
        <Alert color="red" variant="light">
          Faltan insumos: {missingInputs.map((c) => c.product.name).join(', ')}. Hay que comprarlos
          o ajustar la cantidad.
        </Alert>
      )}
      {missingPreparable.length > 0 && (
        <Checkbox
          label={`Preparar lo que falta (${missingPreparable.map((c) => c.product.name).join(', ')})`}
          {...form.getInputProps('prepare_missing', { type: 'checkbox' })}
        />
      )}

      {order && (
        <Table withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Componente usado</Table.Th>
              <Table.Th ta="right">Cantidad</Table.Th>
              <Table.Th ta="right">Costo</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {order.lines.map((l) => (
              <Table.Tr key={l.product.id}>
                <Table.Td>{l.product.name}</Table.Td>
                <Table.Td ta="right">{`${formatNumber(l.quantity, 'quantity')} ${l.unit.code}`}</Table.Td>
                <Table.Td ta="right">{formatMoney(l.cost)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      {order && (
        <Text ta="right">
          Costo total <b>{formatMoney(order.total_cost)}</b> · por {order.unit.code}:{' '}
          <b>{formatMoney(order.unit_cost)}</b>
        </Text>
      )}
      <Textarea
        label="Observaciones"
        autosize
        disabled={readOnly}
        {...form.getInputProps('notes')}
      />
    </EntityDrawer>
  );
}
