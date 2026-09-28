import { Badge, Select } from '@mantine/core';
import { useState } from 'react';

import { useActiveList } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { type Column, DataTable } from '@/shared/crud/DataTable';
import { useListState } from '@/shared/crud/hooks';
import { formatDate } from '@/shared/format/date';
import { formatMoney } from '@/shared/format/number';

import {
  type OperationSummary,
  operationTypesResource,
  useActiveCycles,
  useOperations,
} from './api';

type Props = { onOpen: (operation: OperationSummary) => void };

export function OperationsTab({ onOpen }: Props) {
  const list = useListState();
  const { data: types = [] } = useActiveList(operationTypesResource);
  const { data: cycles } = useActiveCycles();
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [typeId, setTypeId] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);
  const { data, isFetching } = useOperations({
    page: list.page,
    page_size: 50,
    crop_cycle_id: cycleId ?? undefined,
    operation_type_id: typeId ?? undefined,
    date_from: dateFrom ?? undefined,
    date_to: dateTo ?? undefined,
  });
  const reset =
    <V,>(setter: (v: V) => void) =>
    (v: V) => {
      setter(v);
      list.setPage(1);
    };

  const columns: Column<OperationSummary>[] = [
    { key: 'date', header: 'Fecha', nowrap: true, render: (o) => formatDate(o.date) },
    { key: 'number', header: 'Número', nowrap: true, hideOnMobile: true },
    { key: 'operation_type', header: 'Labor', render: (o) => o.operation_type.name },
    { key: 'cycles', header: 'Ciclos', render: (o) => o.cycles.join(' / ') },
    {
      key: 'total_cost',
      header: 'Costo',
      align: 'right',
      render: (o) => formatMoney(o.total_cost),
    },
    {
      key: 'status',
      header: '',
      render: (o) =>
        o.status === 'cancelled' && (
          <Badge color="red" variant="light">
            Anulada
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
      filters={
        <>
          <Select
            placeholder="Ciclo"
            data={(cycles?.items ?? []).map((c) => ({ value: c.id, label: c.name }))}
            value={cycleId}
            onChange={reset(setCycleId)}
            searchable
            clearable
            w={260}
          />
          <Select
            placeholder="Tipo de labor"
            data={types.map((t) => ({ value: t.id, label: t.name }))}
            value={typeId}
            onChange={reset(setTypeId)}
            clearable
            w={170}
          />
          <DateInput placeholder="Desde" value={dateFrom} onChange={reset(setDateFrom)} w={140} />
          <DateInput placeholder="Hasta" value={dateTo} onChange={reset(setDateTo)} w={140} />
        </>
      }
    />
  );
}
