import {
  Checkbox,
  Group,
  SegmentedControl,
  Select,
  SimpleGrid,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useState } from 'react';

import { useCan } from '@/app/auth/session';
import { NumberInput } from '@/shared/components/NumberInput';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatCuit } from '@/shared/format/cuit';

import { labelOf, type Party, partiesResource, useMasterdataOptions } from './api';

type Values = {
  name: string;
  trade_name: string;
  cuit: string;
  vat_condition: Party['vat_condition'];
  is_customer: boolean;
  is_supplier: boolean;
  address: string;
  city: string;
  province: string;
  phone: string;
  email: string;
  payment_days: string | null;
  notes: string;
};

const EMPTY: Values = {
  name: '',
  trade_name: '',
  cuit: '',
  vat_condition: 'registered',
  is_customer: false,
  is_supplier: false,
  address: '',
  city: '',
  province: '',
  phone: '',
  email: '',
  payment_days: '0',
  notes: '',
};

function PartyDrawer({ record, opened, onClose }: DrawerProps<Party>) {
  const can = useCan();
  const canWrite = can('masterdata:write');
  const { data: options } = useMasterdataOptions();
  const { create, update } = useResourceMutations(partiesResource);

  const form = useDrawerForm<Party, Values>({
    opened,
    record,
    empty: EMPTY,
    toValues: (p) => ({
      ...p,
      cuit: formatCuit(p.cuit),
      payment_days: String(p.payment_days),
    }),
    validate: {
      name: required,
      is_supplier: (value, values) =>
        value || values.is_customer ? null : 'Marcá si es cliente, proveedor o ambos',
    },
  });

  async function submit(values: Values) {
    const body = {
      ...values,
      cuit: values.cuit.trim() || null,
      payment_days: Number(values.payment_days ?? 0),
    };
    if (record) await update.mutateAsync({ id: record.id, body });
    else await create.mutateAsync(body);
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nuevo cliente/proveedor'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={partiesResource}
            record={record}
            name={record.name}
            canDeactivate={can('masterdata:deactivate')}
            onClose={onClose}
          />
        )
      }
    >
      <Group>
        <Checkbox
          label="Cliente"
          disabled={!canWrite}
          {...form.getInputProps('is_customer', { type: 'checkbox' })}
        />
        <Checkbox
          label="Proveedor"
          disabled={!canWrite}
          {...form.getInputProps('is_supplier', { type: 'checkbox' })}
        />
      </Group>
      <TextInput
        label="Razón social"
        required
        disabled={!canWrite}
        {...form.getInputProps('name')}
      />
      <TextInput
        label="Nombre de fantasía"
        disabled={!canWrite}
        {...form.getInputProps('trade_name')}
      />
      <SimpleGrid cols={2}>
        <TextInput
          label="CUIT"
          placeholder="20-12345678-9"
          disabled={!canWrite}
          {...form.getInputProps('cuit')}
          onBlur={() => form.setFieldValue('cuit', formatCuit(form.values.cuit))}
        />
        <Select
          label="Condición IVA"
          required
          data={options?.vat_conditions ?? []}
          disabled={!canWrite}
          {...form.getInputProps('vat_condition')}
        />
      </SimpleGrid>
      <TextInput label="Domicilio" disabled={!canWrite} {...form.getInputProps('address')} />
      <SimpleGrid cols={2}>
        <TextInput label="Localidad" disabled={!canWrite} {...form.getInputProps('city')} />
        <TextInput label="Provincia" disabled={!canWrite} {...form.getInputProps('province')} />
        <TextInput label="Teléfono" disabled={!canWrite} {...form.getInputProps('phone')} />
        <TextInput
          label="Email"
          type="email"
          disabled={!canWrite}
          {...form.getInputProps('email')}
        />
      </SimpleGrid>
      <NumberInput
        label="Días de pago"
        description="Plazo habitual para vencimientos"
        kind="quantity"
        disabled={!canWrite}
        {...form.getInputProps('payment_days')}
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

type RoleFilter = 'all' | 'customer' | 'supplier';

export function PartiesTab() {
  const can = useCan();
  const { data: options } = useMasterdataOptions();
  const [role, setRole] = useState<RoleFilter>('all');

  const columns: Column<Party>[] = [
    { key: 'name', header: 'Razón social', sortable: true },
    { key: 'cuit', header: 'CUIT', render: (p) => formatCuit(p.cuit) || '—' },
    {
      key: 'vat_condition',
      header: 'Condición IVA',
      hideOnMobile: true,
      render: (p) => labelOf(options?.vat_conditions, p.vat_condition),
    },
    {
      key: 'roles',
      header: 'Tipo',
      render: (p) =>
        [p.is_customer && 'Cliente', p.is_supplier && 'Proveedor'].filter(Boolean).join(' y '),
    },
    { key: 'phone', header: 'Teléfono', hideOnMobile: true },
  ];

  return (
    <CrudTab
      resource={partiesResource}
      columns={columns}
      newLabel="Nuevo cliente/proveedor"
      canCreate={can('masterdata:write')}
      defaultSort="name"
      searchPlaceholder="Buscar por nombre o CUIT…"
      extraParams={{ role: role === 'all' ? undefined : role }}
      filters={(list) => (
        <SegmentedControl
          size="xs"
          value={role}
          onChange={(v) => {
            setRole(v as RoleFilter);
            list.setPage(1);
          }}
          data={[
            { value: 'all', label: 'Todos' },
            { value: 'customer', label: 'Clientes' },
            { value: 'supplier', label: 'Proveedores' },
          ]}
        />
      )}
      renderDrawer={(props) => <PartyDrawer {...props} />}
    />
  );
}
