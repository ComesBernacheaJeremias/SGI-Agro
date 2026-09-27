import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconBan, IconPlus, IconTrash } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { useEffect } from 'react';

import { useCan } from '@/app/auth/session';
import { partiesResource, useActiveList } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { formatDate } from '@/shared/format/date';
import { formatMoney } from '@/shared/format/number';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import {
  cashAccountsResource,
  DIRECTION_TEXT,
  type Direction,
  type Payment,
  paymentsApi,
  useCommercialOptions,
  useDocuments,
  useInvalidateCommercial,
  usePayment,
} from './api';

type MethodLine = {
  key: string;
  method: 'cash' | 'transfer';
  cash_account_id: string | null;
  amount: string | null;
  reference: string;
};

type Values = {
  party_id: string | null;
  date: string | null;
  notes: string;
  lines: MethodLine[];
  /** Imputado a cada comprobante (id → importe). */
  allocations: Record<string, string | null>;
};

const emptyMethod = (): MethodLine => ({
  key: crypto.randomUUID(),
  method: 'cash',
  cash_account_id: null,
  amount: null,
  reference: '',
});

const empty = (): Values => ({
  party_id: null,
  date: dayjs().format('YYYY-MM-DD'),
  notes: '',
  lines: [emptyMethod()],
  allocations: {},
});

const toValues = (p: Payment): Values => ({
  party_id: p.party.id,
  date: p.date,
  notes: p.notes,
  lines: p.lines.map((l) => ({
    key: crypto.randomUUID(),
    method: l.method,
    cash_account_id: l.cash_account.id,
    amount: l.amount,
    reference: l.reference,
  })),
  allocations: Object.fromEntries(p.allocations.map((a) => [a.document_id, a.amount])),
});

type Props = {
  direction: Direction;
  /** null = nuevo */
  paymentId: string | null;
  /** Para abrir un cobro/pago nuevo ya con el tercero elegido (desde cuentas corrientes). */
  partyId?: string | null;
  opened: boolean;
  onClose: () => void;
};

export function PaymentDrawer({ direction, paymentId, partyId, opened, onClose }: Props) {
  const can = useCan();
  const text = DIRECTION_TEXT[direction];
  const invalidate = useInvalidateCommercial();
  const { data: options } = useCommercialOptions();
  const { data: parties = [] } = useActiveList(partiesResource);
  const { data: accounts = [] } = useActiveList(cashAccountsResource);
  const { data: payment } = usePayment(opened ? paymentId : null);
  const isNew = paymentId === null;
  const readOnly = !can('commercial:write') || payment?.status === 'cancelled';

  const form = useForm<Values>({
    initialValues: empty(),
    validate: {
      party_id: (v) => (v ? null : 'Obligatorio'),
      date: (v) => (v ? null : 'Obligatorio'),
      lines: (lines) =>
        lines.length === 0 || lines.some((l) => !l.cash_account_id || !Number(l.amount))
          ? 'Completá cuenta e importe de cada medio'
          : null,
    },
  });

  useEffect(() => {
    if (!opened) return;
    if (isNew) {
      form.setValues({ ...empty(), party_id: partyId ?? null });
    } else if (payment) {
      form.setValues(toValues(payment));
    } else return;
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- al abrir o al llegar el registro
  }, [opened, isNew, payment]);

  const values = form.values;
  const { data: pendingDocs } = useDocuments(
    { direction, party_id: values.party_id, only_pending: true, page_size: 200 },
    opened && values.party_id !== null,
  );

  // Comprobantes imputables: los pendientes + los que ya imputa este cobro/pago
  const own = Object.fromEntries((payment?.allocations ?? []).map((a) => [a.document_id, a]));
  const rows = (pendingDocs?.items ?? [])
    .map((d) => ({
      id: d.id,
      label: d.invoice_label,
      due_date: d.due_date as string | null,
      available: Number(d.pending) + Number(own[d.id]?.amount ?? 0),
    }))
    .concat(
      (payment?.allocations ?? [])
        .filter((a) => !pendingDocs?.items.some((d) => d.id === a.document_id))
        .map((a) => ({
          id: a.document_id,
          label: a.invoice_label,
          due_date: null,
          available: Number(a.amount),
        })),
    )
    .sort((a, b) => (a.due_date ?? '').localeCompare(b.due_date ?? ''));

  const total = values.lines.reduce((s, l) => s + Number(l.amount ?? 0), 0);
  const allocated = Object.values(values.allocations).reduce((s, v) => s + Number(v ?? 0), 0);

  function autoAllocate() {
    let remaining = total;
    const next: Record<string, string | null> = {};
    for (const row of rows) {
      const amount = Math.min(row.available, Math.max(remaining, 0));
      next[row.id] = amount > 0 ? amount.toFixed(2) : null;
      remaining -= amount;
    }
    form.setFieldValue('allocations', next);
  }

  function updateLine(key: string, patch: Partial<MethodLine>) {
    form.setFieldValue(
      'lines',
      values.lines.map((l) => (l.key === key ? { ...l, ...patch } : l)),
    );
  }

  async function submit(v: Values) {
    const body = {
      direction,
      party_id: v.party_id as string,
      date: v.date as string,
      notes: v.notes,
      lines: v.lines.map((l) => ({
        method: l.method,
        cash_account_id: l.cash_account_id as string,
        amount: l.amount as string,
        reference: l.reference,
      })),
      allocations: Object.entries(v.allocations)
        .filter(([, amount]) => Number(amount) > 0)
        .map(([document_id, amount]) => ({ document_id, amount: amount as string })),
    };
    const saved = isNew
      ? await paymentsApi.create(body)
      : await paymentsApi.update(paymentId, body);
    notifySuccess(`${text.payment} ${saved.number} guardado.`);
    await invalidate();
  }

  async function cancelPayment() {
    if (!payment) return;
    const confirmed = await confirmAction({
      message: `Se va a anular el ${text.payment.toLowerCase()} ${payment.number}. Los comprobantes imputados vuelven a quedar pendientes.`,
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!confirmed) return;
    try {
      await paymentsApi.cancel(payment.id);
      notifySuccess(`${text.payment} ${payment.number} anulado.`);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  const partyOptions = parties
    .filter((p) => (direction === 'sale' ? p.is_customer : p.is_supplier))
    .map((p) => ({ value: p.id, label: p.name }));
  const canCancel =
    payment?.status === 'active' && can('commercial:cancel') && can('commercial:write');

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={
        isNew ? `Nuevo ${text.payment.toLowerCase()}` : `${text.payment} ${payment?.number ?? ''}`
      }
      form={form}
      isEdit={!isNew}
      onSubmit={submit}
      readOnly={readOnly}
      size="lg"
      extraActions={
        payment && (
          <>
            <HistoryButton table="payments" recordId={payment.id} />
            {canCancel && (
              <Button
                variant="subtle"
                color="red"
                leftSection={<IconBan size={16} />}
                onClick={cancelPayment}
              >
                Anular
              </Button>
            )}
          </>
        )
      }
    >
      {payment?.status === 'cancelled' && (
        <Group>
          <Badge color="red">Anulado</Badge>
        </Group>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Select
          label={text.party}
          required
          data={partyOptions}
          searchable
          disabled={readOnly || !isNew}
          {...form.getInputProps('party_id')}
          onChange={(v) => {
            form.setFieldValue('party_id', v);
            form.setFieldValue('allocations', {});
          }}
        />
        <DateInput label="Fecha" required disabled={readOnly} {...form.getInputProps('date')} />
      </SimpleGrid>

      <Stack gap="xs">
        <Text size="sm" fw={500}>
          Medios
        </Text>
        {values.lines.map((line) => (
          <Paper key={line.key} withBorder p="xs">
            <Group gap="xs" align="flex-end" wrap="wrap">
              <Select
                label="Medio"
                data={options?.payment_methods ?? []}
                value={line.method}
                onChange={(v) =>
                  updateLine(line.key, { method: (v ?? 'cash') as MethodLine['method'] })
                }
                allowDeselect={false}
                disabled={readOnly}
                w={140}
              />
              <Select
                label="Cuenta"
                data={accounts.map((a) => ({ value: a.id, label: a.name }))}
                value={line.cash_account_id}
                onChange={(cash_account_id) => updateLine(line.key, { cash_account_id })}
                disabled={readOnly}
                style={{ flex: '1 1 160px' }}
              />
              <NumberInput
                label="Importe"
                kind="price"
                leftSection="$"
                value={line.amount}
                onChange={(amount) => updateLine(line.key, { amount })}
                disabled={readOnly}
                w={150}
              />
              {line.method === 'transfer' && (
                <TextInput
                  label="Referencia"
                  value={line.reference}
                  onChange={(e) => updateLine(line.key, { reference: e.currentTarget.value })}
                  disabled={readOnly}
                  w={140}
                />
              )}
              {!readOnly && values.lines.length > 1 && (
                <ActionIcon
                  variant="subtle"
                  color="red"
                  mb={4}
                  aria-label="Quitar medio"
                  onClick={() =>
                    form.setFieldValue(
                      'lines',
                      values.lines.filter((l) => l.key !== line.key),
                    )
                  }
                >
                  <IconTrash size={16} />
                </ActionIcon>
              )}
            </Group>
          </Paper>
        ))}
        {form.errors.lines && (
          <Text size="xs" c="red">
            {form.errors.lines}
          </Text>
        )}
        {!readOnly && (
          <Group>
            <Button
              variant="light"
              size="xs"
              leftSection={<IconPlus size={14} />}
              onClick={() => form.setFieldValue('lines', [...values.lines, emptyMethod()])}
            >
              Agregar medio
            </Button>
          </Group>
        )}
      </Stack>

      {values.party_id && (
        <Stack gap="xs">
          <Group justify="space-between">
            <Text size="sm" fw={500}>
              Imputar a comprobantes
            </Text>
            {!readOnly && rows.length > 0 && (
              <Button variant="subtle" size="xs" onClick={autoAllocate}>
                Imputar a los más viejos
              </Button>
            )}
          </Group>
          {rows.length === 0 ? (
            <Text size="sm" c="dimmed">
              No hay comprobantes pendientes: todo queda como anticipo.
            </Text>
          ) : (
            <Table verticalSpacing={4}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Comprobante</Table.Th>
                  <Table.Th>Vence</Table.Th>
                  <Table.Th ta="right">Pendiente</Table.Th>
                  <Table.Th ta="right">Imputar</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((row) => (
                  <Table.Tr key={row.id}>
                    <Table.Td>{row.label}</Table.Td>
                    <Table.Td>{row.due_date ? formatDate(row.due_date) : ''}</Table.Td>
                    <Table.Td ta="right">{formatMoney(row.available)}</Table.Td>
                    <Table.Td>
                      <NumberInput
                        kind="price"
                        size="xs"
                        value={values.allocations[row.id] ?? null}
                        onChange={(amount) =>
                          form.setFieldValue('allocations', {
                            ...values.allocations,
                            [row.id]: amount,
                          })
                        }
                        disabled={readOnly}
                        w={130}
                        ml="auto"
                      />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Stack>
      )}

      <Paper withBorder p="sm">
        <Group justify="space-between">
          <Text size="sm">Total</Text>
          <Text fw={700}>{formatMoney(total)}</Text>
        </Group>
        <Group justify="space-between">
          <Text size="sm">Imputado</Text>
          <Text size="sm">{formatMoney(allocated)}</Text>
        </Group>
        <Group justify="space-between">
          <Text size="sm">{allocated > total ? 'Imputado de más' : 'Queda como anticipo'}</Text>
          <Text size="sm" c={allocated > total ? 'red' : undefined}>
            {formatMoney(Math.abs(total - allocated))}
          </Text>
        </Group>
      </Paper>
      <Textarea
        label="Observaciones"
        autosize
        disabled={readOnly}
        {...form.getInputProps('notes')}
      />
    </EntityDrawer>
  );
}
