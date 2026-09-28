import { Checkbox, Group, Select, SimpleGrid, Tabs, Textarea, TextInput } from '@mantine/core';
import { useEffect, useState } from 'react';

import { FormError } from '@/api/errors';
import { useCan } from '@/app/auth/session';
import { labelOf, type Product, productsResource } from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { NumberInput } from '@/shared/components/NumberInput';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useActiveList } from '@/modules/masterdata/api';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatNumber } from '@/shared/format/number';

import {
  type Crop,
  cropsResource,
  type Farm,
  farmsResource,
  type OperationType,
  operationTypesResource,
  type Plot,
  plotsResource,
  useProductionOptions,
} from './api';

/** Acciones comunes del pie del panel (historial + desactivar con permiso de configuración). */
function useConfigPermissions() {
  const can = useCan();
  return { canWrite: can('production:config') };
}

// --- Establecimientos ---

type FarmValues = { name: string; location: string; area_ha: string | null; notes: string };

function FarmDrawer({ record, opened, onClose }: DrawerProps<Farm>) {
  const { canWrite } = useConfigPermissions();
  const { create, update } = useResourceMutations(farmsResource);
  const form = useDrawerForm<Farm, FarmValues>({
    opened,
    record,
    empty: { name: '', location: '', area_ha: null, notes: '' },
    toValues: ({ name, location, area_ha, notes }) => ({ name, location, area_ha, notes }),
    validate: { name: required },
  });
  async function submit(values: FarmValues) {
    if (record) await update.mutateAsync({ id: record.id, body: values });
    else await create.mutateAsync(values);
  }
  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nuevo establecimiento'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={farmsResource}
            record={record}
            name={record.name}
            canDeactivate={canWrite}
            onClose={onClose}
          />
        )
      }
    >
      <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
      <TextInput label="Ubicación" disabled={!canWrite} {...form.getInputProps('location')} />
      <NumberInput
        label="Superficie (ha)"
        kind="quantity"
        disabled={!canWrite}
        {...form.getInputProps('area_ha')}
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

// --- Lotes ---

type PlotValues = {
  farm_id: string | null;
  name: string;
  area_ha: string | null;
  kind: Plot['kind'];
  notes: string;
};

function PlotDrawer({ record, opened, onClose }: DrawerProps<Plot>) {
  const { canWrite } = useConfigPermissions();
  const { data: options } = useProductionOptions();
  const { data: farms = [] } = useActiveList(farmsResource);
  const { create, update } = useResourceMutations(plotsResource);
  const form = useDrawerForm<Plot, PlotValues>({
    opened,
    record,
    empty: { farm_id: null, name: '', area_ha: null, kind: 'open_field', notes: '' },
    toValues: (p) => ({
      farm_id: p.farm.id,
      name: p.name,
      area_ha: p.area_ha,
      kind: p.kind,
      notes: p.notes,
    }),
    validate: { farm_id: required, name: required, area_ha: required },
  });
  async function submit({ farm_id, ...values }: PlotValues) {
    const body = { ...values, area_ha: values.area_ha as string };
    if (record) await update.mutateAsync({ id: record.id, body });
    else await create.mutateAsync({ ...body, farm_id: farm_id as string });
  }
  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? `${record.farm.name} · ${record.name}` : 'Nuevo lote'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={plotsResource}
            record={record}
            name={record.name}
            canDeactivate={canWrite}
            onClose={onClose}
          />
        )
      }
    >
      <Select
        label="Establecimiento"
        required
        data={farms.map((f) => ({ value: f.id, label: f.name }))}
        disabled={!canWrite || record !== null}
        {...form.getInputProps('farm_id')}
      />
      <SimpleGrid cols={2}>
        <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
        <NumberInput
          label="Superficie (ha)"
          required
          kind="quantity"
          disabled={!canWrite}
          {...form.getInputProps('area_ha')}
        />
      </SimpleGrid>
      <Select
        label="Tipo"
        data={options?.plot_kinds ?? []}
        disabled={!canWrite}
        {...form.getInputProps('kind')}
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

// --- Cultivos ---

type CropValues = { species: string; variety: string; kind: Crop['kind'] };

function CropDrawer({ record, opened, onClose }: DrawerProps<Crop>) {
  const { canWrite } = useConfigPermissions();
  const { data: options } = useProductionOptions();
  const { create, update } = useResourceMutations(cropsResource);
  const [product, setProduct] = useState<Product | null>(null);
  const form = useDrawerForm<Crop, CropValues>({
    opened,
    record,
    empty: { species: '', variety: '', kind: 'vegetable' },
    toValues: ({ species, variety, kind }) => ({ species, variety, kind }),
    validate: { species: required },
  });
  useEffect(() => {
    if (opened && record) void productsResource.get(record.harvest_product.id).then(setProduct);
  }, [opened, record]);

  async function submit(values: CropValues) {
    if (!product) throw new FormError('Elegí el producto que se cosecha.');
    const body = { ...values, harvest_product_id: product.id };
    if (record) await update.mutateAsync({ id: record.id, body });
    else await create.mutateAsync(body);
  }
  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nuevo tipo de cultivo'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={cropsResource}
            record={record}
            name={record.name}
            canDeactivate={canWrite}
            onClose={onClose}
          />
        )
      }
    >
      <SimpleGrid cols={2}>
        <TextInput
          label="Especie"
          placeholder="Tomate"
          required
          disabled={!canWrite}
          {...form.getInputProps('species')}
        />
        <TextInput
          label="Variedad"
          placeholder="Perita"
          disabled={!canWrite}
          {...form.getInputProps('variety')}
        />
      </SimpleGrid>
      <Select
        label="Tipo"
        data={options?.crop_kinds ?? []}
        disabled={!canWrite}
        {...form.getInputProps('kind')}
      />
      <ProductSelect
        label="Producto que se cosecha"
        description="De tipo 'Producción propia' (se crea en Maestros → Productos)"
        required
        types={['own_produce']}
        value={product}
        onChange={setProduct}
        disabled={!canWrite}
      />
    </EntityDrawer>
  );
}

// --- Tipos de labor ---

type TypeValues = { name: string; uses_inputs: boolean; uses_assets: boolean; is_harvest: boolean };

function OperationTypeDrawer({ record, opened, onClose }: DrawerProps<OperationType>) {
  const { canWrite } = useConfigPermissions();
  const { create, update } = useResourceMutations(operationTypesResource);
  const form = useDrawerForm<OperationType, TypeValues>({
    opened,
    record,
    empty: { name: '', uses_inputs: false, uses_assets: true, is_harvest: false },
    toValues: ({ name, uses_inputs, uses_assets, is_harvest }) => ({
      name,
      uses_inputs,
      uses_assets,
      is_harvest,
    }),
    validate: { name: required },
  });
  async function submit(values: TypeValues) {
    if (record) await update.mutateAsync({ id: record.id, body: values });
    else await create.mutateAsync(values);
  }
  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nuevo tipo de labor'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={operationTypesResource}
            record={record}
            name={record.name}
            canDeactivate={canWrite}
            onClose={onClose}
          />
        )
      }
    >
      <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
      <Group>
        <Checkbox
          label="Lleva insumos"
          disabled={!canWrite}
          {...form.getInputProps('uses_inputs', { type: 'checkbox' })}
        />
        <Checkbox
          label="Lleva maquinaria"
          disabled={!canWrite}
          {...form.getInputProps('uses_assets', { type: 'checkbox' })}
        />
        <Checkbox
          label="Es cosecha"
          disabled={!canWrite}
          {...form.getInputProps('is_harvest', { type: 'checkbox' })}
        />
      </Group>
    </EntityDrawer>
  );
}

// --- Pestaña ---

const yesNo = (value: boolean) => (value ? 'Sí' : '');

export function ConfigTab() {
  const { canWrite } = useConfigPermissions();
  const { data: options } = useProductionOptions();

  const farmColumns: Column<Farm>[] = [
    { key: 'name', header: 'Nombre', sortable: true },
    { key: 'location', header: 'Ubicación', hideOnMobile: true },
    {
      key: 'area_ha',
      header: 'Superficie',
      align: 'right',
      render: (f) => (f.area_ha ? `${formatNumber(f.area_ha, 'quantity')} ha` : ''),
    },
  ];
  const plotColumns: Column<Plot>[] = [
    { key: 'farm', header: 'Establecimiento', render: (p) => p.farm.name },
    { key: 'name', header: 'Lote', sortable: true },
    { key: 'kind', header: 'Tipo', render: (p) => labelOf(options?.plot_kinds, p.kind) },
    {
      key: 'area_ha',
      header: 'Superficie',
      align: 'right',
      render: (p) => `${formatNumber(p.area_ha, 'quantity')} ha`,
    },
  ];
  const cropColumns: Column<Crop>[] = [
    { key: 'name', header: 'Tipo de cultivo', sortable: true },
    { key: 'kind', header: 'Tipo', render: (c) => labelOf(options?.crop_kinds, c.kind) },
    {
      key: 'harvest_product',
      header: 'Producto cosechado',
      hideOnMobile: true,
      render: (c) => c.harvest_product.name,
    },
  ];
  const typeColumns: Column<OperationType>[] = [
    { key: 'name', header: 'Tipo de labor', sortable: true },
    { key: 'uses_inputs', header: 'Insumos', render: (t) => yesNo(t.uses_inputs) },
    { key: 'uses_assets', header: 'Maquinaria', render: (t) => yesNo(t.uses_assets) },
    { key: 'is_harvest', header: 'Cosecha', render: (t) => yesNo(t.is_harvest) },
  ];

  return (
    <Tabs defaultValue="plots" keepMounted={false} variant="pills">
      <Tabs.List mb="md">
        <Tabs.Tab value="plots">Lotes</Tabs.Tab>
        <Tabs.Tab value="farms">Establecimientos</Tabs.Tab>
        <Tabs.Tab value="crops">Tipos de cultivo</Tabs.Tab>
        <Tabs.Tab value="types">Tipos de labor</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="plots">
        <CrudTab
          resource={plotsResource}
          columns={plotColumns}
          newLabel="Nuevo lote"
          canCreate={canWrite}
          defaultSort="name"
          renderDrawer={(p) => <PlotDrawer {...p} />}
        />
      </Tabs.Panel>
      <Tabs.Panel value="farms">
        <CrudTab
          resource={farmsResource}
          columns={farmColumns}
          newLabel="Nuevo establecimiento"
          canCreate={canWrite}
          defaultSort="name"
          renderDrawer={(p) => <FarmDrawer {...p} />}
        />
      </Tabs.Panel>
      <Tabs.Panel value="crops">
        <CrudTab
          resource={cropsResource}
          columns={cropColumns}
          newLabel="Nuevo tipo de cultivo"
          canCreate={canWrite}
          defaultSort="name"
          renderDrawer={(p) => <CropDrawer {...p} />}
        />
      </Tabs.Panel>
      <Tabs.Panel value="types">
        <CrudTab
          resource={operationTypesResource}
          columns={typeColumns}
          newLabel="Nuevo tipo de labor"
          canCreate={canWrite}
          defaultSort="name"
          renderDrawer={(p) => <OperationTypeDrawer {...p} />}
        />
      </Tabs.Panel>
    </Tabs>
  );
}
