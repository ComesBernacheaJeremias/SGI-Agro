import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { FormError } from '@/api/errors';
import { useCan } from '@/app/auth/session';
import {
  type Product,
  productsResource,
  type Unit,
  unitsResource,
  useActiveList,
} from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { allowedUnits } from '@/modules/masterdata/units';
import { NumberInput } from '@/shared/components/NumberInput';
import { CrudTab, type DrawerProps } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { useDrawerForm } from '@/shared/crud/useDrawerForm';
import { formatMoney, formatNumber } from '@/shared/format/number';

import { type Recipe, recipesResource } from './api';

type ComponentValue = {
  key: string;
  product: Product | null;
  unit_id: string | null;
  quantity: string | null;
};
type Values = { yield_quantity: string | null; yield_unit_id: string | null; instructions: string };

const newComponent = (): ComponentValue => ({
  key: crypto.randomUUID(),
  product: null,
  unit_id: null,
  quantity: null,
});

function ComponentsField({
  value,
  onChange,
  units,
  readOnly,
}: {
  value: ComponentValue[];
  onChange: (v: ComponentValue[]) => void;
  units: Unit[];
  readOnly: boolean;
}) {
  const update = (key: string, patch: Partial<ComponentValue>) =>
    onChange(value.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Componentes
      </Text>
      {value.map((row) => (
        <Group key={row.key} gap="xs" align="flex-end" wrap="wrap">
          <ProductSelect
            label="Producto"
            types={['input', 'semi_finished']}
            value={row.product}
            onChange={(product) => update(row.key, { product, unit_id: product?.unit.id ?? null })}
            disabled={readOnly}
            style={{ flex: '1 1 220px' }}
          />
          <Select
            label="Unidad"
            data={
              row.product
                ? allowedUnits(row.product, units).map((u) => ({ value: u.id, label: u.code }))
                : []
            }
            value={row.unit_id}
            onChange={(unit_id) => update(row.key, { unit_id })}
            disabled={readOnly || !row.product}
            w={85}
          />
          <NumberInput
            label="Cantidad"
            kind="quantity"
            value={row.quantity}
            onChange={(quantity) => update(row.key, { quantity })}
            disabled={readOnly}
            w={120}
          />
          {!readOnly && (
            <ActionIcon
              variant="subtle"
              color="red"
              mb={4}
              aria-label="Quitar"
              onClick={() => onChange(value.filter((r) => r.key !== row.key))}
            >
              <IconTrash size={16} />
            </ActionIcon>
          )}
        </Group>
      ))}
      {!readOnly && (
        <Button
          variant="light"
          size="xs"
          w="fit-content"
          leftSection={<IconPlus size={14} />}
          onClick={() => onChange([...value, newComponent()])}
        >
          Agregar componente
        </Button>
      )}
    </Stack>
  );
}

function RecipeDrawer({ record, opened, onClose }: DrawerProps<Recipe>) {
  const can = useCan();
  const canWrite = can('manufacturing:write');
  const { data: units = [] } = useActiveList(unitsResource);
  const { create, update } = useResourceMutations(recipesResource);
  const [product, setProduct] = useState<Product | null>(null);
  const [components, setComponents] = useState<ComponentValue[]>(() => [newComponent()]);

  const form = useDrawerForm<Recipe, Values>({
    opened,
    record,
    empty: { yield_quantity: '1', yield_unit_id: null, instructions: '' },
    toValues: (r) => ({
      yield_quantity: r.yield_quantity,
      yield_unit_id: r.yield_unit.id,
      instructions: r.instructions,
    }),
  });

  useEffect(() => {
    if (!opened || !record) return;
    void productsResource.get(record.product.id).then(setProduct);
    void Promise.all(record.components.map((c) => productsResource.get(c.product.id))).then(
      (products) =>
        setComponents(
          record.components.map((c, i) => ({
            key: crypto.randomUUID(),
            product: products[i] ?? null,
            unit_id: c.unit.id,
            quantity: c.quantity,
          })),
        ),
    );
  }, [opened, record]);

  async function submit(values: Values) {
    if (!product || !values.yield_quantity || !values.yield_unit_id)
      throw new FormError('Completá producto y rinde.');
    if (
      components.length === 0 ||
      components.some((c) => !c.product || !c.unit_id || !c.quantity)
    ) {
      throw new FormError('Completá producto, unidad y cantidad de cada componente.');
    }
    const body = {
      yield_quantity: values.yield_quantity,
      yield_unit_id: values.yield_unit_id,
      instructions: values.instructions,
      components: components.map((c) => ({
        product_id: c.product?.id ?? '',
        unit_id: c.unit_id ?? '',
        quantity: c.quantity ?? '0',
      })),
    };
    if (record) await update.mutateAsync({ id: record.id, body });
    else await create.mutateAsync({ ...body, product_id: product.id });
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={record ? `Receta: ${record.name}` : 'Nueva receta'}
      form={form}
      isEdit={record !== null}
      onSubmit={submit}
      readOnly={!canWrite}
      size="lg"
      extraActions={
        record && (
          <RecordActions
            resource={recipesResource}
            record={record}
            name={record.name}
            canDeactivate={canWrite}
            onClose={onClose}
          />
        )
      }
    >
      <ProductSelect
        label="Producto elaborado"
        description="Semielaborado o producto terminado"
        required
        types={['semi_finished', 'finished']}
        value={product}
        onChange={(p) => {
          setProduct(p);
          form.setFieldValue('yield_unit_id', p?.unit.id ?? null);
        }}
        disabled={!canWrite || record !== null}
      />
      <SimpleGrid cols={2}>
        <NumberInput
          label="Rinde"
          required
          kind="quantity"
          disabled={!canWrite}
          {...form.getInputProps('yield_quantity')}
        />
        <Select
          label="Unidad"
          required
          data={
            product ? allowedUnits(product, units).map((u) => ({ value: u.id, label: u.code })) : []
          }
          disabled={!canWrite || !product}
          {...form.getInputProps('yield_unit_id')}
        />
      </SimpleGrid>
      <ComponentsField
        value={components}
        onChange={setComponents}
        units={units}
        readOnly={!canWrite}
      />
      {record && (
        <Paper withBorder p="xs">
          <Group gap="xs" wrap="wrap">
            {record.components
              .filter((c) => c.has_recipe)
              .map((c) => (
                <Badge key={c.product.id} variant="light">
                  {c.product.name}: tiene receta propia
                </Badge>
              ))}
          </Group>
          <Text size="sm" mt={4}>
            Costo estimado hoy: <b>{formatMoney(record.estimated_cost)}</b> por{' '}
            {record.yield_unit.code}
          </Text>
        </Paper>
      )}
      <Textarea
        label="Instrucciones"
        autosize
        minRows={2}
        disabled={!canWrite}
        {...form.getInputProps('instructions')}
      />
    </EntityDrawer>
  );
}

export function RecipesTab() {
  const canWrite = useCan()('manufacturing:write');
  const columns: Column<Recipe>[] = [
    { key: 'name', header: 'Producto', sortable: true },
    {
      key: 'yield',
      header: 'Rinde',
      render: (r) => `${formatNumber(r.yield_quantity, 'quantity')} ${r.yield_unit.code}`,
    },
    {
      key: 'components',
      header: 'Componentes',
      hideOnMobile: true,
      render: (r) => r.components.map((c) => c.product.name).join(', '),
    },
    {
      key: 'estimated_cost',
      header: 'Costo estimado',
      align: 'right',
      render: (r) => `${formatMoney(r.estimated_cost)} / ${r.yield_unit.code}`,
    },
  ];
  return (
    <CrudTab
      resource={recipesResource}
      columns={columns}
      newLabel="Nueva receta"
      canCreate={canWrite}
      defaultSort="name"
      renderDrawer={(props) => <RecipeDrawer {...props} />}
    />
  );
}
