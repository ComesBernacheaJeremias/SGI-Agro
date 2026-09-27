import {
  ActionIcon,
  Button,
  Group,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Text,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';

import { type Asset, meterUnit } from '@/modules/assets/api';
import type { Unit, Warehouse } from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { allowedUnits } from '@/modules/masterdata/units';
import { NumberInput } from '@/shared/components/NumberInput';
import { formatMoney, formatNumber } from '@/shared/format/number';

import { type AssetValue, emptyAsset, emptyInput, type InputValue } from './operationForm';

type InputsProps = {
  value: InputValue[];
  onChange: (value: InputValue[]) => void;
  units: Unit[];
  warehouses: Warehouse[];
  totalArea: number;
  readOnly: boolean;
};

/** Insumos de una labor: cantidad total o dosis por hectárea, y almacén de origen. */
export function InputsField({
  value,
  onChange,
  units,
  warehouses,
  totalArea,
  readOnly,
}: InputsProps) {
  const update = (key: string, patch: Partial<InputValue>) =>
    onChange(value.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  const lastWarehouse = value.at(-1)?.warehouse_id ?? warehouses[0]?.id ?? null;

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Insumos
      </Text>
      {value.map((row) => {
        const unit = units.find((u) => u.id === row.unit_id)?.code ?? '';
        const total = row.mode === 'dose' && row.value ? Number(row.value) * totalArea : null;
        return (
          <Paper key={row.key} withBorder p="xs">
            <Group gap="xs" align="flex-end" wrap="wrap">
              <ProductSelect
                label="Producto"
                stockOnly
                value={row.product}
                onChange={(product) =>
                  update(row.key, { product, unit_id: product?.unit.id ?? null })
                }
                disabled={readOnly}
                style={{ flex: '1 1 200px' }}
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
              <SegmentedControl
                size="xs"
                value={row.mode}
                onChange={(mode) => update(row.key, { mode: mode as InputValue['mode'] })}
                data={[
                  { value: 'total', label: 'Total' },
                  { value: 'dose', label: 'Por ha' },
                ]}
                disabled={readOnly}
              />
              <NumberInput
                label={row.mode === 'dose' ? `Dosis (${unit}/ha)` : 'Cantidad'}
                kind="quantity"
                value={row.value}
                onChange={(v) => update(row.key, { value: v })}
                disabled={readOnly}
                w={120}
              />
              <Select
                label="Almacén"
                data={warehouses.map((w) => ({ value: w.id, label: w.name }))}
                value={row.warehouse_id}
                onChange={(warehouse_id) => update(row.key, { warehouse_id })}
                disabled={readOnly}
                w={160}
              />
              {!readOnly && (
                <ActionIcon
                  variant="subtle"
                  color="red"
                  mb={4}
                  aria-label="Quitar insumo"
                  onClick={() => onChange(value.filter((r) => r.key !== row.key))}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              )}
            </Group>
            {total !== null && (
              <Text size="xs" c="dimmed" mt={4}>
                Total: {formatNumber(total, 'quantity')} {unit} (
                {formatNumber(totalArea, 'quantity')} ha)
              </Text>
            )}
          </Paper>
        );
      })}
      {!readOnly && (
        <Button
          variant="light"
          size="xs"
          w="fit-content"
          leftSection={<IconPlus size={14} />}
          onClick={() => onChange([...value, emptyInput(lastWarehouse)])}
        >
          Agregar insumo
        </Button>
      )}
    </Stack>
  );
}

type AssetsProps = {
  value: AssetValue[];
  onChange: (value: AssetValue[]) => void;
  assets: Asset[];
  readOnly: boolean;
};

/** Maquinaria de una labor: activo y uso (horas o km). */
export function AssetsField({ value, onChange, assets, readOnly }: AssetsProps) {
  const update = (key: string, patch: Partial<AssetValue>) =>
    onChange(value.map((row) => (row.key === key ? { ...row, ...patch } : row)));

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Maquinaria
      </Text>
      {value.map((row) => {
        const asset = assets.find((a) => a.id === row.asset_id);
        const unit = asset ? meterUnit(asset.meter) : '';
        return (
          <Group key={row.key} gap="xs" align="flex-end" wrap="wrap">
            <Select
              label="Activo"
              data={assets
                .filter((a) => a.status === 'operational' || a.id === row.asset_id)
                .map((a) => ({ value: a.id, label: a.name }))}
              value={row.asset_id}
              onChange={(asset_id) => update(row.key, { asset_id })}
              disabled={readOnly}
              searchable
              style={{ flex: '1 1 200px' }}
            />
            <NumberInput
              label={unit === 'km' ? 'Kilómetros' : 'Horas'}
              kind="quantity"
              value={row.usage}
              onChange={(usage) => update(row.key, { usage })}
              disabled={readOnly}
              w={110}
            />
            {asset && row.usage && (
              <Text size="xs" c="dimmed" mb={8}>
                {formatMoney(Number(row.usage) * Number(asset.rate))} ({formatMoney(asset.rate)}/
                {unit})
              </Text>
            )}
            {!readOnly && (
              <ActionIcon
                variant="subtle"
                color="red"
                mb={4}
                aria-label="Quitar activo"
                onClick={() => onChange(value.filter((r) => r.key !== row.key))}
              >
                <IconTrash size={16} />
              </ActionIcon>
            )}
          </Group>
        );
      })}
      {!readOnly && (
        <Button
          variant="light"
          size="xs"
          w="fit-content"
          leftSection={<IconPlus size={14} />}
          onClick={() => onChange([...value, emptyAsset()])}
        >
          Agregar máquina
        </Button>
      )}
    </Stack>
  );
}
