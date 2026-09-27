import { Anchor, Group, Loader, Paper, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { useSession } from '@/app/auth/session';
import { PLAN_STATE, planAlertText } from '@/modules/assets/api';
import { alertText } from '@/modules/inventory/api';
import { type ResultSummary, useDashboard } from '@/modules/reports/api';
import { formatMoney, formatNumber } from '@/shared/format/number';
import { PageHeader } from '@/shared/ui/PageHeader';

function Card({ title, to, children }: { title: string; to?: string; children: ReactNode }) {
  return (
    <Paper withBorder p="md">
      <Group justify="space-between" mb="xs">
        <Title order={4}>{title}</Title>
        {to && (
          <Anchor component={Link} to={to} size="sm">
            Ver más
          </Anchor>
        )}
      </Group>
      {children}
    </Paper>
  );
}

function Figure({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Stack gap={0}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={700} size="lg" c={color}>
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
  return (
    <Table verticalSpacing={4}>
      <Table.Thead>
        <Table.Tr>
          <Table.Th />
          <Table.Th ta="right">Esta temporada</Table.Th>
          <Table.Th ta="right">Anterior (misma fecha)</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {RESULT_ROWS.map(([key, label, sign]) => {
          const bold = key === 'result';
          const value = (r: ResultSummary) => Number(r[key]) * sign;
          return (
            <Table.Tr key={key} fw={bold ? 700 : undefined}>
              <Table.Td>{label}</Table.Td>
              <Table.Td ta="right" c={bold && value(current) < 0 ? 'red' : undefined}>
                {formatMoney(value(current))}
              </Table.Td>
              <Table.Td ta="right" c="dimmed">
                {formatMoney(value(previous))}
              </Table.Td>
            </Table.Tr>
          );
        })}
      </Table.Tbody>
    </Table>
  );
}

/** Tablero: cada tarjeta aparece si el usuario tiene permiso para ver ese módulo. */
export function DashboardPage() {
  const session = useSession();
  const firstName = session.status === 'authenticated' ? session.user.full_name.split(' ')[0] : '';
  const { data, isLoading } = useDashboard();
  const empty = data && !data.result && !data.cycles && !data.stock && !data.accounts && !data.cash;
  return (
    <>
      <PageHeader title={firstName ? `Hola, ${firstName}` : 'Tablero'} />
      {isLoading && <Loader />}
      {empty && <Text c="dimmed">No hay información para mostrar con tus permisos.</Text>}
      {data && (
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          {data.result && (
            <Card title={`Resultado · temporada ${data.result.name}`} to="/costos">
              <ResultTable current={data.result.current} previous={data.result.previous} />
            </Card>
          )}
          {data.cycles && (
            <Card title="Ciclos en curso" to="/produccion">
              <Group mb="xs">
                <Figure label="Ciclos" value={String(data.cycles.active)} />
                <Figure label="Costo acumulado" value={formatMoney(data.cycles.total_cost)} />
              </Group>
              {data.cycles.top.map((c) => (
                <Group key={c.id} justify="space-between" wrap="nowrap">
                  <Text size="sm" lineClamp={1}>
                    {c.name} · {c.plot.name}
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
                  color={Number(data.accounts.receivable_overdue) > 0 ? 'red' : undefined}
                />
                <Figure label="A pagar" value={formatMoney(data.accounts.payable)} />
                <Figure
                  label="Vencido a pagar"
                  value={formatMoney(data.accounts.payable_overdue)}
                  color={Number(data.accounts.payable_overdue) > 0 ? 'red' : undefined}
                />
              </SimpleGrid>
            </Card>
          )}
          {data.cash && (
            <Card title="Cajas y bancos" to="/comercial">
              <Figure label="Total" value={formatMoney(data.cash.total)} />
              {data.cash.accounts.map((a) => (
                <Group key={a.account.id} justify="space-between">
                  <Text size="sm">{a.account.name}</Text>
                  <Text size="sm" c={Number(a.balance) < 0 ? 'red' : undefined}>
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
              <Figure label="Valor del stock" value={formatMoney(data.stock.value)} />
              {data.stock.alerts.length > 0 && (
                <Stack gap={2} mt="xs">
                  <Text size="sm" fw={600} c="orange">
                    Necesitás comprar ({data.stock.alerts.length})
                  </Text>
                  {data.stock.alerts.slice(0, 5).map((a) => (
                    <Text key={a.product.id} size="xs" c="dimmed">
                      {alertText(a)}
                    </Text>
                  ))}
                </Stack>
              )}
            </Card>
          )}
        </SimpleGrid>
      )}
    </>
  );
}
