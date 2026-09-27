import { Select, SimpleGrid, TextInput } from '@mantine/core';

import { useCan } from '@/app/auth/session';
import { NumberInput } from '@/shared/components/NumberInput';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatNumber } from '@/shared/format/number';

import { labelOf, type Unit, unitsResource, useMasterdataOptions } from './api';

type Values = { code: string; name: string; kind: Unit['kind']; factor: string | null };

const EMPTY: Values = { code: '', name: '', kind: 'package', factor: '1' };

function UnitDrawer({ record, opened, onClose }: DrawerProps<Unit>) {
  const can = useCan();
  const canWrite = can('masterdata:write');
  const { data: options } = useMasterdataOptions();
  const { create, update } = useResourceMutations(unitsResource);
  const form = useDrawerForm<Unit, Values>({
    opened,
    record,
    empty: EMPTY,
    toValues: ({ code, name, kind, factor }) => ({ code, name, kind, factor }),
    validate: { code: required, name: required, factor: required },
  });

  async function submit({ code, name, kind, factor }: Values) {
    const base = { code, name, factor: factor ?? '1' };
    if (record) await update.mutateAsync({ id: record.id, body: base });
    else await create.mutateAsync({ ...base, kind });
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? `Unidad ${record.code}` : 'Nueva unidad'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={unitsResource}
            record={record}
            name={record.name}
            canDeactivate={can('masterdata:deactivate')}
            onClose={onClose}
          />
        )
      }
    >
      <SimpleGrid cols={2}>
        <TextInput
          label="Abreviatura"
          required
          disabled={!canWrite}
          {...form.getInputProps('code')}
        />
        <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
      </SimpleGrid>
      <Select
        label="Tipo"
        description="No se puede cambiar después de crearla"
        required
        data={options?.unit_kinds ?? []}
        disabled={!canWrite || record !== null}
        {...form.getInputProps('kind')}
      />
      <NumberInput
        label="Factor"
        description="Equivalencia con la unidad base del tipo (ej.: 1 tn = 1.000 kg). Envases: 1."
        kind="quantity"
        disabled={!canWrite}
        {...form.getInputProps('factor')}
      />
    </EntityDrawer>
  );
}

export function UnitsTab() {
  const can = useCan();
  const { data: options } = useMasterdataOptions();
  const columns: Column<Unit>[] = [
    { key: 'code', header: 'Abreviatura', sortable: true },
    { key: 'name', header: 'Nombre', sortable: true },
    { key: 'kind', header: 'Tipo', render: (u) => labelOf(options?.unit_kinds, u.kind) },
    {
      key: 'factor',
      header: 'Factor',
      align: 'right',
      render: (u) => formatNumber(u.factor, 'quantity'),
    },
  ];
  return (
    <CrudTab
      resource={unitsResource}
      columns={columns}
      newLabel="Nueva unidad"
      canCreate={can('masterdata:write')}
      defaultSort="name"
      renderDrawer={(props) => <UnitDrawer {...props} />}
    />
  );
}
