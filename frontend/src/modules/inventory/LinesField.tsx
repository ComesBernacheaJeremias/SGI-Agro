import { ActionIcon, Button, Group, Paper, Select, Stack, Text } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';

import type { Unit } from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { allowedUnits } from '@/modules/masterdata/units';
import { NumberInput } from '@/shared/components/NumberInput';
import { formatMoney, formatNumber } from '@/shared/format/number';

import { emptyLine, type LineValue } from './lines';

type Props = {
  value: LineValue[];
  onChange: (lines: LineValue[]) => void;
  units: Unit[];
  withCost: boolean;
  /** Ajuste: la cantidad es lo contado; se muestra el stock del sistema (unidad base). */
  systemStock?: Record<string, number>;
  readOnly: boolean;
  error?: string;
};

function factorOf(line: LineValue, units: Unit[]): number {
  const product = line.product;
  if (!product || !line.unit_id) return 1;
  if (line.unit_id === product.unit.id) return 1;
  const conversion = product.conversions.find((c) => c.unit.id === line.unit_id);
  if (conversion) return 1 / Number(conversion.quantity); // 1 base = quantity unidades
  const unit = units.find((u) => u.id === line.unit_id);
  const base = units.find((u) => u.id === product.unit.id);
  return unit && base ? Number(unit.factor) / Number(base.factor) : 1;
}

/** Renglones de un comprobante de stock. */
export function LinesField({
  value,
  onChange,
  units,
  withCost,
  systemStock,
  readOnly,
  error,
}: Props) {
  const update = (key: string, patch: Partial<LineValue>) =>
    onChange(value.map((line) => (line.key === key ? { ...line, ...patch } : line)));

  const total = value.reduce(
    (sum, l) => sum + Number(l.quantity ?? 0) * Number(l.unit_cost ?? 0),
    0,
  );

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Productos
      </Text>
      {value.map((line) => {
        const unitOptions = line.product
          ? allowedUnits(line.product, units).map((u) => ({ value: u.id, label: u.code }))
          : [];
        const current = line.product && systemStock ? (systemStock[line.product.id] ?? 0) : null;
        const counted = Number(line.quantity ?? 0) * factorOf(line, units);
        return (
          <Paper key={line.key} withBorder p="xs">
            <Group gap="xs" align="flex-end" wrap="wrap">
              <ProductSelect
                label="Producto"
                stockOnly
                value={line.product}
                onChange={(product) =>
                  update(line.key, { product, unit_id: product?.unit.id ?? null })
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
                label={systemStock ? 'Contado' : 'Cantidad'}
                kind="quantity"
                value={line.quantity}
                onChange={(quantity) => update(line.key, { quantity })}
                disabled={readOnly}
                w={120}
              />
              {withCost && (
                <NumberInput
                  label="Costo unitario"
                  kind="price"
                  leftSection="$"
                  value={line.unit_cost}
                  onChange={(unit_cost) => update(line.key, { unit_cost })}
                  disabled={readOnly}
                  w={140}
                />
              )}
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
            {withCost && line.quantity && line.unit_cost && (
              <Text size="xs" c="dimmed" mt={4}>
                Subtotal: {formatMoney(Number(line.quantity) * Number(line.unit_cost))}
              </Text>
            )}
            {current !== null && line.product && (
              <Text size="xs" c="dimmed" mt={4}>
                Según el sistema: {formatNumber(current, 'quantity')} {line.product.unit.code}
                {line.quantity !== null &&
                  ` · Diferencia: ${formatNumber(counted - current, 'quantity')} ${line.product.unit.code}`}
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
      <Group justify="space-between">
        {!readOnly && (
          <Button
            variant="light"
            size="xs"
            leftSection={<IconPlus size={14} />}
            onClick={() => onChange([...value, emptyLine()])}
          >
            Agregar producto
          </Button>
        )}
        {withCost && total > 0 && <Text fw={600}>Total: {formatMoney(total)}</Text>}
      </Group>
    </Stack>
  );
}
