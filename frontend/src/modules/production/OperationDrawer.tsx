import {
  Alert,
  Button,
  Checkbox,
  Group,
  MultiSelect,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';

import { useCan } from '@/app/auth/session';
import { assetsResource } from '@/modules/assets/api';
import { notifyStockAlerts } from '@/modules/inventory/api';
import {
  productsResource,
  unitsResource,
  useActiveList,
  warehousesResource,
} from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { allowedUnits } from '@/modules/masterdata/units';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';
import { useNewId } from '@/shared/crud/newId';

import {
  cropsResource,
  cyclesApi,
  type Operation,
  operationsApi,
  operationTypesResource,
  useActiveCycles,
  useInvalidateProduction,
} from './api';
import { AssetsField, InputsField } from './OperationFields';
import { emptyOperation, type OperationValues, toBody, validateOperation } from './operationForm';

type Props = {
  /** null = labor nueva */
  operationId: string | null;
  /** Para una labor nueva: cosecha o labor común */
  harvest: boolean;
  /** Ciclo preseleccionado (desde el tablero de ciclos) */
  defaultCycleId?: string;
  opened: boolean;
  onClose: () => void;
};

export function OperationDrawer({ operationId, harvest, defaultCycleId, opened, onClose }: Props) {
  const can = useCan();
  const newId = useNewId(opened);
  const invalidate = useInvalidateProduction();
  const { data: types = [] } = useActiveList(operationTypesResource);
  const { data: cycles } = useActiveCycles();
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const { data: units = [] } = useActiveList(unitsResource);
  const { data: assets = [] } = useActiveList(assetsResource);
  const { data: existing } = useQuery({
    queryKey: ['field-operations', 'detail', operationId],
    queryFn: () => operationsApi.get(operationId as string),
    enabled: opened && operationId !== null,
  });

  const form = useForm<OperationValues & { _form?: string }>({
    initialValues: emptyOperation(defaultCycleId),
    validate: (values) => {
      const message = validateOperation(values, isHarvest(values.operation_type_id));
      return message ? { _form: message } : {};
    },
  });
  const isHarvest = (typeId: string | null) =>
    types.find((t) => t.id === typeId)?.is_harvest ?? false;
  const type = types.find((t) => t.id === form.values.operation_type_id);
  const harvestMode = existing ? existing.is_harvest : harvest;
  const readOnly = !can('production:write') || (existing !== undefined && !existing.editable);
  // El aviso aparece al guardar y se actualiza (o desaparece) mientras se corrige
  const formError =
    form.errors._form && validateOperation(form.values, isHarvest(form.values.operation_type_id));

  async function loadExisting(op: Operation) {
    const products = await Promise.all(op.inputs.map((i) => productsResource.get(i.product.id)));
    const harvestProduct = op.harvest ? await productsResource.get(op.harvest.product.id) : null;
    form.setValues({
      date: op.date,
      operation_type_id: op.operation_type.id,
      cycle_ids: op.cycles.map((c) => c.crop_cycle_id),
      areas: Object.fromEntries(op.cycles.map((c) => [c.crop_cycle_id, c.area_ha])),
      inputs: op.inputs.map((i, index) => ({
        key: crypto.randomUUID(),
        product: products[index] ?? null,
        unit_id: i.unit_id,
        mode: i.dose_per_ha ? 'dose' : 'total',
        value: i.dose_per_ha ?? i.quantity,
        warehouse_id: i.warehouse.id,
      })),
      assets: op.assets.map((a) => ({
        key: crypto.randomUUID(),
        asset_id: a.asset.id,
        usage: a.usage,
      })),
      harvest: {
        product: harvestProduct,
        unit_id: op.harvest?.unit_id ?? null,
        quantity: op.harvest?.quantity ?? null,
        warehouse_id: op.harvest?.warehouse.id ?? null,
        is_final: op.harvest?.is_final ?? false,
      },
      notes: op.notes,
    });
    form.resetDirty();
  }

  // Cargar valores al abrir (nuevo o existente)
  useEffect(() => {
    if (!opened) return;
    if (operationId === null) {
      const values = emptyOperation(defaultCycleId);
      const firstType = types.find((t) => t.is_harvest === harvest);
      values.operation_type_id = firstType?.id ?? null;
      values.harvest.warehouse_id = warehouses[0]?.id ?? null;
      form.setValues(values);
      form.resetDirty();
      return;
    }
    if (existing) void loadExisting(existing);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- al abrir o al llegar la labor
  }, [opened, operationId, existing, types.length]);

  // Cosecha: al elegir el ciclo, proponer el producto de su cultivo
  const firstCycle = cycles?.items.find((c) => c.id === form.values.cycle_ids[0]);
  useEffect(() => {
    if (!harvestMode || !firstCycle || form.values.harvest.product || readOnly) return;
    void cropsResource
      .get(firstCycle.crop.id)
      .then((crop) => productsResource.get(crop.harvest_product.id))
      .then((product) =>
        form.setFieldValue('harvest', {
          ...form.values.harvest,
          product,
          unit_id: product.unit.id,
        }),
      );
    // eslint-disable-next-line react-hooks/exhaustive-deps -- al cambiar el ciclo
  }, [firstCycle?.id, harvestMode]);

  const selectedCycles = (cycles?.items ?? []).filter((c) => form.values.cycle_ids.includes(c.id));
  const totalArea = selectedCycles.reduce(
    (sum, c) => sum + Number(form.values.areas[c.id] || c.area_ha),
    0,
  );

  async function submit(values: OperationValues) {
    const body = toBody(values, harvestMode);
    await afterSave(
      operationId
        ? await operationsApi.update(operationId, body)
        : await operationsApi.create({ ...body, id: newId }),
    );
  }

  async function afterSave(saved: Awaited<ReturnType<typeof operationsApi.create>>) {
    const values = form.values;
    notifySuccess(`${harvestMode ? 'Cosecha' : 'Labor'} ${saved.operation.number} guardada.`);
    notifyStockAlerts(saved.alerts);
    await invalidate();
    const cycle = saved.operation.cycles[0];
    if (harvestMode && values.harvest.is_final && cycle && cycle.status === 'active') {
      const finish = await confirmAction({
        title: 'Cosecha final',
        message: `¿Finalizar el cultivo "${cycle.name}" con fecha ${formatDate(saved.operation.date)}? Sus costos quedan congelados.`,
        confirmLabel: 'Finalizar cultivo',
      });
      if (finish) {
        await cyclesApi.finish(cycle.crop_cycle_id, saved.operation.date);
        notifySuccess('Cultivo finalizado.');
        await invalidate();
      }
    }
  }

  async function cancelOperation() {
    if (!existing) return;
    const confirmed = await confirmAction({
      message: `Se va a anular la labor ${existing.number}. El stock y los costos se recalculan.`,
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!confirmed) return;
    try {
      const result = await operationsApi.cancel(existing.id);
      notifySuccess(`Labor ${existing.number} anulada.`);
      notifyStockAlerts(result.alerts);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  const typeOptions = types
    .filter((t) => t.is_harvest === harvestMode)
    .map((t) => ({ value: t.id, label: t.name }));
  const cycleOptions = (cycles?.items ?? []).map((c) => ({ value: c.id, label: c.name }));
  const harvestProduct = form.values.harvest.product;

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={
        existing
          ? `${existing.operation_type.name} ${existing.number}`
          : harvestMode
            ? 'Cargar cosecha'
            : 'Cargar labor'
      }
      form={form}
      isEdit={operationId !== null}
      onSubmit={submit}
      readOnly={readOnly}
      size="xl"
      extraActions={
        existing && (
          <>
            <HistoryButton table="field_operations" recordId={existing.id} />
            {existing.editable && can('production:write') && (
              <Button variant="subtle" color="red" onClick={cancelOperation}>
                Anular
              </Button>
            )}
          </>
        )
      }
    >
      {existing?.status === 'cancelled' && (
        <Alert color="red" variant="light">
          Labor anulada.
        </Alert>
      )}
      {existing && existing.status === 'active' && !existing.editable && (
        <Alert variant="light">
          Un cultivo de esta labor está finalizado: no se puede modificar.
        </Alert>
      )}
      {formError && (
        <Alert color="red" variant="light">
          {formError}
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <DateInput label="Fecha" required disabled={readOnly} {...form.getInputProps('date')} />
        <Select
          label="Tipo de labor"
          required
          data={typeOptions}
          disabled={readOnly}
          {...form.getInputProps('operation_type_id')}
        />
      </SimpleGrid>
      <MultiSelect
        label={harvestMode ? 'Cultivo' : 'Cultivos'}
        description={
          harvestMode
            ? undefined
            : 'Si elegís varios, los insumos y las horas se reparten por superficie'
        }
        data={cycleOptions}
        searchable
        maxValues={harvestMode ? 1 : undefined}
        disabled={readOnly}
        {...form.getInputProps('cycle_ids')}
      />
      {selectedCycles.length > 1 && (
        <Paper withBorder p="xs">
          <Stack gap={4}>
            {selectedCycles.map((c) => (
              <Group key={c.id} justify="space-between" wrap="nowrap">
                <Text size="sm">{c.name}</Text>
                <NumberInput
                  kind="quantity"
                  size="xs"
                  w={110}
                  rightSection="ha"
                  placeholder={formatNumber(c.area_ha, 'quantity')}
                  value={form.values.areas[c.id] ?? null}
                  onChange={(v) => form.setFieldValue('areas', { ...form.values.areas, [c.id]: v })}
                  disabled={readOnly}
                />
              </Group>
            ))}
            <Text size="xs" c="dimmed">
              Total: {formatNumber(totalArea, 'quantity')} ha
            </Text>
          </Stack>
        </Paper>
      )}

      {type?.uses_inputs && (
        <InputsField
          value={form.values.inputs}
          onChange={(inputs) => form.setFieldValue('inputs', inputs)}
          units={units}
          warehouses={warehouses}
          totalArea={totalArea}
          readOnly={readOnly}
        />
      )}

      {harvestMode && (
        <Paper withBorder p="xs">
          <Stack gap="xs">
            <Text size="sm" fw={500}>
              Cosecha
            </Text>
            <Group gap="xs" align="flex-end" wrap="wrap">
              <ProductSelect
                label="Producto"
                types={['own_produce']}
                value={harvestProduct}
                onChange={(product) =>
                  form.setFieldValue('harvest', {
                    ...form.values.harvest,
                    product,
                    unit_id: product?.unit.id ?? null,
                  })
                }
                disabled={readOnly}
                style={{ flex: '1 1 200px' }}
              />
              <Select
                label="Unidad"
                data={
                  harvestProduct
                    ? allowedUnits(harvestProduct, units).map((u) => ({
                        value: u.id,
                        label: u.code,
                      }))
                    : []
                }
                disabled={readOnly || !harvestProduct}
                w={90}
                {...form.getInputProps('harvest.unit_id')}
              />
              <NumberInput
                label="Cantidad"
                kind="quantity"
                disabled={readOnly}
                w={120}
                {...form.getInputProps('harvest.quantity')}
              />
              <Select
                label="Almacén destino"
                data={warehouses.map((w) => ({ value: w.id, label: w.name }))}
                disabled={readOnly}
                w={170}
                {...form.getInputProps('harvest.warehouse_id')}
              />
            </Group>
            <Checkbox
              label="¿Es la cosecha final? (ofrece finalizar el cultivo)"
              disabled={readOnly}
              {...form.getInputProps('harvest.is_final', { type: 'checkbox' })}
            />
            {existing?.harvest?.batch_code && (
              <Text size="xs" c="dimmed">
                Partida: {existing.harvest.batch_code}
              </Text>
            )}
          </Stack>
        </Paper>
      )}

      {type?.uses_assets && (
        <AssetsField
          value={form.values.assets}
          onChange={(value) => form.setFieldValue('assets', value)}
          assets={assets}
          readOnly={readOnly}
        />
      )}

      <Textarea
        label="Observaciones"
        autosize
        disabled={readOnly}
        {...form.getInputProps('notes')}
      />
      {existing && (
        <Text size="sm" ta="right">
          Costo de la labor: <b>{formatMoney(existing.total_cost)}</b>
        </Text>
      )}
    </EntityDrawer>
  );
}
