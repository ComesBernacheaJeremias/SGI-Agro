import { Group, SegmentedControl, Select, Stack, Text } from '@mantine/core';
import { useState } from 'react';

import { type Product, useActiveList, useMasterdataOptions } from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { plotsResource, useSeasons } from '@/modules/production/api';
import { DateInput } from '@/shared/components/DateInput';

import type { ReportFilter, ReportParams } from './api';
import { FILTER_RESOURCES, type FilterResource } from './filters';

type Props = {
  filters: ReportFilter[];
  values: ReportParams;
  onChange: (patch: ReportParams) => void;
};

/** Desplegable con los registros activos de un recurso. */
function ResourceSelect({
  resource,
  label,
  value,
  onChange,
  filter,
}: {
  resource: FilterResource;
  label: string;
  value: string | null;
  onChange: (value: string | null) => void;
  filter?: (item: never) => boolean;
}) {
  const { data = [] } = useActiveList(resource);
  const items = filter ? data.filter(filter as (i: unknown) => boolean) : data;
  return (
    <Select
      label={label}
      placeholder="Todos"
      data={items.map((i) => ({ value: i.id, label: i.name }))}
      value={value}
      onChange={onChange}
      searchable
      clearable
      w={200}
    />
  );
}

/** Filtros de un reporte, armados según su definición en el backend. */
export function ReportFilters({ filters, values, onChange }: Props) {
  const { data: seasons = [] } = useSeasons();
  const { data: options } = useMasterdataOptions();
  const [product, setProduct] = useState<Product | null>(null);
  const seasonOptions = seasons.map((s) => ({ value: s.id, label: s.name }));

  return (
    <Group align="flex-end" gap="sm" wrap="wrap" mb="md">
      {filters.map((f) => {
        const key = `${f.kind}-${f.name ?? ''}`;
        switch (f.kind) {
          case 'period':
            return (
              <Group key={key} gap="xs" align="flex-end">
                <Select
                  label="Temporada"
                  placeholder="Elegir fechas"
                  data={seasonOptions}
                  value={values.season_id ?? null}
                  onChange={(season_id) => onChange({ season_id, date_from: null, date_to: null })}
                  clearable
                  w={140}
                />
                <DateInput
                  label="Desde"
                  value={values.date_from ?? null}
                  onChange={(date_from) => onChange({ date_from, season_id: null })}
                  w={140}
                />
                <DateInput
                  label="Hasta"
                  value={values.date_to ?? null}
                  onChange={(date_to) => onChange({ date_to, season_id: null })}
                  w={140}
                />
              </Group>
            );
          case 'date':
            return (
              <DateInput
                key={key}
                label={f.label}
                placeholder="Hoy"
                value={values.date_to ?? null}
                onChange={(date_to) => onChange({ date_to })}
                w={150}
              />
            );
          case 'season':
            return (
              <Select
                key={key}
                label={f.label}
                placeholder="Todas"
                data={seasonOptions}
                value={values.season_id ?? null}
                onChange={(season_id) => onChange({ season_id })}
                clearable
                w={140}
              />
            );
          case 'plot':
            return (
              <ResourceSelect
                key={key}
                resource={plotsResource}
                label={f.label}
                value={values.plot_id ?? null}
                onChange={(plot_id) => onChange({ plot_id })}
                filter={
                  values.farm_id
                    ? (((p: { farm: { id: string } }) => p.farm.id === values.farm_id) as never)
                    : undefined
                }
              />
            );
          case 'product':
            return (
              <ProductSelect
                key={key}
                label={f.label}
                placeholder="Todos"
                value={product}
                onChange={(p) => {
                  setProduct(p);
                  onChange({ product_id: p?.id ?? null });
                }}
                clearable
                w={220}
              />
            );
          case 'product_type':
            return (
              <Select
                key={key}
                label={f.label}
                placeholder="Todos"
                data={options?.product_types ?? []}
                value={values.product_type ?? null}
                onChange={(product_type) => onChange({ product_type })}
                clearable
                w={180}
              />
            );
          case 'choice': {
            const name = f.name as string;
            const value = values[name] ?? f.default ?? null;
            return (f.options ?? []).length <= 4 ? (
              <Stack key={key} gap={4}>
                <Text size="sm" fw={500}>
                  {f.label}
                </Text>
                <SegmentedControl
                  size="xs"
                  data={f.options ?? []}
                  value={value ?? undefined}
                  onChange={(v) => onChange({ [name]: v })}
                />
              </Stack>
            ) : (
              <Select
                key={key}
                label={f.label}
                data={f.options ?? []}
                value={value}
                onChange={(v) => onChange({ [name]: v })}
                allowDeselect={false}
                w={190}
              />
            );
          }
          default: {
            const spec = FILTER_RESOURCES[f.kind];
            if (!spec) return null;
            return (
              <ResourceSelect
                key={key}
                resource={spec.resource}
                label={f.required ? `${f.label} *` : f.label}
                value={values[spec.param] ?? null}
                onChange={(v) => onChange({ [spec.param]: v })}
              />
            );
          }
        }
      })}
    </Group>
  );
}
