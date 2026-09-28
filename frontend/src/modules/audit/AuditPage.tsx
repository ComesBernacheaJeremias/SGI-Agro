import { Badge, Modal, Select, Stack, Tabs, Text } from '@mantine/core';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { type Column, DataTable } from '@/shared/crud/DataTable';
import { useListState } from '@/shared/crud/hooks';
import { DateInput } from '@/shared/components/DateInput';
import { formatAuditValue } from '@/shared/format/audit';
import { formatDate } from '@/shared/format/date';
import { PageHeader } from '@/shared/ui/PageHeader';

import { describeDevice } from './device';

type Entry = components['schemas']['AuditEntryOut'];

// Entidades con historial (se agregan a medida que se implementan módulos)
const TABLES = [
  { value: 'users', label: 'Usuarios' },
  { value: 'roles', label: 'Roles' },
  { value: 'products', label: 'Productos' },
  { value: 'parties', label: 'Clientes/Proveedores' },
  { value: 'warehouses', label: 'Almacenes' },
  { value: 'product_categories', label: 'Categorías' },
  { value: 'units', label: 'Unidades' },
  { value: 'stock_documents', label: 'Comprobantes de stock' },
  { value: 'crop_cycles', label: 'Ciclos' },
  { value: 'field_operations', label: 'Labores' },
  { value: 'plots', label: 'Lotes' },
  { value: 'farms', label: 'Establecimientos' },
  { value: 'crops', label: 'Cultivos' },
  { value: 'assets', label: 'Activos' },
  { value: 'recipes', label: 'Recetas' },
  { value: 'production_orders', label: 'Preparaciones' },
  { value: 'commercial_documents', label: 'Compras y ventas' },
  { value: 'payments', label: 'Cobros y pagos' },
  { value: 'cash_movements', label: 'Movimientos de caja' },
  { value: 'cash_accounts', label: 'Cajas y bancos' },
  { value: 'expense_categories', label: 'Categorías de gasto' },
  { value: 'maintenances', label: 'Mantenimientos' },
  { value: 'maintenance_plans', label: 'Planes de mantenimiento' },
  { value: 'asset_meter_readings', label: 'Lecturas de medidor' },
];

const ACTIONS = [
  { value: 'create', label: 'Alta' },
  { value: 'update', label: 'Modificación' },
  { value: 'deactivate', label: 'Desactivación' },
  { value: 'activate', label: 'Reactivación' },
  { value: 'cancel', label: 'Anulación' },
  { value: 'delete', label: 'Eliminación' },
];

const actionLabel = (code: string) => ACTIONS.find((a) => a.value === code)?.label ?? code;

const COLUMNS: Column<Entry>[] = [
  { key: 'at', header: 'Fecha y hora', render: (e) => formatDate(e.at, 'dateTime') },
  { key: 'user_name', header: 'Usuario', render: (e) => e.user_name ?? 'Sistema' },
  { key: 'action', header: 'Acción', render: (e) => actionLabel(e.action) },
  { key: 'table_label', header: 'Entidad' },
  {
    key: 'changes',
    header: 'Campos',
    hideOnMobile: true,
    render: (e) => e.changes.map((c) => c.label).join(', '),
  },
];

type LoginEvent = components['schemas']['LoginEventOut'];

const LOGIN_RESULTS = [
  { value: 'success', label: 'Ingreso correcto' },
  { value: 'failed', label: 'Usuario o contraseña incorrectos' },
  { value: 'locked', label: 'Cuenta bloqueada' },
  { value: 'blocked_ip', label: 'IP bloqueada por intentos' },
];

const LOGIN_COLUMNS: Column<LoginEvent>[] = [
  { key: 'created_at', header: 'Fecha', render: (e) => formatDate(e.created_at, 'dateTime') },
  { key: 'username', header: 'Usuario' },
  {
    key: 'result',
    header: 'Resultado',
    render: (e) => (
      <Badge color={e.result === 'success' ? 'green' : 'red'} variant="light">
        {e.result_label}
      </Badge>
    ),
  },
  { key: 'ip', header: 'IP', hideOnMobile: true },
  {
    key: 'user_agent',
    header: 'Dispositivo',
    hideOnMobile: true,
    render: (e) => (
      <Text size="xs" c="dimmed" title={e.user_agent ?? undefined}>
        {describeDevice(e.user_agent)}
      </Text>
    ),
  },
];

/** Intentos de ingreso al sistema (para ver si alguien anda probando contraseñas). */
function LoginsTab() {
  const list = useListState();
  const [result, setResult] = useState<string | null>(null);
  const query = {
    page: list.page,
    page_size: 50,
    q: list.params.q,
    result: (result ?? undefined) as LoginEvent['result'] | undefined,
  };
  const { data, isFetching } = useQuery({
    queryKey: ['audit', 'logins', query],
    queryFn: async () => unwrap(await api.GET('/api/v1/audit/logins', { params: { query } })),
    placeholderData: keepPreviousData,
  });
  return (
    <DataTable
      columns={LOGIN_COLUMNS}
      list={list}
      data={data}
      loading={isFetching}
      searchPlaceholder="Usuario o IP…"
      showActiveFilter={false}
      filters={
        <Select
          placeholder="Resultado"
          data={LOGIN_RESULTS}
          value={result}
          onChange={(v) => {
            setResult(v);
            list.setPage(1);
          }}
          clearable
          w={240}
        />
      }
    />
  );
}

/** Historial: cambios en los datos y accesos al sistema (dueño y soporte). */
export function AuditPage() {
  return (
    <>
      <PageHeader title="Historial" />
      <Tabs defaultValue="changes" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="changes">Cambios</Tabs.Tab>
          <Tabs.Tab value="logins">Accesos</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="changes">
          <ChangesTab />
        </Tabs.Panel>
        <Tabs.Panel value="logins">
          <LoginsTab />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}

/** Cambios en los datos, con filtros. */
function ChangesTab() {
  const list = useListState();
  const [table, setTable] = useState<string | null>(null);
  const [action, setAction] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);
  const [selected, setSelected] = useState<Entry | null>(null);

  const query = {
    page: list.page,
    page_size: 50,
    table: table ?? undefined,
    action: action ?? undefined,
    date_from: dateFrom ?? undefined,
    date_to: dateTo ?? undefined,
  };
  const { data, isFetching } = useQuery({
    queryKey: ['audit', 'general', query],
    queryFn: async () => unwrap(await api.GET('/api/v1/audit', { params: { query } })),
    placeholderData: keepPreviousData,
  });

  // Cualquier cambio de filtro vuelve a la página 1
  const withReset =
    <V,>(setter: (value: V) => void) =>
    (value: V) => {
      setter(value);
      list.setPage(1);
    };

  return (
    <>
      <DataTable
        columns={COLUMNS}
        list={list}
        data={data}
        loading={isFetching}
        onRowClick={setSelected}
        showSearch={false}
        showActiveFilter={false}
        filters={
          <>
            <Select
              placeholder="Entidad"
              data={TABLES}
              value={table}
              onChange={withReset(setTable)}
              clearable
              w={160}
            />
            <Select
              placeholder="Acción"
              data={ACTIONS}
              value={action}
              onChange={withReset(setAction)}
              clearable
              w={160}
            />
            <DateInput
              placeholder="Desde"
              value={dateFrom}
              onChange={withReset(setDateFrom)}
              w={140}
            />
            <DateInput placeholder="Hasta" value={dateTo} onChange={withReset(setDateTo)} w={140} />
          </>
        }
      />
      <Modal
        opened={selected !== null}
        onClose={() => setSelected(null)}
        title={selected ? `${actionLabel(selected.action)} · ${selected.table_label}` : ''}
      >
        {selected && (
          <Stack gap={4}>
            <Text size="sm" c="dimmed">
              {formatDate(selected.at, 'dateTime')} · {selected.user_name ?? 'Sistema'}
            </Text>
            {selected.changes.map((c) => (
              <Text size="sm" key={c.field}>
                <b>{c.label}:</b> {formatAuditValue(c.before)} → {formatAuditValue(c.after)}
              </Text>
            ))}
          </Stack>
        )}
      </Modal>
    </>
  );
}
