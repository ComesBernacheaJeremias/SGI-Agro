import { Anchor, Group, Loader, SimpleGrid, Stack, Table, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { PLAN_STATE, planAlertText } from '@/modules/assets/api';
import { alertText, ownProduceNote, STOCK_ALERT_COLOR } from '@/modules/inventory/api';
import { type ResultSummary, useDashboard } from '@/modules/reports/api';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { InfoCard } from '@/shared/ui/InfoCard';
import { PageHeader } from '@/shared/ui/PageHeader';

/** Tarjeta del tablero con "Ver más" hacia el módulo. */
function Card({ title, to, children }: { title: string; to: string; children: ReactNode }) {
  return (
    <InfoCard
      title={title}
      action={
        <Anchor component={Link} to={to} size="sm">
          Ver más
        </Anchor>
      }
    >
      {children}
    </InfoCard>
  );
}

/** Número clave de la fila superior (en rojo si es negativo) y una aclaración opcional. */
function Kpi({ label, value, note }: KpiProps) {
  return (
    <InfoCard title={label}>
      <Text
        fw={700}
        fz={{ base: 22, sm: 26 }}
        lh={1.1}
        c={value < 0 ? 'red.7' : undefined}
        style={{ whiteSpace: 'nowrap' }}
      >
        {formatMoney(value)}
      </Text>
      {note && (
        <Text size="xs" c="dimmed" mt={4}>
          {note}
        </Text>
      )}
    </InfoCard>
  );
}

type KpiProps = { label: string; value: number; note?: string | null };

function Figure({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Stack gap={0}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={700} size="lg" c={color} style={{ whiteSpace: 'nowrap' }}>
        {value}
      </Text>
    </Stack>
  );
}

const RESULT_ROWS: [keyof ResultSummary, string, number][] = [
  ['sales', 'Ventas', 1],
  ['cost_of_sales', 'Costo de lo vendido', -1],
  ['production', 'Costos de producción', -1],
  ['losses', 'Mermas', -1],
  ['structure', 'Gastos de estructura', -1],
  ['result', 'Resultado', 1],
];

function ResultTable({ current, previous }: { current: ResultSummary; previous: ResultSummary }) {
  // Sin datos de la temporada anterior no se muestra la columna (serían todos ceros)
  const hasPrevious = RESULT_ROWS.some(([key]) => Number(previous[key]) !== 0);
  return (
    <Table verticalSpacing={4}>
      <Table.Thead>
        <Table.Tr>
          <Table.Th />
          <Table.Th ta="right">Esta temporada</Table.Th>
          {hasPrevious && <Table.Th ta="right">Anterior (misma fecha)</Table.Th>}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {RESULT_ROWS.map(([key, label, sign]) => {
          const bold = key === 'result';
          const value = (r: ResultSummary) => Number(r[key]) * sign;
          return (
            <Table.Tr key={key} fw={bold ? 700 : undefined}>
              <Table.Td>{label}</Table.Td>
              <Table.Td ta="right" c={bold && value(current) < 0 ? 'red.7' : undefined}>
                {formatMoney(value(current))}
              </Table.Td>
              {hasPrevious && (
                <Table.Td ta="right" c="dimmed">
                  {formatMoney(value(previous))}
                </Table.Td>
              )}
            </Table.Tr>
          );
        })}
      </Table.Tbody>
    </Table>
  );
}

/** Tablero: cada tarjeta aparece si el usuario tiene permiso para ver ese módulo. */
export function DashboardPage() {
  const { data, isLoading } = useDashboard();
  const empty = data && !data.result && !data.cycles && !data.stock && !data.accounts && !data.cash;
  const kpis: KpiProps[] = [
    data?.result && { label: 'Resultado', value: Number(data.result.current.result) },
    data?.accounts && { label: 'A cobrar', value: Number(data.accounts.receivable) },
    data?.cash && { label: 'Caja y bancos', value: Number(data.cash.total) },
    data?.stock && {
      label: 'Valor del stock',
      // Incluye la producción propia valorizada por costo del ciclo (informativo, ADR-012)
      value: Number(data.stock.value) + Number(data.stock.own_produce_value),
      note: ownProduceNote(data.stock.own_produce_value, data.stock.own_produce_provisional),
    },
  ].filter((kpi): kpi is KpiProps => Boolean(kpi));
  return (
    <>
      <PageHeader
        title="Tablero"
        subtitle={data?.result ? `Temporada ${data.result.name}` : undefined}
      />
      {isLoading && <Loader />}
      {empty && <Text c="dimmed">No hay información para mostrar con tus permisos.</Text>}
      {/* Celular: una columna, así el número entra en una línea (montos de millones incluidos) */}
      {kpis.length > 0 && (
        <SimpleGrid cols={{ base: 1, xs: 2, md: kpis.length }} mb="md">
          {kpis.map((kpi) => (
            <Kpi key={kpi.label} {...kpi} />
          ))}
        </SimpleGrid>
      )}
      {data && (
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          {data.result && (
            <Card title="Resultado de gestión" to="/costos">
              <ResultTable current={data.result.current} previous={data.result.previous} />
            </Card>
          )}
          {data.cycles && (
            <Card title="Cultivos en curso" to="/produccion">
              <Group mb="xs">
                <Figure label="Cultivos" value={String(data.cycles.active)} />
                <Figure label="Costo acumulado" value={formatMoney(data.cycles.total_cost)} />
              </Group>
              {data.cycles.top.map((c) => (
                <Group key={c.id} justify="space-between" wrap="nowrap">
                  <Text size="sm" lineClamp={1}>
                    {c.name}
                  </Text>
                  <Text size="sm" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                    {formatMoney(c.total_cost)}
                    {Number(c.harvested_quantity) > 0 &&
                      ` · ${formatNumber(c.harvested_quantity, 'quantity')} ${c.harvest_unit}`}
                  </Text>
                </Group>
              ))}
            </Card>
          )}
          {data.accounts && (
            <Card title="Cuentas corrientes" to="/comercial">
              <SimpleGrid cols={2}>
                <Figure label="A cobrar" value={formatMoney(data.accounts.receivable)} />
                <Figure
                  label="Vencido a cobrar"
                  value={formatMoney(data.accounts.receivable_overdue)}
                  color={Number(data.accounts.receivable_overdue) > 0 ? 'red.7' : undefined}
                />
                <Figure label="A pagar" value={formatMoney(data.accounts.payable)} />
                <Figure
                  label="Vencido a pagar"
                  value={formatMoney(data.accounts.payable_overdue)}
                  color={Number(data.accounts.payable_overdue) > 0 ? 'red.7' : undefined}
                />
              </SimpleGrid>
            </Card>
          )}
          {data.cash && (
            <Card title="Cajas y bancos" to="/comercial">
              {data.cash.accounts.map((a) => (
                <Group key={a.account.id} justify="space-between">
                  <Text size="sm">{a.account.name}</Text>
                  <Text size="sm" c={Number(a.balance) < 0 ? 'red.7' : undefined}>
                    {formatMoney(a.balance)}
                  </Text>
                </Group>
              ))}
            </Card>
          )}
          {data.maintenance && data.maintenance.length > 0 && (
            <Card title="Mantenimientos" to="/activos">
              <Stack gap={4}>
                {data.maintenance.map((m) => (
                  <Text key={m.plan.id} size="sm" c={PLAN_STATE[m.state].color}>
                    {planAlertText(m)}
                  </Text>
                ))}
              </Stack>
            </Card>
          )}
          {data.stock && (
            <Card title="Stock" to="/inventario">
              {data.stock.alerts.length > 0 ? (
                <Stack gap={2}>
                  <Text size="sm" fw={600} c={`${STOCK_ALERT_COLOR}.8`}>
                    Necesitás comprar ({data.stock.alerts.length})
                  </Text>
                  {data.stock.alerts.slice(0, 5).map((a) => (
                    <Text key={a.product.id} size="sm">
                      {alertText(a)}
                    </Text>
                  ))}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">
                  Ningún producto por debajo del mínimo.
                </Text>
              )}
            </Card>
          )}
        </SimpleGrid>
      )}
    </>
  );
}
