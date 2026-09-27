import { Select, TextInput } from '@mantine/core';

import { useCan } from '@/app/auth/session';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';

import { categoriesResource, type Category, useActiveList } from './api';

type Values = { name: string; parent_id: string | null };

const EMPTY: Values = { name: '', parent_id: null };

function CategoryDrawer({ record, opened, onClose }: DrawerProps<Category>) {
  const can = useCan();
  const canWrite = can('masterdata:write');
  const { data: categories = [] } = useActiveList(categoriesResource);
  const { create, update } = useResourceMutations(categoriesResource);
  const form = useDrawerForm<Category, Values>({
    opened,
    record,
    empty: EMPTY,
    toValues: ({ name, parent_id }) => ({ name, parent_id }),
    validate: { name: required },
  });

  async function submit(values: Values) {
    if (record) await update.mutateAsync({ id: record.id, body: values });
    else await create.mutateAsync(values);
  }

  // No se puede elegir como padre a sí misma ni a sus subcategorías
  const parentOptions = categories
    .filter((c) => !record || (c.id !== record.id && !c.path.startsWith(`${record.path} > `)))
    .map((c) => ({ value: c.id, label: c.path }));

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.path : 'Nueva categoría'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={categoriesResource}
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
        label="Dentro de"
        placeholder="(categoría principal)"
        data={parentOptions}
        searchable
        clearable
        disabled={!canWrite}
        {...form.getInputProps('parent_id')}
      />
    </EntityDrawer>
  );
}

const COLUMNS: Column<Category>[] = [{ key: 'path', header: 'Categoría' }];

export function CategoriesTab() {
  const can = useCan();
  return (
    <CrudTab
      resource={categoriesResource}
      columns={COLUMNS}
      newLabel="Nueva categoría"
      canCreate={can('masterdata:write')}
      defaultSort="name"
      renderDrawer={(props) => <CategoryDrawer {...props} />}
    />
  );
}
