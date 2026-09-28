import { Badge, Select, SimpleGrid, Textarea, TextInput } from '@mantine/core';
import { useState } from 'react';

import { useCan } from '@/app/auth/session';
import { labelOf } from '@/modules/masterdata/api';
import { NumberInput } from '@/shared/components/NumberInput';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatMoney } from '@/shared/format/number';
import { PageHeader } from '@/shared/ui/PageHeader';

import {
  type Asset,
  assetsResource,
  meterRate,
  PLAN_STATE,
  useAssetOptions,
  useMaintenanceAlerts,
} from './api';
import { AssetSheet } from './AssetSheet';

type Values = {
  name: string;
  kind: Asset['kind'];
  brand: string;
  model: string;
  year: string | null;
  identifier: string;
  meter: Asset['meter'];
  rate: string | null;
  status: Asset['status'];
  notes: string;
};

const EMPTY: Values = {
  name: '',
  kind: 'machinery',
  brand: '',
  model: '',
  year: null,
  identifier: '',
  meter: 'hours',
  rate: '0',
  status: 'operational',
  notes: '',
};

function AssetDrawer({ record, opened, onClose }: DrawerProps<Asset>) {
  const can = useCan();
  const canWrite = can('assets:write');
  const { data: options } = useAssetOptions();
  const { create, update } = useResourceMutations(assetsResource);
  const form = useDrawerForm<Asset, Values>({
    opened,
    record,
    empty: EMPTY,
    toValues: (a) => ({ ...a, year: a.year === null ? null : String(a.year) }),
    validate: { name: required, rate: required },
  });

  async function submit(values: Values) {
    const body = {
      ...values,
      year: values.year ? Number(values.year) : null,
      rate: values.rate ?? '0',
    };
    if (record) await update.mutateAsync({ id: record.id, body });
    else await create.mutateAsync(body);
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nuevo activo'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={assetsResource}
            record={record}
            name={record.name}
            canDeactivate={can('assets:deactivate')}
            onClose={onClose}
          />
        )
      }
    >
      <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
      <SimpleGrid cols={2}>
        <Select
          label="Tipo"
          data={options?.kinds ?? []}
          disabled={!canWrite}
          {...form.getInputProps('kind')}
          onChange={(kind) => {
            form.setFieldValue('kind', (kind ?? 'machinery') as Asset['kind']);
            // Un activo nuevo: los vehículos se miden en km; máquinas y herramientas en horas
            if (!record) form.setFieldValue('meter', kind === 'vehicle' ? 'km' : 'hours');
          }}
        />
        <Select
          label="Estado"
          data={options?.statuses ?? []}
          disabled={!canWrite}
          {...form.getInputProps('status')}
        />
        <TextInput label="Marca" disabled={!canWrite} {...form.getInputProps('brand')} />
        <TextInput label="Modelo" disabled={!canWrite} {...form.getInputProps('model')} />
        <NumberInput
          label="Año"
          kind="quantity"
          disabled={!canWrite}
          {...form.getInputProps('year')}
        />
        <TextInput
          label="Patente / N° de serie"
          disabled={!canWrite}
          {...form.getInputProps('identifier')}
        />
        <Select
          label="Se mide en"
          data={options?.meters ?? []}
          disabled={!canWrite}
          {...form.getInputProps('meter')}
        />
        <NumberInput
          label={`Tarifa ${meterRate(form.values.meter)}`}
          description="Se imputa a las labores"
          kind="price"
          leftSection="$"
          disabled={!canWrite}
          {...form.getInputProps('rate')}
        />
      </SimpleGrid>
      <Textarea
        label="Observaciones"
        autosize
        disabled={!canWrite}
        {...form.getInputProps('notes')}
      />
    </EntityDrawer>
  );
}

/** Tocar un activo abre su ficha; desde la ficha se editan sus datos. */
function AssetView({ record, opened, onClose }: DrawerProps<Asset>) {
  const [editing, setEditing] = useState(false);
  if (!record) return <AssetDrawer record={null} opened={opened} onClose={onClose} />;
  return (
    <>
      <AssetSheet
        asset={opened ? record : null}
        onClose={onClose}
        onEdit={() => setEditing(true)}
      />
      <AssetDrawer record={record} opened={editing} onClose={() => setEditing(false)} />
    </>
  );
}

export function AssetsPage() {
  const can = useCan();
  const { data: options } = useAssetOptions();
  const { data: alerts = [] } = useMaintenanceAlerts();
  const worst = (assetId: string) => {
    const states = alerts.filter((a) => a.asset.id === assetId).map((a) => a.state);
    return states.includes('overdue') ? 'overdue' : states.includes('upcoming') ? 'upcoming' : null;
  };
  const columns: Column<Asset>[] = [
    { key: 'name', header: 'Nombre', sortable: true },
    { key: 'kind', header: 'Tipo', render: (a) => labelOf(options?.kinds, a.kind) },
    {
      key: 'brand',
      header: 'Marca / modelo',
      hideOnMobile: true,
      render: (a) => [a.brand, a.model].filter(Boolean).join(' '),
    },
    {
      key: 'rate',
      header: 'Tarifa',
      align: 'right',
      render: (a) => `${formatMoney(a.rate)} ${meterRate(a.meter)}`,
    },
    {
      key: 'status',
      header: 'Estado',
      render: (a) =>
        a.status === 'in_repair' && (
          <Badge color="orange" variant="light">
            En reparación
          </Badge>
        ),
    },
    {
      key: 'maintenance',
      header: 'Mantenimiento',
      render: (a) => {
        const state = worst(a.id);
        return (
          state && (
            <Badge color={PLAN_STATE[state].color} variant="light">
              {PLAN_STATE[state].label}
            </Badge>
          )
        );
      },
    },
  ];
  return (
    <>
      <PageHeader title="Activos" />
      <CrudTab
        resource={assetsResource}
        columns={columns}
        newLabel="Nuevo activo"
        canCreate={can('assets:write')}
        defaultSort="name"
        renderDrawer={(props) => <AssetView {...props} />}
      />
    </>
  );
}
