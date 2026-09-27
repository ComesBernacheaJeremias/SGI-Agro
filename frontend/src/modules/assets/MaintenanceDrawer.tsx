import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Paper,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconBan, IconPlus, IconTrash } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { useEffect } from 'react';

import { useCan } from '@/app/auth/session';
import { useDocuments } from '@/modules/commercial/api';
import { notifyStockAlerts } from '@/modules/inventory/api';
import {
  type Product,
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
import { formatMoney } from '@/shared/format/number';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import {
  type Maintenance,
  maintenancesApi,
  type MaintenanceIn,
  type PlanStatus,
  useInvalidateAssets,
} from './api';

type Part = {
  key: string;
  product: Product | null;
  unit_id: string | null;
  quantity: string | null;
};

type Values = {
  date: string | null;
  kind: MaintenanceIn['kind'];
  plan_id: string | null;
  meter_reading: string | null;
  description: string;
  purchase_document_id: string | null;
  warehouse_id: string | null;
  parts: Part[];
};

const emptyPart = (): Part => ({
  key: crypto.randomUUID(),
  product: null,
  unit_id: null,
  quantity: null,
});

const empty = (): Values => ({
  date: dayjs().format('YYYY-MM-DD'),
  kind: 'preventive',
  plan_id: null,
  meter_reading: null,
  description: '',
  purchase_document_id: null,
  warehouse_id: null,
  parts: [],
});

async function toValues(m: Maintenance): Promise<Values> {
  const products = await Promise.all(m.parts.map((p) => productsResource.get(p.product.id)));
  return {
    date: m.date,
    kind: m.kind,
    plan_id: m.plan?.id ?? null,
    meter_reading: m.meter_reading,
    description: m.description,
    purchase_document_id: m.purchase_document?.id ?? null,
    warehouse_id: m.warehouse?.id ?? null,
    parts: m.parts.map((p, i) => ({
      key: crypto.randomUUID(),
      product: products[i] ?? null,
      unit_id: p.unit.id,
      quantity: p.quantity,
    })),
  };
}

type Props = {
  assetId: string;
  unit: string;
  plans: PlanStatus[];
  currentReading: string;
  /** null = nuevo */
  maintenance: Maintenance | null;
  /** Nuevo mantenimiento de un plan (desde "Registrar" en el plan). */
  planId?: string | null;
  opened: boolean;
  onClose: () => void;
};

export function MaintenanceDrawer({
  assetId,
  unit,
  plans,
  currentReading,
  maintenance,
  planId,
  opened,
  onClose,
}: Props) {
  const can = useCan();
  const invalidate = useInvalidateAssets();
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const { data: units = [] } = useActiveList(unitsResource);
  const { data: purchases } = useDocuments(
    { direction: 'purchase', status: 'active', page_size: 100 },
    opened,
  );
  const readOnly = !can('assets:write') || maintenance?.status === 'cancelled';

  const form = useForm<Values>({
    initialValues: empty(),
    validate: {
      date: (v) => (v ? null : 'Obligatorio'),
      warehouse_id: (v, values) =>
        values.parts.length > 0 && !v ? 'Elegí de dónde salen los repuestos' : null,
      parts: (parts) =>
        parts.some((p) => !p.product || !p.unit_id || !Number(p.quantity))
          ? 'Completá producto, unidad y cantidad de cada repuesto'
          : null,
    },
  });

  useEffect(() => {
    if (!opened) return;
    if (maintenance) {
      void toValues(maintenance).then((values) => {
        form.setValues(values);
        form.resetDirty();
      });
      return;
    }
    form.setValues({ ...empty(), plan_id: planId ?? null, meter_reading: currentReading });
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- al abrir
  }, [opened, maintenance]);

  const values = form.values;
  const setParts = (parts: Part[]) => form.setFieldValue('parts', parts);
  const updatePart = (key: string, patch: Partial<Part>) =>
    setParts(values.parts.map((p) => (p.key === key ? { ...p, ...patch } : p)));

  async function submit(v: Values) {
    const body: MaintenanceIn = {
      asset_id: assetId,
      date: v.date as string,
      kind: v.kind,
      plan_id: v.plan_id,
      meter_reading: v.meter_reading,
      description: v.description,
      purchase_document_id: v.purchase_document_id,
      warehouse_id: v.parts.length ? v.warehouse_id : null,
      parts: v.parts.map((p) => ({
        product_id: p.product?.id ?? '',
        unit_id: p.unit_id as string,
        quantity: p.quantity as string,
      })),
    };
    const saved = maintenance
      ? await maintenancesApi.update(maintenance.id, body)
      : await maintenancesApi.create(body);
    notifySuccess(`Mantenimiento ${saved.maintenance.number} guardado.`);
    notifyStockAlerts(saved.alerts);
    await invalidate();
  }

  async function cancel() {
    if (!maintenance) return;
    const confirmed = await confirmAction({
      message: `Se va a anular el mantenimiento ${maintenance.number}. Los repuestos vuelven al stock.`,
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!confirmed) return;
    try {
      await maintenancesApi.cancel(maintenance.id);
      notifySuccess(`Mantenimiento ${maintenance.number} anulado.`);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  const purchaseOptions = (purchases?.items ?? []).map((d) => ({
    value: d.id,
    label: `${d.invoice_label} · ${d.party.name} · ${formatDate(d.date)}`,
  }));
  // La compra ya vinculada siempre figura, aunque no esté entre las últimas
  if (
    maintenance?.purchase_document &&
    !purchaseOptions.some((o) => o.value === maintenance.purchase_document?.id)
  ) {
    purchaseOptions.unshift({
      value: maintenance.purchase_document.id,
      label: maintenance.purchase_document.name,
    });
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={maintenance ? `Mantenimiento ${maintenance.number}` : 'Registrar mantenimiento'}
      form={form}
      isEdit={maintenance !== null}
      onSubmit={submit}
      readOnly={readOnly}
      size="lg"
      extraActions={
        maintenance && (
          <>
            <HistoryButton table="maintenances" recordId={maintenance.id} />
            {maintenance.status === 'active' && can('assets:write') && (
              <Button
                variant="subtle"
                color="red"
                leftSection={<IconBan size={16} />}
                onClick={cancel}
              >
                Anular
              </Button>
            )}
          </>
        )
      }
    >
      {maintenance?.status === 'cancelled' && (
        <Group>
          <Badge color="red">Anulado</Badge>
        </Group>
      )}
      <SegmentedControl
        data={[
          { value: 'preventive', label: 'Preventivo' },
          { value: 'corrective', label: 'Correctivo' },
        ]}
        disabled={readOnly}
        {...form.getInputProps('kind')}
      />
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <DateInput label="Fecha" required disabled={readOnly} {...form.getInputProps('date')} />
        <NumberInput
          label={`Lectura del medidor (${unit})`}
          kind="quantity"
          disabled={readOnly}
          {...form.getInputProps('meter_reading')}
        />
        <Select
          label="Plan"
          placeholder="Sin plan"
          description="Si corresponde a un plan, el próximo se cuenta desde acá"
          data={plans.map((p) => ({ value: p.plan.id, label: p.plan.name }))}
          clearable
          disabled={readOnly}
          {...form.getInputProps('plan_id')}
        />
        <Select
          label="Compra del servicio"
          placeholder="Ninguna"
          description="La factura del taller (cargada en Compras con destino = este activo)"
          data={purchaseOptions}
          searchable
          clearable
          disabled={readOnly}
          {...form.getInputProps('purchase_document_id')}
        />
      </SimpleGrid>
      <Textarea
        label="Qué se hizo"
        autosize
        disabled={readOnly}
        {...form.getInputProps('description')}
      />

      <Stack gap="xs">
        <Group justify="space-between">
          <Text size="sm" fw={500}>
            Repuestos del stock
          </Text>
          {maintenance && Number(maintenance.parts_cost) > 0 && (
            <Text size="sm" c="dimmed">
              Costo: {formatMoney(maintenance.parts_cost)}
            </Text>
          )}
        </Group>
        {values.parts.length > 0 && (
          <Select
            label="Salen del almacén"
            required
            data={warehouses.map((w) => ({ value: w.id, label: w.name }))}
            disabled={readOnly}
            {...form.getInputProps('warehouse_id')}
          />
        )}
        {values.parts.map((part) => (
          <Paper key={part.key} withBorder p="xs">
            <Group gap="xs" align="flex-end" wrap="wrap">
              <ProductSelect
                label="Repuesto"
                stockOnly
                value={part.product}
                onChange={(product) =>
                  updatePart(part.key, { product, unit_id: product?.unit.id ?? null })
                }
                disabled={readOnly}
                style={{ flex: '1 1 220px' }}
              />
              <Select
                label="Unidad"
                data={
                  part.product
                    ? allowedUnits(part.product, units).map((u) => ({ value: u.id, label: u.code }))
                    : []
                }
                value={part.unit_id}
                onChange={(unit_id) => updatePart(part.key, { unit_id })}
                disabled={readOnly || !part.product}
                w={90}
              />
              <NumberInput
                label="Cantidad"
                kind="quantity"
                value={part.quantity}
                onChange={(quantity) => updatePart(part.key, { quantity })}
                disabled={readOnly}
                w={110}
              />
              {!readOnly && (
                <ActionIcon
                  variant="subtle"
                  color="red"
                  mb={4}
                  aria-label="Quitar repuesto"
                  onClick={() => setParts(values.parts.filter((p) => p.key !== part.key))}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              )}
            </Group>
          </Paper>
        ))}
        {form.errors.parts && (
          <Text size="xs" c="red">
            {form.errors.parts}
          </Text>
        )}
        {!readOnly && (
          <Group>
            <Button
              variant="light"
              size="xs"
              leftSection={<IconPlus size={14} />}
              onClick={() => setParts([...values.parts, emptyPart()])}
            >
              Agregar repuesto
            </Button>
          </Group>
        )}
      </Stack>
    </EntityDrawer>
  );
}
