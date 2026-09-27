import { Badge, Select } from '@mantine/core';
import { useState } from 'react';

import { labelOf, useActiveList, warehousesResource } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { type Column, DataTable } from '@/shared/crud/DataTable';
import { useListState } from '@/shared/crud/hooks';
import { formatDate } from '@/shared/format/date';

import { type DocumentSummary, type DocumentType, useDocuments, useInventoryOptions } from './api';

type Props = { onOpen: (id: string, type: DocumentType) => void };

export function DocumentsTab({ onOpen }: Props) {
  const list = useListState();
  const { data: options } = useInventoryOptions();
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const [type, setType] = useState<DocumentType | null>(null);
  const [status, setStatus] = useState<'active' | 'cancelled' | null>(null);
  const [warehouseId, setWarehouseId] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);

  const { data, isFetching } = useDocuments({
    q: list.params.q,
    page: list.page,
    page_size: 50,
    type: type ?? undefined,
    status: status ?? undefined,
    warehouse_id: warehouseId ?? undefined,
    date_from: dateFrom ?? undefined,
    date_to: dateTo ?? undefined,
  });
  const reset =
    <V,>(setter: (v: V) => void) =>
    (v: V) => {
      setter(v);
      list.setPage(1);
    };

  const columns: Column<DocumentSummary>[] = [
    { key: 'date', header: 'Fecha', render: (d) => formatDate(d.date) },
    { key: 'number', header: 'Número' },
    { key: 'type', header: 'Tipo', render: (d) => labelOf(options?.document_types, d.type) },
    {
      key: 'warehouse',
      header: 'Almacén',
      render: (d) =>
        d.target_warehouse ? `${d.warehouse.name} → ${d.target_warehouse.name}` : d.warehouse.name,
    },
    { key: 'reference', header: 'Referencia', hideOnMobile: true },
    { key: 'line_count', header: 'Líneas', align: 'right', hideOnMobile: true },
    {
      key: 'status',
      header: 'Estado',
      render: (d) =>
        d.status === 'cancelled' ? (
          <Badge color="red" variant="light">
            Anulado
          </Badge>
        ) : null,
    },
  ];

  return (
    <DataTable
      columns={columns}
      list={list}
      data={data}
      loading={isFetching}
      onRowClick={(d) => onOpen(d.id, d.type)}
      searchPlaceholder="Número o referencia…"
      showActiveFilter={false}
      filters={
        <>
          <Select
            placeholder="Tipo"
            data={options?.document_types ?? []}
            value={type}
            onChange={(v) => reset(setType)(v as DocumentType | null)}
            clearable
            w={150}
          />
          <Select
            placeholder="Almacén"
            data={warehouses.map((w) => ({ value: w.id, label: w.name }))}
            value={warehouseId}
            onChange={reset(setWarehouseId)}
            clearable
            w={170}
          />
          <Select
            placeholder="Estado"
            data={options?.statuses ?? []}
            value={status}
            onChange={(v) => reset(setStatus)(v as 'active' | 'cancelled' | null)}
            clearable
            w={130}
          />
          <DateInput placeholder="Desde" value={dateFrom} onChange={reset(setDateFrom)} w={140} />
          <DateInput placeholder="Hasta" value={dateTo} onChange={reset(setDateTo)} w={140} />
        </>
      }
    />
  );
}
