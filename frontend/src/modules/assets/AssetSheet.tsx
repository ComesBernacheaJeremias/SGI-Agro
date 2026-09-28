import {
  ActionIcon,
  Badge,
  Button,
  Drawer,
  Group,
  Loader,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconEdit, IconPlus, IconTool, IconTrash } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { Fragment, useState } from 'react';

import { useCan } from '@/app/auth/session';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import {
  type Asset,
  type Maintenance,
  meterRate,
  PLAN_STATE,
  type PlanStatus,
  plansResource,
  readingsResource,
  useAssetSheet,
  useInvalidateAssets,
} from './api';
import { MaintenanceDrawer } from './MaintenanceDrawer';

const qty = (value: string | number | null | undefined, unit: string) =>
  value === null || value === undefined ? '—' : `${formatNumber(value, 'quantity')} ${unit}`;

function Figure({
  label,
  value,
  hint,
  color,
}: {
  label: string;
  value: string;
  hint?: string;
  color?: string;
}) {
  return (
    <Stack gap={0}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={700} c={color}>
        {value}
      </Text>
      {hint && (
        <Text size="xs" c="dimmed">
          {hint}
        </Text>
      )}
    </Stack>
  );
}

// --- Plan (alta/edición) ---

type PlanValues = {
  name: string;
  every_usage: string | null;
  every_months: string | null;
  start_date: string | null;
  start_reading: string | null;
};

function PlanModal({
  assetId,
  unit,
  plan,
  opened,
  onClose,
}: {
  assetId: string;
  unit: string;
  plan: PlanStatus | null;
  opened: boolean;
  onClose: () => void;
}) {
  const invalidate = useInvalidateAssets();
  const form = useForm<PlanValues>({
    initialValues: plan
      ? {
          name: plan.plan.name,
          every_usage: plan.plan.every_usage,
          every_months: plan.plan.every_months === null ? null : String(plan.plan.every_months),
          start_date: plan.plan.start_date,
          start_reading: plan.plan.start_reading,
        }
      : { name: '', every_usage: null, every_months: null, start_date: null, start_reading: null },
    validate: {
      name: (v) => (v.trim() ? null : 'Obligatorio'),
      every_usage: (v, values) =>
        v || values.every_months ? null : `Indicá cada cuántas ${unit} o cada cuántos meses`,
    },
  });
  async function submit(v: PlanValues) {
    const body = {
      name: v.name,
      every_usage: v.every_usage,
      every_months: v.every_months ? Number(v.every_months) : null,
      start_date: v.start_date,
      start_reading: v.start_reading,
    };
    try {
      if (plan) await plansResource.update(plan.plan.id, body);
      else await plansResource.create({ ...body, asset_id: assetId });
      notifySuccess('Plan guardado.');
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={plan ? plan.plan.name : 'Nuevo plan de mantenimiento'}
    >
      <form onSubmit={form.onSubmit(submit)}>
        <Stack>
          <TextInput
            label="Nombre"
            placeholder="Cambio de aceite"
            required
            {...form.getInputProps('name')}
          />
          <SimpleGrid cols={2}>
            <NumberInput
              label={unit === 'km' ? 'Cada cuántos km' : 'Cada cuántas horas de uso'}
              placeholder={unit === 'km' ? '10.000' : '250'}
              kind="quantity"
              {...form.getInputProps('every_usage')}
            />
            <NumberInput
              label="O cada cuántos meses"
              description="Opcional"
              kind="quantity"
              {...form.getInputProps('every_months')}
            />
          </SimpleGrid>
          <Text size="xs" c="dimmed">
            {unit === 'km'
              ? 'En rodados lo habitual es por km. '
              : 'Las horas son las que marca el horómetro del tractor. '}
            Si completás los dos, avisa con lo que llegue primero (cuando falta el 10 % o 15 días).
          </Text>
          <SimpleGrid cols={2}>
            <DateInput
              label="Contar desde"
              placeholder="Hoy"
              description="Hasta el primer mantenimiento de este plan"
              {...form.getInputProps('start_date')}
            />
            <NumberInput
              label={`Lectura en esa fecha (${unit})`}
              placeholder="La actual"
              kind="quantity"
              {...form.getInputProps('start_reading')}
            />
          </SimpleGrid>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit">Guardar</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

// --- Lectura ---

function ReadingModal({
  assetId,
  unit,
  opened,
  onClose,
}: {
  assetId: string;
  unit: string;
  opened: boolean;
  onClose: () => void;
}) {
  const invalidate = useInvalidateAssets();
  const form = useForm({
    initialValues: {
      date: dayjs().format('YYYY-MM-DD') as string | null,
      value: null as string | null,
      notes: '',
    },
    validate: {
      date: (v) => (v ? null : 'Obligatorio'),
      value: (v) => (v ? null : 'Obligatorio'),
    },
  });
  async function submit(v: typeof form.values) {
    try {
      await readingsResource.create({
        asset_id: assetId,
        date: v.date as string,
        value: v.value as string,
        notes: v.notes,
      });
      notifySuccess('Lectura guardada.');
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }
  return (
    <Modal opened={opened} onClose={onClose} title="Cargar lectura del medidor">
      <form onSubmit={form.onSubmit(submit)}>
        <Stack>
          <SimpleGrid cols={2}>
            <DateInput label="Fecha" required {...form.getInputProps('date')} />
            <NumberInput
              label={`Lectura (${unit})`}
              kind="quantity"
              required
              {...form.getInputProps('value')}
            />
          </SimpleGrid>
          <TextInput label="Observaciones" {...form.getInputProps('notes')} />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit">Guardar</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

// --- Ficha ---

type Props = { asset: Asset | null; onClose: () => void; onEdit: (asset: Asset) => void };

/** Ficha del activo: medidor, costo real vs. tarifa, planes, mantenimientos y lecturas. */
export function AssetSheet({ asset, onClose, onEdit }: Props) {
  const can = useCan();
  const canWrite = can('assets:write');
  const invalidate = useInvalidateAssets();
  const [dateFrom, setDateFrom] = useState<string | null>(
    dayjs().subtract(12, 'month').format('YYYY-MM-DD'),
  );
  const [dateTo, setDateTo] = useState<string | null>(dayjs().format('YYYY-MM-DD'));
  const { data: sheet, isLoading } = useAssetSheet(asset?.id ?? null, dateFrom, dateTo);
  const [maintenance, setMaintenance] = useState<{
    record: Maintenance | null;
    planId?: string;
  } | null>(null);
  const [plan, setPlan] = useState<{ record: PlanStatus | null } | null>(null);
  const [reading, setReading] = useState(false);

  async function removePlan(p: PlanStatus) {
    const ok = await confirmAction({
      message: `Se va a desactivar el plan "${p.plan.name}".`,
      confirmLabel: 'Desactivar',
      danger: true,
    });
    if (!ok) return;
    try {
      await plansResource.setActive(p.plan.id, false);
      await invalidate();
    } catch (err) {
      notifyError(err);
    }
  }

  async function removeReading(id: string) {
    const ok = await confirmAction({
      message: 'Se va a anular la lectura.',
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!ok) return;
    try {
      await readingsResource.setActive(id, false);
      await invalidate();
    } catch (err) {
      notifyError(err);
    }
  }

  const unit = sheet?.unit ?? 'horas';
  const costs = sheet?.costs;
  const diff =
    costs?.real_rate && Number(costs.rate)
      ? ((Number(costs.real_rate) - Number(costs.rate)) / Number(costs.rate)) * 100
      : null;

  return (
    <Drawer
      opened={asset !== null}
      onClose={onClose}
      position="right"
      size="xl"
      title={
        <Group gap="xs">
          <Text fw={700}>{asset?.name}</Text>
          {asset?.status === 'in_repair' && <Badge color="orange">En reparación</Badge>}
        </Group>
      }
    >
      {isLoading && <Loader />}
      {asset && sheet && costs && (
        <Stack>
          <Group justify="space-between" wrap="wrap">
            <Text size="sm" c="dimmed">
              {[asset.brand, asset.model, asset.year, asset.identifier].filter(Boolean).join(' · ')}
            </Text>
            <Group gap="xs">
              {canWrite && (
                <Button
                  size="xs"
                  leftSection={<IconTool size={14} />}
                  onClick={() => setMaintenance({ record: null })}
                >
                  Registrar mantenimiento
                </Button>
              )}
              <Button
                size="xs"
                variant="default"
                leftSection={<IconEdit size={14} />}
                onClick={() => onEdit(asset)}
              >
                Editar datos
              </Button>
            </Group>
          </Group>

          <Paper withBorder p="sm">
            <SimpleGrid cols={{ base: 2, sm: 4 }}>
              <Figure
                label={unit === 'km' ? 'Odómetro (estimado)' : 'Horómetro (estimado)'}
                value={qty(sheet.current_reading, unit)}
                hint={
                  sheet.last_reading_date
                    ? `Última lectura ${formatDate(sheet.last_reading_date)} + labores`
                    : 'Sin lecturas: solo labores'
                }
              />
              <Figure label="Uso en labores" value={qty(costs.usage, unit)} />
              <Figure
                label="Gasto real"
                value={formatMoney(costs.total)}
                hint={`Cargado a ciclos: ${formatMoney(costs.rate_cost)}`}
              />
              <Figure
                label={`Costo real ${meterRate(unit)}`}
                value={costs.real_rate ? formatMoney(costs.real_rate) : '—'}
                hint={`Tarifa: ${formatMoney(costs.rate)}${diff !== null ? ` (${diff > 0 ? '+' : ''}${formatNumber(diff, 'quantity')} %)` : ''}`}
                color={diff !== null && Math.abs(diff) > 20 ? 'orange' : undefined}
              />
            </SimpleGrid>
            <Group gap="xs" mt="sm" align="flex-end">
              <DateInput
                label="Período desde"
                value={dateFrom}
                onChange={setDateFrom}
                w={150}
                size="xs"
              />
              <DateInput label="hasta" value={dateTo} onChange={setDateTo} w={150} size="xs" />
            </Group>
          </Paper>

          <Tabs defaultValue="plans" keepMounted={false}>
            <Tabs.List>
              <Tabs.Tab value="plans">Planes ({sheet.plans.length})</Tabs.Tab>
              <Tabs.Tab value="maintenances">Mantenimientos</Tabs.Tab>
              <Tabs.Tab value="expenses">Gastos</Tabs.Tab>
              <Tabs.Tab value="readings">Lecturas</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="plans" pt="sm">
              {sheet.plans.length === 0 && (
                <Text c="dimmed" size="sm">
                  Sin planes de mantenimiento.
                </Text>
              )}
              {sheet.plans.length > 0 && (
                <Table verticalSpacing={4}>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Plan</Table.Th>
                      <Table.Th>Último</Table.Th>
                      <Table.Th>Próximo</Table.Th>
                      <Table.Th>Falta</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {sheet.plans.map((p) => (
                      <Table.Tr key={p.plan.id}>
                        <Table.Td>
                          <Text size="sm">{p.plan.name}</Text>
                          <Text size="xs" c="dimmed">
                            {[
                              p.plan.every_usage && `cada ${qty(p.plan.every_usage, unit)}`,
                              p.plan.every_months && `cada ${p.plan.every_months} meses`,
                            ]
                              .filter(Boolean)
                              .join(' o ')}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{formatDate(p.last_date)}</Text>
                          <Text size="xs" c="dimmed">
                            {qty(p.last_reading, unit)}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{p.due_date ? formatDate(p.due_date) : ''}</Text>
                          <Text size="xs" c="dimmed">
                            {p.due_reading ? qty(p.due_reading, unit) : ''}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={PLAN_STATE[p.state].color} variant="light">
                            {PLAN_STATE[p.state].label}
                          </Badge>
                          <Text size="xs" c="dimmed">
                            {[
                              p.remaining_usage !== null && qty(p.remaining_usage, unit),
                              p.remaining_days !== null && `${p.remaining_days} días`,
                            ]
                              .filter(Boolean)
                              .join(' · ')}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          {canWrite && (
                            <Group gap={4} wrap="nowrap">
                              <Button
                                size="compact-xs"
                                variant="light"
                                onClick={() => setMaintenance({ record: null, planId: p.plan.id })}
                              >
                                Registrar
                              </Button>
                              <ActionIcon
                                variant="subtle"
                                aria-label="Editar plan"
                                onClick={() => setPlan({ record: p })}
                              >
                                <IconEdit size={16} />
                              </ActionIcon>
                              <ActionIcon
                                variant="subtle"
                                color="red"
                                aria-label="Desactivar plan"
                                onClick={() => removePlan(p)}
                              >
                                <IconTrash size={16} />
                              </ActionIcon>
                            </Group>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
              {canWrite && (
                <Button
                  mt="sm"
                  size="xs"
                  variant="light"
                  leftSection={<IconPlus size={14} />}
                  onClick={() => setPlan({ record: null })}
                >
                  Nuevo plan
                </Button>
              )}
            </Tabs.Panel>

            <Tabs.Panel value="maintenances" pt="sm">
              {sheet.maintenances.length === 0 && (
                <Text c="dimmed" size="sm">
                  Sin mantenimientos registrados.
                </Text>
              )}
              <Stack gap={6}>
                {sheet.maintenances.map((m) => (
                  <Paper
                    key={m.id}
                    withBorder
                    p="xs"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setMaintenance({ record: m })}
                  >
                    <Group justify="space-between" wrap="nowrap">
                      <Group gap="xs">
                        <Text size="sm" fw={600}>
                          {formatDate(m.date)} ·{' '}
                          {m.plan?.name ?? (m.kind === 'corrective' ? 'Correctivo' : 'Preventivo')}
                        </Text>
                        {m.status === 'cancelled' && (
                          <Badge color="red" size="xs">
                            Anulado
                          </Badge>
                        )}
                      </Group>
                      <Text size="sm">
                        {formatMoney(Number(m.parts_cost) + Number(m.purchase_cost))}
                      </Text>
                    </Group>
                    <Text size="xs" c="dimmed" lineClamp={2}>
                      {[
                        m.number,
                        m.meter_reading && qty(m.meter_reading, unit),
                        m.description,
                        m.purchase_document?.name,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </Text>
                  </Paper>
                ))}
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="expenses" pt="sm">
              {sheet.expenses_by_category.length === 0 && (
                <Text c="dimmed" size="sm">
                  Sin gastos en el período. Los gastos se cargan en Compras o Caja con destino =
                  este activo.
                </Text>
              )}
              {sheet.expenses_by_category.map((e) => (
                <Group key={e.name} justify="space-between">
                  <Text size="sm">{e.name}</Text>
                  <Text size="sm">{formatMoney(e.amount)}</Text>
                </Group>
              ))}
            </Tabs.Panel>

            <Tabs.Panel value="readings" pt="sm">
              {sheet.readings.map((r) => (
                <Group key={r.id} justify="space-between">
                  <Text size="sm">
                    {formatDate(r.date)} · {qty(r.value, unit)} {r.notes && `· ${r.notes}`}
                  </Text>
                  {canWrite && (
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      aria-label="Anular lectura"
                      onClick={() => removeReading(r.id)}
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  )}
                </Group>
              ))}
              {sheet.readings.length === 0 && (
                <Text c="dimmed" size="sm">
                  Sin lecturas cargadas.
                </Text>
              )}
              {canWrite && (
                <Button
                  mt="sm"
                  size="xs"
                  variant="light"
                  leftSection={<IconPlus size={14} />}
                  onClick={() => setReading(true)}
                >
                  Cargar lectura
                </Button>
              )}
            </Tabs.Panel>
          </Tabs>

          {/* Paneles y ventanas: se vuelven a montar en cada apertura (formulario limpio) */}
          <Fragment
            key={
              maintenance ? (maintenance.record?.id ?? `new-${maintenance.planId ?? ''}`) : 'closed'
            }
          >
            <MaintenanceDrawer
              assetId={asset.id}
              unit={unit}
              plans={sheet.plans}
              currentReading={sheet.current_reading}
              maintenance={maintenance?.record ?? null}
              planId={maintenance?.planId}
              opened={maintenance !== null}
              onClose={() => setMaintenance(null)}
            />
          </Fragment>
          {plan && (
            <PlanModal
              assetId={asset.id}
              unit={unit}
              plan={plan.record}
              opened
              onClose={() => setPlan(null)}
            />
          )}
          {reading && (
            <ReadingModal assetId={asset.id} unit={unit} opened onClose={() => setReading(false)} />
          )}
        </Stack>
      )}
    </Drawer>
  );
}
