import { Badge, SegmentedControl } from '@mantine/core';
import dayjs from 'dayjs';
import { useState } from 'react';

import { labelOf } from '@/modules/masterdata/api';
import { type Column, DataTable } from '@/shared/crud/DataTable';
import { useListState } from '@/shared/crud/hooks';
import { formatDate } from '@/shared/format/date';
import { formatMoney } from '@/shared/format/number';

import {
  type Direction,
  type DocumentSummary,
  type Payment,
  useCommercialOptions,
  useDocuments,
  usePayments,
} from './api';

const today = () => dayjs().format('YYYY-MM-DD');

/** Estado de pago de un comprobante (anulado · pendiente/vencido · saldado). */
function StatusBadge({ doc }: { doc: DocumentSummary }) {
  if (doc.status === 'cancelled')
    return (
      <Badge color="red" variant="light">
        Anulada
      </Badge>
    );
  if (doc.kind === 'credit_note') return null;
  if (Number(doc.pending) <= 0)
    return (
      <Badge color="green" variant="light">
        Saldada
      </Badge>
    );
  const overdue = doc.due_date < today();
  return (
    <Badge color={overdue ? 'red' : 'orange'} variant="light">
      {overdue ? 'Vencida' : 'Pendiente'}
    </Badge>
  );
}

type DocumentsProps = { direction: Direction; onOpen: (doc: DocumentSummary) => void };

/** Listado de compras o ventas. */
export function DocumentsTab({ direction, onOpen }: DocumentsProps) {
  const list = useListState();
  const [onlyPending, setOnlyPending] = useState('all');
  const { data: options } = useCommercialOptions();
  const { data, isFetching } = useDocuments({
    direction,
    q: list.params.q,
    only_pending: onlyPending === 'pending',
    page: list.page,
    page_size: 50,
  });
  const columns: Column<DocumentSummary>[] = [
    { key: 'date', header: 'Fecha', render: (d) => formatDate(d.date) },
    {
      key: 'invoice_label',
      header: 'Comprobante',
      render: (d) =>
        d.has_invoice
          ? d.invoice_label
          : `${labelOf(options?.document_kinds, d.kind)} ${d.internal_number}`,
    },
    {
      key: 'party',
      header: direction === 'sale' ? 'Cliente' : 'Proveedor',
      render: (d) => d.party.name,
    },
    {
      key: 'due_date',
      header: 'Vence',
      hideOnMobile: true,
      render: (d) => formatDate(d.due_date),
    },
    {
      key: 'total',
      header: 'Total',
      align: 'right',
      render: (d) => formatMoney(d.kind === 'credit_note' ? -Number(d.total) : d.total),
    },
    {
      key: 'pending',
      header: 'Pendiente',
      align: 'right',
      hideOnMobile: true,
      render: (d) => (Number(d.pending) > 0 ? formatMoney(d.pending) : ''),
    },
    { key: 'status', header: '', render: (d) => <StatusBadge doc={d} /> },
  ];
  return (
    <DataTable
      columns={columns}
      list={list}
      data={data}
      loading={isFetching}
      onRowClick={onOpen}
      searchPlaceholder="Buscar por número o nombre…"
      showActiveFilter={false}
      filters={
        <SegmentedControl
          size="xs"
          value={onlyPending}
          onChange={(v) => {
            setOnlyPending(v);
            list.setPage(1);
          }}
          data={[
            { value: 'all', label: 'Todas' },
            { value: 'pending', label: direction === 'sale' ? 'A cobrar' : 'A pagar' },
          ]}
        />
      }
    />
  );
}

type PaymentsProps = { direction: Direction; onOpen: (payment: Payment) => void };

/** Listado de cobros o pagos. */
export function PaymentsTab({ direction, onOpen }: PaymentsProps) {
  const list = useListState();
  const { data, isFetching } = usePayments({ direction, page: list.page, page_size: 50 });
  const columns: Column<Payment>[] = [
    { key: 'date', header: 'Fecha', render: (p) => formatDate(p.date) },
    { key: 'number', header: 'Número' },
    {
      key: 'party',
      header: direction === 'sale' ? 'Cliente' : 'Proveedor',
      render: (p) => p.party.name,
    },
    {
      key: 'methods',
      header: 'Medios',
      hideOnMobile: true,
      render: (p) => p.lines.map((l) => l.cash_account.name).join(', '),
    },
    { key: 'total', header: 'Total', align: 'right', render: (p) => formatMoney(p.total) },
    {
      key: 'unallocated',
      header: 'Anticipo',
      align: 'right',
      hideOnMobile: true,
      render: (p) => (Number(p.unallocated) > 0 ? formatMoney(p.unallocated) : ''),
    },
    {
      key: 'status',
      header: '',
      render: (p) =>
        p.status === 'cancelled' && (
          <Badge color="red" variant="light">
            Anulado
          </Badge>
        ),
    },
  ];
  return (
    <DataTable
      columns={columns}
      list={list}
      data={data}
      loading={isFetching}
      onRowClick={onOpen}
      showSearch={false}
      showActiveFilter={false}
    />
  );
}
