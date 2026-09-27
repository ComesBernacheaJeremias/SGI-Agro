import { ActionIcon, Button, Group, Paper, Select, Stack, Text, TextInput } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';

import type { Unit } from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { allowedUnits } from '@/modules/masterdata/units';
import { NumberInput } from '@/shared/components/NumberInput';
import { formatMoney } from '@/shared/format/number';

import type { Direction, ExpenseCategory } from './api';
import { BatchSelect } from './BatchSelect';
import { DestinationField } from './DestinationField';
import { type DocLineValue, emptyDocLine, lineAmounts, VAT_RATES } from './documentLines';

type Props = {
  direction: Direction;
  value: DocLineValue[];
  onChange: (lines: DocLineValue[]) => void;
  units: Unit[];
  categories: ExpenseCategory[];
  /** Venta: permite elegir la partida de producción propia. */
  batch?: {
    warehouseId: string | null;
    date: string | null;
    stockDocumentId: string | null;
    returning: boolean;
  };
  readOnly: boolean;
  error?: string;
};

/** Renglones de una compra o venta: productos (mueven stock) y gastos/conceptos. */
export function DocumentLinesField({
  direction,
  value,
  onChange,
  units,
  categories,
  batch,
  readOnly,
  error,
}: Props) {
  const isPurchase = direction === 'purchase';
  const update = (key: string, patch: Partial<DocLineValue>) =>
    onChange(value.map((line) => (line.key === key ? { ...line, ...patch } : line)));

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Detalle
      </Text>
      {value.map((line) => {
        const { net } = lineAmounts(line);
        const unitOptions = line.product
          ? allowedUnits(line.product, units).map((u) => ({ value: u.id, label: u.code }))
          : [];
        return (
          <Paper key={line.key} withBorder p="xs">
            <Group gap="xs" align="flex-end" wrap="wrap">
              {line.kind === 'product' ? (
                <>
                  <ProductSelect
                    label="Producto"
                    stockOnly
                    value={line.product}
                    onChange={(product) =>
                      update(line.key, {
                        product,
                        unit_id: product?.unit.id ?? null,
                        batch_id: null,
                      })
                    }
                    disabled={readOnly}
                    style={{ flex: '1 1 220px' }}
                  />
                  <Select
                    label="Unidad"
                    data={unitOptions}
                    value={line.unit_id}
                    onChange={(unit_id) => update(line.key, { unit_id })}
                    disabled={readOnly || !line.product}
                    w={90}
                  />
                  <NumberInput
                    label="Cantidad"
                    kind="quantity"
                    value={line.quantity}
                    onChange={(quantity) => update(line.key, { quantity })}
                    disabled={readOnly}
                    w={110}
                  />
                </>
              ) : (
                <>
                  {isPurchase && (
                    <Select
                      label="Categoría"
                      data={categories.map((c) => ({ value: c.id, label: c.name }))}
                      value={line.expense_category_id}
                      onChange={(expense_category_id) => update(line.key, { expense_category_id })}
                      searchable
                      disabled={readOnly}
                      style={{ flex: '1 1 180px' }}
                    />
                  )}
                  <TextInput
                    label={isPurchase ? 'Detalle' : 'Concepto'}
                    value={line.description}
                    onChange={(e) => update(line.key, { description: e.currentTarget.value })}
                    disabled={readOnly}
                    style={{ flex: '1 1 200px' }}
                  />
                </>
              )}
              <NumberInput
                label={line.kind === 'product' ? 'Precio unit. (neto)' : 'Importe neto'}
                kind="price"
                leftSection="$"
                value={line.unit_price}
                onChange={(unit_price) => update(line.key, { unit_price })}
                disabled={readOnly}
                w={150}
              />
              <Select
                label="IVA"
                data={VAT_RATES}
                value={line.vat_rate}
                onChange={(v) => update(line.key, { vat_rate: v ?? '21' })}
                allowDeselect={false}
                disabled={readOnly}
                w={90}
              />
              {!readOnly && (
                <ActionIcon
                  variant="subtle"
                  color="red"
                  mb={4}
                  aria-label="Quitar línea"
                  onClick={() => onChange(value.filter((l) => l.key !== line.key))}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              )}
            </Group>
            {line.kind === 'expense' && isPurchase && (
              <Group gap="xs" mt="xs" align="flex-end" wrap="wrap">
                <DestinationField
                  value={line.destination}
                  onChange={(destination) => update(line.key, { destination })}
                  disabled={readOnly}
                />
              </Group>
            )}
            {batch && line.kind === 'product' && line.product?.type === 'own_produce' && (
              <Group gap="xs" mt="xs">
                <BatchSelect
                  productId={line.product.id}
                  unitCode={line.product.unit.code}
                  warehouseId={batch.warehouseId}
                  date={batch.date}
                  excludeDocumentId={batch.stockDocumentId}
                  returning={batch.returning}
                  value={line.batch_id}
                  onChange={(batch_id) => update(line.key, { batch_id })}
                  disabled={readOnly}
                />
              </Group>
            )}
            {line.kind === 'product' && net > 0 && (
              <Text size="xs" c="dimmed" mt={4}>
                Subtotal neto: {formatMoney(net)}
              </Text>
            )}
          </Paper>
        );
      })}
      {error && (
        <Text size="xs" c="red">
          {error}
        </Text>
      )}
      {!readOnly && (
        <Group gap="xs">
          <Button
            variant="light"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={() => onChange([...value, emptyDocLine('product')])}
          >
            Agregar producto
          </Button>
          <Button
            variant="light"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={() => onChange([...value, emptyDocLine('expense')])}
          >
            {isPurchase ? 'Agregar gasto o servicio' : 'Agregar concepto'}
          </Button>
        </Group>
      )}
    </Stack>
  );
}
