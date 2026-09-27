import {
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconBan, IconPlus } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { Fragment, useEffect, useState } from 'react';

import { useCan } from '@/app/auth/session';
import { labelOf, useActiveList } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { type Column, DataTable } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useListState } from '@/shared/crud/hooks';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { formatDate } from '@/shared/format/date';
import { formatMoney } from '@/shared/format/number';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import {
  cashAccountsResource,
  type CashMovement,
  type CashMovementIn,
  expenseCategoriesResource,
  movementsApi,
  useCashBalances,
  useCashStatement,
  useCommercialOptions,
  useInvalidateCommercial,
  useMovements,
} from './api';
import {
  type Destination,
  destinationText,
  destinationValues,
  emptyDestination,
} from './destination';
import { DestinationField } from './DestinationField';

// --- Movimiento ---

type Values = {
  date: string | null;
  kind: CashMovementIn['kind'];
  cash_account_id: string | null;
  target_account_id: string | null;
  amount: string | null;
  description: string;
  expense_category_id: string | null;
  destination: Destination;
};

const empty = (): Values => ({
  date: dayjs().format('YYYY-MM-DD'),
  kind: 'expense',
  cash_account_id: null,
  target_account_id: null,
  amount: null,
  description: '',
  expense_category_id: null,
  destination: emptyDestination(),
});

const toValues = (m: CashMovement): Values => ({
  date: m.date,
  kind: m.kind,
  cash_account_id: m.cash_account.id,
  target_account_id: m.target_account?.id ?? null,
  amount: m.amount,
  description: m.description,
  expense_category_id: m.expense_category?.id ?? null,
  destination: destinationValues(m.destination),
});

type DrawerProps = { movement: CashMovement | null; opened: boolean; onClose: () => void };

export function MovementDrawer({ movement, opened, onClose }: DrawerProps) {
  const can = useCan();
  const invalidate = useInvalidateCommercial();
  const { data: options } = useCommercialOptions();
  const { data: accounts = [] } = useActiveList(cashAccountsResource);
  const { data: categories = [] } = useActiveList(expenseCategoriesResource);
  const readOnly = !can('cash:write') || movement?.status === 'cancelled';
  const form = useForm<Values>({
    initialValues: empty(),
    validate: {
      date: (v) => (v ? null : 'Obligatorio'),
      cash_account_id: (v) => (v ? null : 'Obligatorio'),
      amount: (v) => (Number(v) > 0 ? null : 'Obligatorio'),
      target_account_id: (v, values) =>
        values.kind !== 'transfer'
          ? null
          : !v
            ? 'Obligatorio'
            : v === values.cash_account_id
              ? 'Tiene que ser otra cuenta'
              : null,
      expense_category_id: (v, values) => (values.kind === 'expense' && !v ? 'Obligatorio' : null),
      description: (v, values) =>
        (values.kind === 'income' || values.kind === 'withdrawal') && !v.trim()
          ? 'Obligatorio'
          : null,
    },
  });
  useEffect(() => {
    if (!opened) return;
    form.setValues(movement ? toValues(movement) : empty());
    form.resetDirty();
    form.clearErrors();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al abrir o cambiar de registro
  }, [opened, movement]);

  const v = form.values;
  async function submit(values: Values) {
    const isExpense = values.kind === 'expense';
    const body: CashMovementIn = {
      date: values.date as string,
      kind: values.kind,
      cash_account_id: values.cash_account_id as string,
      target_account_id: values.kind === 'transfer' ? values.target_account_id : null,
      amount: values.amount as string,
      description: values.description,
      expense_category_id: isExpense ? values.expense_category_id : null,
      ...(isExpense ? values.destination : emptyDestination()),
    };
    const saved = movement
      ? await movementsApi.update(movement.id, body)
      : await movementsApi.create(body);
    notifySuccess(`Movimiento ${saved.number} guardado.`);
    await invalidate();
  }

  async function cancelMovement() {
    if (!movement) return;
    const confirmed = await confirmAction({
      message: `Se va a anular el movimiento ${movement.number}.`,
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!confirmed) return;
    try {
      await movementsApi.cancel(movement.id);
      notifySuccess(`Movimiento ${movement.number} anulado.`);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  const accountOptions = accounts.map((a) => ({ value: a.id, label: a.name }));
  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={movement ? `Movimiento ${movement.number}` : 'Nuevo movimiento de caja'}
      form={form}
      isEdit={movement !== null}
      onSubmit={submit}
      readOnly={readOnly}
      extraActions={
        movement && (
          <>
            <HistoryButton table="cash_movements" recordId={movement.id} />
            {movement.status === 'active' && can('cash:write') && (
              <Button
                variant="subtle"
                color="red"
                leftSection={<IconBan size={16} />}
                onClick={cancelMovement}
              >
                Anular
              </Button>
            )}
          </>
        )
      }
    >
      {movement?.status === 'cancelled' && (
        <Group>
          <Badge color="red">Anulado</Badge>
        </Group>
      )}
      <Select
        label="Tipo"
        data={options?.movement_kinds ?? []}
        allowDeselect={false}
        disabled={readOnly}
        {...form.getInputProps('kind')}
      />
      <SimpleGrid cols={2}>
        <DateInput label="Fecha" required disabled={readOnly} {...form.getInputProps('date')} />
        <NumberInput
          label="Importe"
          required
          kind="price"
          leftSection="$"
          disabled={readOnly}
          {...form.getInputProps('amount')}
        />
      </SimpleGrid>
      <SimpleGrid cols={v.kind === 'transfer' ? 2 : 1}>
        <Select
          label={v.kind === 'transfer' ? 'Desde' : 'Cuenta'}
          required
          data={accountOptions}
          disabled={readOnly}
          {...form.getInputProps('cash_account_id')}
        />
        {v.kind === 'transfer' && (
          <Select
            label="Hacia"
            required
            data={accountOptions}
            disabled={readOnly}
            {...form.getInputProps('target_account_id')}
          />
        )}
      </SimpleGrid>
      {v.kind === 'expense' && (
        <>
          <Select
            label="Categoría"
            required
            data={categories.map((c) => ({ value: c.id, label: c.name }))}
            searchable
            disabled={readOnly}
            {...form.getInputProps('expense_category_id')}
          />
          <Group gap="xs" align="flex-end" wrap="wrap">
            <DestinationField
              value={v.destination}
              onChange={(destination) => form.setFieldValue('destination', destination)}
              disabled={readOnly}
            />
          </Group>
        </>
      )}
      <TextInput
        label="Descripción"
        required={v.kind === 'income' || v.kind === 'withdrawal'}
        disabled={readOnly}
        {...form.getInputProps('description')}
      />
    </EntityDrawer>
  );
}

// --- Resumen de una cuenta ---

type StatementProps = { account: { id: string; name: string } | null; onClose: () => void };

function StatementModal({ account, onClose }: StatementProps) {
  const [from, setFrom] = useState<string | null>(dayjs().startOf('month').format('YYYY-MM-DD'));
  const { data, isLoading } = useCashStatement(account?.id ?? null, from);
  return (
    <Modal
      opened={account !== null}
      onClose={onClose}
      title={`Movimientos · ${account?.name ?? ''}`}
      size="xl"
    >
      <DateInput label="Desde" value={from} onChange={setFrom} w={160} mb="sm" />
      {isLoading && <Loader />}
      {data && (
        <Table.ScrollContainer minWidth={520}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                <Table.Th>Detalle</Table.Th>
                <Table.Th ta="right">Importe</Table.Th>
                <Table.Th ta="right">Saldo</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              <Table.Tr>
                <Table.Td />
                <Table.Td c="dimmed">Saldo anterior</Table.Td>
                <Table.Td />
                <Table.Td ta="right">{formatMoney(data.opening_balance)}</Table.Td>
              </Table.Tr>
              {data.rows.map((r) => (
                <Table.Tr key={`${r.source}-${r.id}`}>
                  <Table.Td>{formatDate(r.date)}</Table.Td>
                  <Table.Td>{r.label}</Table.Td>
                  <Table.Td ta="right" c={Number(r.amount) < 0 ? 'red' : 'green'}>
                    {formatMoney(r.amount)}
                  </Table.Td>
                  <Table.Td ta="right">{formatMoney(r.balance)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Modal>
  );
}

// --- Pestaña ---

export function CashTab() {
  const can = useCan();
  const list = useListState();
  const { data: options } = useCommercialOptions();
  const [at, setAt] = useState<string | null>(null);
  const { data: balances = [] } = useCashBalances(at);
  const { data, isFetching } = useMovements({ page: list.page, page_size: 50 });
  const [drawer, setDrawer] = useState<{ record: CashMovement | null } | null>(null);
  const [account, setAccount] = useState<{ id: string; name: string } | null>(null);

  const columns: Column<CashMovement>[] = [
    { key: 'date', header: 'Fecha', render: (m) => formatDate(m.date) },
    { key: 'kind', header: 'Tipo', render: (m) => labelOf(options?.movement_kinds, m.kind) },
    {
      key: 'account',
      header: 'Cuenta',
      render: (m) =>
        m.target_account
          ? `${m.cash_account.name} → ${m.target_account.name}`
          : m.cash_account.name,
    },
    {
      key: 'detail',
      header: 'Detalle',
      hideOnMobile: true,
      render: (m) =>
        m.kind === 'expense'
          ? `${m.expense_category?.name ?? ''} · ${destinationText(m.destination)}${m.description ? ` · ${m.description}` : ''}`
          : m.description,
    },
    { key: 'amount', header: 'Importe', align: 'right', render: (m) => formatMoney(m.amount) },
    {
      key: 'status',
      header: '',
      render: (m) =>
        m.status === 'cancelled' && (
          <Badge color="red" variant="light">
            Anulado
          </Badge>
        ),
    },
  ];

  const total = balances.reduce((s, b) => s + Number(b.balance), 0);
  return (
    <Stack>
      <DateInput label="Saldos al" placeholder="Hoy" value={at} onChange={setAt} w={160} />
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 4 }}>
        {balances.map((b) => (
          <Paper
            key={b.account.id}
            withBorder
            p="sm"
            style={{ cursor: 'pointer' }}
            onClick={() => setAccount(b.account)}
          >
            <Text size="xs" c="dimmed">
              {labelOf(options?.cash_account_kinds, b.kind)}
            </Text>
            <Text fw={600}>{b.account.name}</Text>
            <Text size="lg" fw={700} c={Number(b.balance) < 0 ? 'red' : undefined}>
              {formatMoney(b.balance)}
            </Text>
          </Paper>
        ))}
        {balances.length > 0 && (
          <Paper withBorder p="sm" bg="var(--mantine-color-default-hover)">
            <Text size="xs" c="dimmed">
              Total
            </Text>
            <Text fw={600}>Cajas y bancos</Text>
            <Text size="lg" fw={700}>
              {formatMoney(total)}
            </Text>
          </Paper>
        )}
      </SimpleGrid>
      {balances.length === 0 && (
        <Text c="dimmed">
          Todavía no hay cajas ni bancos: se crean en la pestaña Configuración.
        </Text>
      )}
      <Group justify="space-between">
        <Text fw={600}>Movimientos sin tercero</Text>
        {can('cash:write') && (
          <Button leftSection={<IconPlus size={16} />} onClick={() => setDrawer({ record: null })}>
            Nuevo movimiento
          </Button>
        )}
      </Group>
      <DataTable
        columns={columns}
        list={list}
        data={data}
        loading={isFetching}
        onRowClick={(record) => setDrawer({ record })}
        showSearch={false}
        showActiveFilter={false}
      />
      {/* Se vuelve a montar en cada apertura (formulario limpio) */}
      <Fragment key={drawer ? (drawer.record?.id ?? 'new') : 'closed'}>
        <MovementDrawer
          movement={drawer?.record ?? null}
          opened={drawer !== null}
          onClose={() => setDrawer(null)}
        />
      </Fragment>
      <StatementModal account={account} onClose={() => setAccount(null)} />
    </Stack>
  );
}
