import { Select, SimpleGrid, Tabs, TextInput } from '@mantine/core';

import { useCan } from '@/app/auth/session';
import { labelOf } from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatDate } from '@/shared/format/date';
import { formatMoney } from '@/shared/format/number';

import {
  type CashAccount,
  cashAccountsResource,
  type ExpenseCategory,
  expenseCategoriesResource,
  useCommercialOptions,
} from './api';

// --- Categorías de gasto ---

function CategoryDrawer({ record, opened, onClose }: DrawerProps<ExpenseCategory>) {
  const canWrite = useCan()('commercial:write');
  const { create, update } = useResourceMutations(expenseCategoriesResource);
  const form = useDrawerForm<ExpenseCategory, { name: string }>({
    opened,
    record,
    empty: { name: '' },
    toValues: ({ name }) => ({ name }),
    validate: { name: required },
  });
  async function submit(values: { name: string }) {
    if (record) await update.mutateAsync({ id: record.id, body: values });
    else await create.mutateAsync(values);
  }
  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nueva categoría de gasto'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={expenseCategoriesResource}
            record={record}
            name={record.name}
            canDeactivate={canWrite}
            onClose={onClose}
          />
        )
      }
    >
      <TextInput label="Nombre" required disabled={!canWrite} {...form.getInputProps('name')} />
    </EntityDrawer>
  );
}

// --- Cajas y bancos ---

type AccountValues = {
  name: string;
  kind: CashAccount['kind'];
  opening_balance: string | null;
  opening_date: string | null;
};

function AccountDrawer({ record, opened, onClose }: DrawerProps<CashAccount>) {
  const canWrite = useCan()('cash:write');
  const { data: options } = useCommercialOptions();
  const { create, update } = useResourceMutations(cashAccountsResource);
  const form = useDrawerForm<CashAccount, AccountValues>({
    opened,
    record,
    empty: { name: '', kind: 'cash', opening_balance: '0', opening_date: null },
    toValues: ({ name, kind, opening_balance, opening_date }) => ({
      name,
      kind,
      opening_balance,
      opening_date,
    }),
    validate: { name: required, opening_date: required },
  });
  async function submit(values: AccountValues) {
    const body = {
      name: values.name,
      opening_balance: values.opening_balance ?? '0',
      opening_date: values.opening_date as string,
    };
    if (record) await update.mutateAsync({ id: record.id, body });
    else await create.mutateAsync({ ...body, kind: values.kind });
  }
  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? record.name : 'Nueva caja o banco'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={cashAccountsResource}
            record={record}
            name={record.name}
            canDeactivate={canWrite}
            onClose={onClose}
          />
        )
      }
    >
      <TextInput
        label="Nombre"
        placeholder="Caja, Banco Nación c/c…"
        required
        disabled={!canWrite}
        {...form.getInputProps('name')}
      />
      <Select
        label="Tipo"
        data={options?.cash_account_kinds ?? []}
        allowDeselect={false}
        disabled={!canWrite || record !== null}
        {...form.getInputProps('kind')}
      />
      <SimpleGrid cols={2}>
        <NumberInput
          label="Saldo inicial"
          kind="price"
          leftSection="$"
          allowNegative
          disabled={!canWrite}
          {...form.getInputProps('opening_balance')}
        />
        <DateInput
          label="Al día"
          description="No se pueden cargar movimientos anteriores"
          required
          disabled={!canWrite}
          {...form.getInputProps('opening_date')}
        />
      </SimpleGrid>
    </EntityDrawer>
  );
}

// --- Pestaña ---

export function ConfigTab() {
  const can = useCan();
  const { data: options } = useCommercialOptions();
  const categoryColumns: Column<ExpenseCategory>[] = [
    { key: 'name', header: 'Categoría', sortable: true },
  ];
  const accountColumns: Column<CashAccount>[] = [
    { key: 'name', header: 'Nombre', sortable: true },
    { key: 'kind', header: 'Tipo', render: (a) => labelOf(options?.cash_account_kinds, a.kind) },
    {
      key: 'opening_balance',
      header: 'Saldo inicial',
      align: 'right',
      render: (a) => `${formatMoney(a.opening_balance)} al ${formatDate(a.opening_date)}`,
    },
  ];
  return (
    <Tabs
      defaultValue={can('cash:read') ? 'accounts' : 'categories'}
      keepMounted={false}
      variant="pills"
    >
      <Tabs.List mb="md">
        {can('cash:read') && <Tabs.Tab value="accounts">Cajas y bancos</Tabs.Tab>}
        <Tabs.Tab value="categories">Categorías de gasto</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="accounts">
        <CrudTab
          resource={cashAccountsResource}
          columns={accountColumns}
          newLabel="Nueva caja o banco"
          canCreate={can('cash:write')}
          defaultSort="name"
          renderDrawer={(p) => <AccountDrawer {...p} />}
        />
      </Tabs.Panel>
      <Tabs.Panel value="categories">
        <CrudTab
          resource={expenseCategoriesResource}
          columns={categoryColumns}
          newLabel="Nueva categoría"
          canCreate={can('commercial:write')}
          defaultSort="name"
          renderDrawer={(p) => <CategoryDrawer {...p} />}
        />
      </Tabs.Panel>
    </Tabs>
  );
}
