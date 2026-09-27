import { Badge, Select, SimpleGrid, Textarea, TextInput } from '@mantine/core';

import { useCan } from '@/app/auth/session';
import { NumberInput } from '@/shared/components/NumberInput';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatNumber } from '@/shared/format/number';
import { useState } from 'react';

import {
  categoriesResource,
  labelOf,
  type Product,
  productsResource,
  unitsResource,
  useActiveList,
  useMasterdataOptions,
} from './api';
import { ConversionsField, type ConversionValue } from './ConversionsField';

type Values = {
  code: string;
  name: string;
  type: Product['type'];
  category_id: string | null;
  unit_id: string;
  vat_rate: string;
  min_stock: string | null;
  notes: string;
  conversions: ConversionValue[];
};

const EMPTY: Values = {
  code: '',
  name: '',
  type: 'input',
  category_id: null,
  unit_id: '',
  vat_rate: '21',
  min_stock: null,
  notes: '',
  conversions: [],
};

function ProductDrawer({ record, opened, onClose }: DrawerProps<Product>) {
  const can = useCan();
  const canWrite = can('masterdata:write');
  const { data: options } = useMasterdataOptions();
  const { data: units = [] } = useActiveList(unitsResource);
  const { data: categories = [] } = useActiveList(categoriesResource);
  const { create, update } = useResourceMutations(productsResource);

  const form = useDrawerForm<Product, Values>({
    opened,
    record,
    empty: EMPTY,
    toValues: (p) => ({
      code: p.code,
      name: p.name,
      type: p.type,
      category_id: p.category?.id ?? null,
      unit_id: p.unit.id,
      vat_rate: String(Number(p.vat_rate)),
      min_stock: p.min_stock,
      notes: p.notes,
      conversions: p.conversions.map((c) => ({ unit_id: c.unit.id, quantity: c.quantity })),
    }),
    validate: { name: required, type: required, unit_id: required },
  });

  async function submit(values: Values) {
    const body = {
      ...values,
      code: values.code.trim() || null,
      conversions: values.conversions
        .filter((c) => c.unit_id && c.quantity)
        .map((c) => ({ unit_id: c.unit_id, quantity: c.quantity as string })),
    };
    if (record)
      await update.mutateAsync({ id: record.id, body: { ...body, code: body.code ?? undefined } });
    else await create.mutateAsync(body);
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? `Producto ${record.code}` : 'Nuevo producto'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={productsResource}
            record={record}
            name={record.name}
            canDeactivate={can('masterdata:deactivate')}
            onClose={onClose}
          />
        )
      }
    >
      <SimpleGrid cols={2}>
        <Select
          label="Tipo"
          required
          data={options?.product_types ?? []}
          disabled={!canWrite}
          {...form.getInputProps('type')}
        />
        <TextInput
          label="Código"
          placeholder="Automático"
          disabled={!canWrite}
          {...form.getInputProps('code')}
        />
      </SimpleGrid>
      <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
      <Select
        label="Categoría"
        data={categories.map((c) => ({ value: c.id, label: c.path }))}
        searchable
        clearable
        disabled={!canWrite}
        {...form.getInputProps('category_id')}
      />
      <SimpleGrid cols={2}>
        <Select
          label="Unidad base"
          required
          data={units.map((u) => ({ value: u.id, label: `${u.code} (${u.name})` }))}
          searchable
          disabled={!canWrite}
          {...form.getInputProps('unit_id')}
        />
        <Select
          label="IVA"
          data={(options?.vat_rates ?? []).map((r) => ({
            value: String(Number(r)),
            label: `${formatNumber(r, 'quantity').replace(/,00$/, '')} %`,
          }))}
          disabled={!canWrite}
          {...form.getInputProps('vat_rate')}
        />
      </SimpleGrid>
      <NumberInput
        label="Stock mínimo"
        description="Aviso cuando el stock baje de este valor"
        kind="quantity"
        disabled={!canWrite}
        {...form.getInputProps('min_stock')}
      />
      <ConversionsField
        value={form.values.conversions}
        onChange={(value) => form.setFieldValue('conversions', value)}
        units={units}
        baseUnitId={form.values.unit_id}
        disabled={!canWrite}
      />
      <Textarea
        label="Observaciones"
        autosize
        disabled={!canWrite}
        {...form.getInputProps('notes')}
      />
    </EntityDrawer>
  );
}

export function ProductsTab() {
  const can = useCan();
  const { data: options } = useMasterdataOptions();
  const { data: categories = [] } = useActiveList(categoriesResource);
  const [type, setType] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState<string | null>(null);

  const columns: Column<Product>[] = [
    { key: 'code', header: 'Código', sortable: true },
    { key: 'name', header: 'Nombre', sortable: true },
    { key: 'type', header: 'Tipo', render: (p) => labelOf(options?.product_types, p.type) },
    {
      key: 'category',
      header: 'Categoría',
      hideOnMobile: true,
      render: (p) => p.category?.name ?? '—',
    },
    { key: 'unit', header: 'Unidad', render: (p) => p.unit.code },
    {
      key: 'is_active',
      header: 'Estado',
      hideOnMobile: true,
      render: (p) =>
        !p.is_active && (
          <Badge color="gray" variant="light">
            Inactivo
          </Badge>
        ),
    },
  ];

  return (
    <CrudTab
      resource={productsResource}
      columns={columns}
      newLabel="Nuevo producto"
      canCreate={can('masterdata:write')}
      defaultSort="name"
      searchPlaceholder="Buscar por código o nombre…"
      extraParams={{ type: type ?? undefined, category_id: categoryId ?? undefined }}
      filters={(list) => (
        <>
          <Select
            placeholder="Tipo"
            data={options?.product_types ?? []}
            value={type}
            onChange={(v) => {
              setType(v);
              list.setPage(1);
            }}
            clearable
            w={180}
          />
          <Select
            placeholder="Categoría"
            data={categories.map((c) => ({ value: c.id, label: c.path }))}
            value={categoryId}
            onChange={(v) => {
              setCategoryId(v);
              list.setPage(1);
            }}
            searchable
            clearable
            w={220}
          />
        </>
      )}
      renderDrawer={(props) => <ProductDrawer {...props} />}
    />
  );
}
