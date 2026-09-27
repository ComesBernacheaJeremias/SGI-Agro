import { Badge, Group, Loader, Modal, Paper, Stack, Text, Timeline } from '@mantine/core';

import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';

import { type Cycle, useFieldBook } from './api';
import { CycleSummary } from './CycleDrawer';

type Props = { cycle: Cycle | null; onClose: () => void; onOpenOperation: (id: string) => void };

/** Cuaderno de campo: todas las labores del ciclo en orden, con insumos, dosis y costos. */
export function FieldBookModal({ cycle, onClose, onOpenOperation }: Props) {
  const { data, isLoading } = useFieldBook(cycle?.id ?? null);
  return (
    <Modal
      opened={cycle !== null}
      onClose={onClose}
      title={`Cuaderno de campo · ${cycle?.name ?? ''}`}
      size="xl"
    >
      {isLoading && <Loader />}
      {data && (
        <Stack>
          <Paper withBorder p="sm">
            <CycleSummary cycle={data.cycle} />
          </Paper>
          {data.entries.length === 0 && <Text c="dimmed">Todavía no hay labores cargadas.</Text>}
          <Timeline bulletSize={16} lineWidth={2}>
            {data.entries.map((e) => (
              <Timeline.Item
                key={e.id}
                title={
                  <Group gap="xs">
                    <Text
                      fw={600}
                      size="sm"
                      style={{ cursor: 'pointer' }}
                      onClick={() => onOpenOperation(e.id)}
                    >
                      {formatDate(e.date)} · {e.operation_type}
                    </Text>
                    {e.is_harvest && <Badge size="xs">Cosecha</Badge>}
                    <Text size="xs" c="dimmed">
                      {e.number} · {formatNumber(e.area_ha, 'quantity')} ha
                    </Text>
                  </Group>
                }
              >
                <Stack gap={2} mt={4}>
                  {e.inputs.map((i) => (
                    <Text size="sm" key={i.product}>
                      {i.product}: {formatNumber(i.quantity, 'quantity')} {i.unit}
                      {i.dose_per_ha &&
                        ` (${formatNumber(i.dose_per_ha, 'quantity')} ${i.unit}/ha)`}{' '}
                      · {formatMoney(i.cost)}
                    </Text>
                  ))}
                  {e.assets.map((a) => (
                    <Text size="sm" key={a.asset}>
                      {a.asset}: {formatNumber(a.usage, 'quantity')} {a.unit} ·{' '}
                      {formatMoney(a.cost)}
                    </Text>
                  ))}
                  {e.harvest_quantity && (
                    <Text size="sm">
                      Cosechado: {formatNumber(e.harvest_quantity, 'quantity')} {e.harvest_unit}
                      {e.batch_code && ` · Partida ${e.batch_code}`}
                    </Text>
                  )}
                  {e.notes && (
                    <Text size="xs" c="dimmed">
                      {e.notes}
                    </Text>
                  )}
                  <Text size="xs" fw={500}>
                    Costo: {formatMoney(e.cost)}
                  </Text>
                </Stack>
              </Timeline.Item>
            ))}
          </Timeline>
        </Stack>
      )}
    </Modal>
  );
}
