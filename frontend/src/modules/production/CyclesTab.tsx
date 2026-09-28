import { Badge, Group, SegmentedControl, Select, SimpleGrid, Stack, Text } from '@mantine/core';
import { useState } from 'react';

import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { InfoCard } from '@/shared/ui/InfoCard';

import { type Cycle, useCycles, useSeasons } from './api';

type Props = { onOpen: (cycle: Cycle) => void };

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={0}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600}>
        {value}
      </Text>
    </Stack>
  );
}

/** Tablero de ciclos: una tarjeta por ciclo con costo, cosecha y rinde. */
export function CyclesTab({ onOpen }: Props) {
  const [status, setStatus] = useState<'active' | 'finished' | 'all'>('active');
  const [seasonId, setSeasonId] = useState<string | null>(null);
  const { data: seasons = [] } = useSeasons();
  const { data } = useCycles({
    status: status === 'all' ? undefined : status,
    season_id: seasonId ?? undefined,
    page_size: 100,
  });

  return (
    <>
      <Group mb="md" wrap="wrap">
        <SegmentedControl
          size="xs"
          value={status}
          onChange={(v) => setStatus(v as typeof status)}
          data={[
            { value: 'active', label: 'En curso' },
            { value: 'finished', label: 'Finalizados' },
            { value: 'all', label: 'Todos' },
          ]}
        />
        <Select
          placeholder="Temporada"
          data={seasons.map((s) => ({ value: s.id, label: s.name }))}
          value={seasonId}
          onChange={setSeasonId}
          clearable
          w={150}
        />
      </Group>
      {data?.items.length === 0 && <Text c="dimmed">No hay ciclos para mostrar.</Text>}
      <SimpleGrid cols={{ base: 1, md: 2, lg: 3 }}>
        {data?.items.map((c) => (
          <InfoCard key={c.id} onClick={() => onOpen(c)}>
            <Group justify="space-between" mb={4} wrap="nowrap">
              <Text fw={700} lineClamp={1}>
                {c.crop.name}
              </Text>
              <Badge color={c.status === 'finished' ? 'gray' : 'green'} variant="light">
                {c.status === 'finished' ? 'Finalizado' : 'En curso'}
              </Badge>
            </Group>
            <Text size="sm" c="dimmed">
              {c.farm.name} · {c.plot.name} · {formatNumber(c.area_ha, 'quantity')} ha
            </Text>
            <Text size="xs" c="dimmed" mb="sm">
              Desde {formatDate(c.start_date)} · Temporada {c.season.name}
            </Text>
            <SimpleGrid cols={3} spacing="xs">
              <Stat label="Costo" value={formatMoney(c.total_cost)} />
              <Stat
                label="Cosechado"
                value={`${formatNumber(c.harvested_quantity, 'quantity')} ${c.harvest_unit}`}
              />
              <Stat
                label="Rinde"
                value={
                  c.yield_per_ha
                    ? `${formatNumber(c.yield_per_ha, 'quantity')} ${c.harvest_unit}/ha`
                    : '—'
                }
              />
            </SimpleGrid>
          </InfoCard>
        ))}
      </SimpleGrid>
    </>
  );
}
