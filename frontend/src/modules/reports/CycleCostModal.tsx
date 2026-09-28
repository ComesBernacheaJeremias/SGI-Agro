import { Badge, Group, Loader, Modal, Paper, SimpleGrid, Stack, Table, Text } from '@mantine/core';
import type { ReactNode } from 'react';

import { CycleSummary } from '@/modules/production/CycleDrawer';
import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';

import { useCycleCost } from './api';

type Column<T> = { header: string; value: (row: T) => ReactNode; numeric?: boolean };

/** Tabla chica de un desglose (sin paginar). */
function Breakdown<T>({
  title,
  rows,
  columns,
}: {
  title: string;
  rows: T[];
  columns: Column<T>[];
}) {
  if (rows.length === 0) return null;
  return (
    <Stack gap={4}>
      <Text fw={600} size="sm">
        {title}
      </Text>
      <Table verticalSpacing={4} fz="sm">
        <Table.Thead>
          <Table.Tr>
            {columns.map((c) => (
              <Table.Th key={c.header} ta={c.numeric ? 'right' : 'left'}>
                {c.header}
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row, i) => (
            <Table.Tr key={i}>
              {columns.map((c) => (
                <Table.Td key={c.header} ta={c.numeric ? 'right' : 'left'}>
                  {c.value(row)}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}

type Props = { cycleId: string | null; onClose: () => void };

/** Costo y rentabilidad de un ciclo con todos sus desgloses. */
export function CycleCostModal({ cycleId, onClose }: Props) {
  const { data, isLoading } = useCycleCost(cycleId);
  const cycle = data?.cycle;
  return (
    <Modal
      opened={cycleId !== null}
      onClose={onClose}
      size="xl"
      title={cycle ? `Costos · ${cycle.name}` : 'Costos del cultivo'}
    >
      {isLoading && <Loader />}
      {data && cycle && (
        <Stack>
          <Group gap="xs">
            <Text size="sm" c="dimmed">
              {cycle.farm.name} · {cycle.plot.name} · {formatNumber(cycle.area_ha, 'quantity')} ha ·
              Temporada {cycle.season.name}
            </Text>
            <Badge color={cycle.status === 'finished' ? 'gray' : 'green'} variant="light">
              {cycle.status === 'finished' ? 'Finalizado' : 'En curso'}
            </Badge>
          </Group>
          <Paper withBorder p="sm">
            <CycleSummary cycle={cycle} />
          </Paper>
          <Paper withBorder p="sm">
            <SimpleGrid cols={{ base: 2, sm: 4 }}>
              {[
                ['Ingresos', formatMoney(data.revenue)],
                ['Margen', formatMoney(data.margin)],
                ['Margen por ha', formatMoney(data.margin_per_ha)],
                [
                  'Vendido',
                  `${formatNumber(data.sold_quantity, 'quantity')} ${cycle.harvest_unit}`,
                ],
              ].map(([label, value]) => (
                <Stack key={label} gap={0}>
                  <Text size="xs" c="dimmed">
                    {label}
                  </Text>
                  <Text
                    fw={700}
                    c={label === 'Margen' && Number(data.margin) < 0 ? 'red' : undefined}
                  >
                    {value}
                  </Text>
                </Stack>
              ))}
            </SimpleGrid>
          </Paper>
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Breakdown
              title="Insumos"
              rows={data.inputs}
              columns={[
                { header: 'Producto', value: (r) => r.name },
                {
                  header: 'Cantidad',
                  value: (r) => `${formatNumber(r.quantity, 'quantity')} ${r.unit}`,
                  numeric: true,
                },
                { header: 'Costo', value: (r) => formatMoney(r.amount), numeric: true },
              ]}
            />
            <Breakdown
              title="Maquinaria"
              rows={data.machinery}
              columns={[
                { header: 'Activo', value: (r) => r.name },
                {
                  header: 'Uso',
                  value: (r) => `${formatNumber(r.quantity, 'quantity')} ${r.unit}`,
                  numeric: true,
                },
                { header: 'Costo', value: (r) => formatMoney(r.amount), numeric: true },
              ]}
            />
            <Breakdown
              title="Servicios y gastos"
              rows={data.expenses}
              columns={[
                { header: 'Categoría', value: (r) => r.name },
                { header: 'Importe', value: (r) => formatMoney(r.amount), numeric: true },
              ]}
            />
            <Breakdown
              title="Ventas por partida"
              rows={data.sales}
              columns={[
                { header: 'Partida', value: (r) => r.batch },
                {
                  header: 'Cantidad',
                  value: (r) => `${formatNumber(r.quantity, 'quantity')} ${cycle.harvest_unit}`,
                  numeric: true,
                },
                { header: 'Ingreso', value: (r) => formatMoney(r.revenue), numeric: true },
              ]}
            />
          </SimpleGrid>
          <Breakdown
            title="Por tipo de labor"
            rows={data.by_operation_type}
            columns={[
              { header: 'Labor', value: (r) => r.name },
              { header: 'Insumos', value: (r) => formatMoney(r.inputs), numeric: true },
              { header: 'Maquinaria', value: (r) => formatMoney(r.machinery), numeric: true },
              { header: 'Total', value: (r) => formatMoney(r.total), numeric: true },
            ]}
          />
          <Breakdown
            title="Por mes"
            rows={data.by_month}
            columns={[
              { header: 'Mes', value: (r) => formatDate(`${r.month}-01`, 'month') },
              { header: 'Insumos', value: (r) => formatMoney(r.inputs), numeric: true },
              { header: 'Maquinaria', value: (r) => formatMoney(r.machinery), numeric: true },
              {
                header: 'Servicios y gastos',
                value: (r) => formatMoney(r.expenses),
                numeric: true,
              },
              { header: 'Total', value: (r) => formatMoney(r.total), numeric: true },
            ]}
          />
        </Stack>
      )}
    </Modal>
  );
}
