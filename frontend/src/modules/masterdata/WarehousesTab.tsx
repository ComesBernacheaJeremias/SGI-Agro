import { Select, TextInput } from '@mantine/core';

import { useCan } from '@/app/auth/session';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';

import { labelOf, useMasterdataOptions, type Warehouse, warehousesResource } from './api';

type Values = { name: string; kind: Warehouse['kind']; location: string };

const EMPTY: Values = { name: '', kind: 'depot', location: '' };

function WarehouseDrawer({ record, opened, onClose }: DrawerProps<Warehouse>) {
  const can = useCan();
  const canWrite = can('masterdata:write');
  const { data: options } = useMasterdataOptions();
  const { create, update } = useResourceMutations(warehousesResource);
  const form = useDrawerForm<Warehouse, Values>({
    opened,
    record,
    empty: EMPTY,
    toValues: ({ name, kind, location }) => ({ name, kind, location }),
    validate: { name: required },
  });

  async function submit(values: Values) {
    if (record) await update.mutateAsync({ id: record.id, body: values });
    else await create.mutateAsync(values);
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nuevo almacén'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={warehousesResource}
            record={record}
            name={record.name}
            canDeactivate={can('masterdata:deactivate')}
            onClose={onClose}
          />
        )
      }
    >
      <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
      <Select
        label="Tipo"
        required
        data={options?.warehouse_kinds ?? []}
        disabled={!canWrite}
        {...form.getInputProps('kind')}
      />
      <TextInput label="Ubicación" disabled={!canWrite} {...form.getInputProps('location')} />
    </EntityDrawer>
  );
}

export function WarehousesTab() {
  const can = useCan();
  const { data: options } = useMasterdataOptions();
  const columns: Column<Warehouse>[] = [
    { key: 'name', header: 'Nombre', sortable: true },
    { key: 'kind', header: 'Tipo', render: (w) => labelOf(options?.warehouse_kinds, w.kind) },
    { key: 'location', header: 'Ubicación', hideOnMobile: true },
  ];
  return (
    <CrudTab
      resource={warehousesResource}
      columns={columns}
      newLabel="Nuevo almacén"
      canCreate={can('masterdata:write')}
      defaultSort="name"
      renderDrawer={(props) => <WarehouseDrawer {...props} />}
    />
  );
}
