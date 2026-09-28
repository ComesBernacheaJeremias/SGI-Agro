import {
  Alert,
  Badge,
  Button,
  Group,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import dayjs from 'dayjs';
import { useState } from 'react';

import { useCan } from '@/app/auth/session';
import { useActiveList } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { notifyError, notifySuccess } from '@/shared/ui/feedback';

import {
  cropsResource,
  type Cycle,
  cyclesApi,
  plotsResource,
  useInvalidateProduction,
} from './api';

type Values = {
  plot_id: string | null;
  crop_id: string | null;
  area_ha: string | null;
  start_date: string | null;
  expected_end_date: string | null;
  notes: string;
};

const EMPTY: Values = {
  plot_id: null,
  crop_id: null,
  area_ha: null,
  start_date: dayjs().format('YYYY-MM-DD'),
  expected_end_date: null,
  notes: '',
};

/** Resumen de costos y cosecha de un ciclo. */
export function CycleSummary({ cycle }: { cycle: Cycle }) {
  const unit = cycle.harvest_unit;
  const item = (label: string, value: string) => (
    <Stack gap={0}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={600}>{value}</Text>
    </Stack>
  );
  return (
    <SimpleGrid cols={{ base: 2, sm: 3 }}>
      {item('Insumos', formatMoney(cycle.input_cost))}
      {item('Maquinaria', formatMoney(cycle.machinery_cost))}
      {item('Servicios y gastos', formatMoney(cycle.expense_cost))}
      {item('Costo total', formatMoney(cycle.total_cost))}
      {item('Cosechado', `${formatNumber(cycle.harvested_quantity, 'quantity')} ${unit}`)}
      {item(
        'Rinde',
        cycle.yield_per_ha ? `${formatNumber(cycle.yield_per_ha, 'quantity')} ${unit}/ha` : '—',
      )}
      {item('Costo por ha', formatMoney(cycle.cost_per_ha))}
      {cycle.cost_per_unit && item(`Costo por ${unit}`, formatMoney(cycle.cost_per_unit))}
    </SimpleGrid>
  );
}

type Props = {
  cycle: Cycle | null;
  opened: boolean;
  onClose: () => void;
  onOpenFieldBook: (cycle: Cycle) => void;
};

export function CycleDrawer({ cycle, opened, onClose, onOpenFieldBook }: Props) {
  const can = useCan();
  const canWrite = can('production:write');
  const invalidate = useInvalidateProduction();
  const { data: plots = [] } = useActiveList(plotsResource);
  const { data: crops = [] } = useActiveList(cropsResource);
  const [endDate, setEndDate] = useState<string | null>(dayjs().format('YYYY-MM-DD'));
  const finished = cycle?.status === 'finished';

  const form = useDrawerForm<Cycle, Values>({
    opened,
    record: cycle,
    empty: EMPTY,
    toValues: (c) => ({
      plot_id: c.plot.id,
      crop_id: c.crop.id,
      area_ha: c.area_ha,
      start_date: c.start_date,
      expected_end_date: c.expected_end_date,
      notes: c.notes,
    }),
    validate: { plot_id: required, crop_id: required, area_ha: required, start_date: required },
  });

  async function submit(values: Values) {
    const common = {
      area_ha: values.area_ha as string,
      start_date: values.start_date as string,
      expected_end_date: values.expected_end_date,
      notes: values.notes,
    };
    if (cycle) await cyclesApi.update(cycle.id, common);
    else
      await cyclesApi.create({
        ...common,
        plot_id: values.plot_id as string,
        crop_id: values.crop_id as string,
      });
    notifySuccess(cycle ? 'Cultivo actualizado.' : 'Cultivo empezado.');
    await invalidate();
  }

  async function run(action: () => Promise<unknown>, message: string) {
    try {
      await action();
      notifySuccess(message);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  function openFinish() {
    if (!cycle) return;
    modals.openConfirmModal({
      title: `Finalizar ${cycle.name}`,
      children: (
        <Stack>
          <Text size="sm">
            Al finalizar, sus costos quedan congelados y no se pueden cargar ni modificar labores.
            Solo Soporte puede reabrirlo.
          </Text>
          <DateInput label="Fecha de fin" defaultValue={endDate} onChange={setEndDate} />
        </Stack>
      ),
      labels: { confirm: 'Finalizar', cancel: 'Cancelar' },
      onConfirm: () =>
        void run(
          () => cyclesApi.finish(cycle.id, endDate ?? dayjs().format('YYYY-MM-DD')),
          'Cultivo finalizado.',
        ),
    });
  }

  function openReopen() {
    if (!cycle) return;
    let reason = '';
    modals.openConfirmModal({
      title: `Reabrir ${cycle.name}`,
      children: (
        <TextInput label="Motivo" required onChange={(e) => (reason = e.currentTarget.value)} />
      ),
      labels: { confirm: 'Reabrir', cancel: 'Cancelar' },
      onConfirm: () =>
        void run(() => cyclesApi.reopen(cycle.id, reason || 'Sin motivo'), 'Cultivo reabierto.'),
    });
  }

  const freeArea = (plotId: string | null) => plots.find((p) => p.id === plotId)?.area_ha;

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={cycle ? cycle.name : 'Empezar cultivo'}
      form={form}
      isEdit={cycle !== null}
      onSubmit={submit}
      readOnly={!canWrite || finished}
      size="lg"
      extraActions={
        cycle && (
          <>
            <HistoryButton table="crop_cycles" recordId={cycle.id} />
            <Button variant="subtle" onClick={() => onOpenFieldBook(cycle)}>
              Cuaderno
            </Button>
            {!finished && canWrite && (
              <Button variant="subtle" color="orange" onClick={openFinish}>
                Finalizar
              </Button>
            )}
            {finished && can('production:reopen_cycle') && (
              <Button variant="subtle" onClick={openReopen}>
                Reabrir
              </Button>
            )}
          </>
        )
      }
    >
      {cycle && (
        <Paper withBorder p="sm">
          <Group justify="space-between" mb="xs">
            <Text size="sm" c="dimmed">
              {cycle.farm.name} · Temporada {cycle.season.name}
            </Text>
            <Badge color={finished ? 'gray' : 'green'}>
              {finished ? `Finalizado ${formatDate(cycle.end_date)}` : 'En curso'}
            </Badge>
          </Group>
          <CycleSummary cycle={cycle} />
        </Paper>
      )}
      {finished && (
        <Alert variant="light">Cultivo finalizado: sus datos y costos quedan fijos.</Alert>
      )}
      <SimpleGrid cols={2}>
        <Select
          label="Lote"
          required
          searchable
          data={plots.map((p) => ({ value: p.id, label: `${p.farm.name} · ${p.name}` }))}
          disabled={cycle !== null}
          {...form.getInputProps('plot_id')}
        />
        <Select
          label="Tipo de cultivo"
          required
          searchable
          data={crops.map((c) => ({ value: c.id, label: c.name }))}
          disabled={cycle !== null}
          {...form.getInputProps('crop_id')}
        />
        <NumberInput
          label="Superficie (ha)"
          description={
            freeArea(form.values.plot_id)
              ? `El lote tiene ${formatNumber(freeArea(form.values.plot_id) as string, 'quantity')} ha`
              : undefined
          }
          required
          kind="quantity"
          disabled={!canWrite || finished}
          {...form.getInputProps('area_ha')}
        />
        <DateInput
          label="Inicio"
          required
          disabled={!canWrite || finished}
          {...form.getInputProps('start_date')}
        />
        <DateInput
          label="Fin estimado"
          disabled={!canWrite || finished}
          {...form.getInputProps('expected_end_date')}
        />
      </SimpleGrid>
      <Textarea
        label="Observaciones"
        autosize
        disabled={!canWrite || finished}
        {...form.getInputProps('notes')}
      />
    </EntityDrawer>
  );
}
