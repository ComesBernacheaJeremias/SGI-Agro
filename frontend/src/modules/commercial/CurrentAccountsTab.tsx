import { Button, Group, Loader, Modal, SegmentedControl, Table, Text } from '@mantine/core';
import { useState } from 'react';

import { formatDate } from '@/shared/format/date';
import { formatMoney } from '@/shared/format/number';

import { type Balance, DIRECTION_TEXT, type Direction, useBalances, useLedger } from './api';

const money = (value: string | number) => (Number(value) ? formatMoney(value) : '');

type LedgerProps = {
  direction: Direction;
  party: Balance['party'] | null;
  onClose: () => void;
  onOpenRow: (kind: string, id: string) => void;
  onNewPayment: (partyId: string) => void;
  canWrite: boolean;
};

/** Resumen de cuenta de un cliente/proveedor: comprobantes y cobros/pagos con saldo acumulado. */
function LedgerModal({
  direction,
  party,
  onClose,
  onOpenRow,
  onNewPayment,
  canWrite,
}: LedgerProps) {
  const text = DIRECTION_TEXT[direction];
  const { data, isLoading } = useLedger(party?.id ?? null, direction);
  return (
    <Modal
      opened={party !== null}
      onClose={onClose}
      title={`Cuenta corriente · ${party?.name ?? ''}`}
      size="xl"
    >
      {isLoading && <Loader />}
      {data && (
        <>
          <Table.ScrollContainer minWidth={560}>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Fecha</Table.Th>
                  <Table.Th>Comprobante</Table.Th>
                  <Table.Th ta="right">Debe</Table.Th>
                  <Table.Th ta="right">Haber</Table.Th>
                  <Table.Th ta="right">Saldo</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.rows.map((r) => (
                  <Table.Tr
                    key={`${r.kind}-${r.id}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => onOpenRow(r.kind, r.id)}
                  >
                    <Table.Td>{formatDate(r.date)}</Table.Td>
                    <Table.Td>{r.label}</Table.Td>
                    <Table.Td ta="right">{money(r.debit)}</Table.Td>
                    <Table.Td ta="right">{money(r.credit)}</Table.Td>
                    <Table.Td ta="right">{formatMoney(r.balance)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {data.rows.length === 0 && <Text c="dimmed">Sin movimientos.</Text>}
          <Group justify="space-between" mt="md">
            <Text fw={700}>
              Saldo: {formatMoney(data.closing_balance)}{' '}
              <Text span size="sm" c="dimmed">
                {Number(data.closing_balance) >= 0
                  ? direction === 'sale'
                    ? '(nos debe)'
                    : '(le debemos)'
                  : '(a favor del ' + text.party.toLowerCase() + ')'}
              </Text>
            </Text>
            {canWrite && party && (
              <Button onClick={() => onNewPayment(party.id)}>
                Nuevo {text.payment.toLowerCase()}
              </Button>
            )}
          </Group>
        </>
      )}
    </Modal>
  );
}

type Props = {
  canWrite: boolean;
  onOpenDocument: (direction: Direction, id: string) => void;
  onOpenPayment: (direction: Direction, id: string | null, partyId?: string) => void;
};

/** Saldos de clientes o proveedores con antigüedad de la deuda vencida. */
export function CurrentAccountsTab({ canWrite, onOpenDocument, onOpenPayment }: Props) {
  const [direction, setDirection] = useState<Direction>('sale');
  const [party, setParty] = useState<Balance['party'] | null>(null);
  const { data = [], isLoading } = useBalances(direction);
  const total = (key: keyof Balance) => data.reduce((s, b) => s + Number(b[key]), 0);
  const columns: { key: keyof Balance; label: string }[] = [
    { key: 'balance', label: direction === 'sale' ? 'Nos debe' : 'Le debemos' },
    { key: 'overdue', label: 'Vencido' },
    { key: 'days_0_30', label: '1-30 días' },
    { key: 'days_31_60', label: '31-60' },
    { key: 'days_61_90', label: '61-90' },
    { key: 'days_over_90', label: '+90' },
    { key: 'advances', label: 'Anticipos' },
  ];
  return (
    <>
      <SegmentedControl
        mb="md"
        size="xs"
        value={direction}
        onChange={(v) => setDirection(v as Direction)}
        data={[
          { value: 'sale', label: 'Clientes' },
          { value: 'purchase', label: 'Proveedores' },
        ]}
      />
      {isLoading && <Loader />}
      {!isLoading && data.length === 0 && <Text c="dimmed">No hay saldos pendientes.</Text>}
      {data.length > 0 && (
        <Table.ScrollContainer minWidth={720}>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{DIRECTION_TEXT[direction].party}</Table.Th>
                {columns.map((c) => (
                  <Table.Th key={c.key} ta="right">
                    {c.label}
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.map((b) => (
                <Table.Tr
                  key={b.party.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setParty(b.party)}
                >
                  <Table.Td>{b.party.name}</Table.Td>
                  {columns.map((c) => (
                    <Table.Td
                      key={c.key}
                      ta="right"
                      c={c.key === 'overdue' && Number(b.overdue) > 0 ? 'red' : undefined}
                    >
                      {c.key === 'balance' ? formatMoney(b.balance) : money(b[c.key] as string)}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
            <Table.Tfoot>
              <Table.Tr>
                <Table.Th>Total</Table.Th>
                {columns.map((c) => (
                  <Table.Th key={c.key} ta="right">
                    {formatMoney(total(c.key))}
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Tfoot>
          </Table>
        </Table.ScrollContainer>
      )}
      <LedgerModal
        direction={direction}
        party={party}
        onClose={() => setParty(null)}
        canWrite={canWrite}
        onOpenRow={(kind, id) => {
          setParty(null);
          if (kind === 'document') onOpenDocument(direction, id);
          else onOpenPayment(direction, id);
        }}
        onNewPayment={(partyId) => {
          setParty(null);
          onOpenPayment(direction, null, partyId);
        }}
      />
    </>
  );
}
