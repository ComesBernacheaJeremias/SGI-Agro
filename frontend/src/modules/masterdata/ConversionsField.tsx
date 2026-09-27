import { ActionIcon, Button, Group, Select, Stack, Text } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';

import { NumberInput } from '@/shared/components/NumberInput';

import type { Unit } from './api';

/** 1 <unidad del producto> = `quantity` <unit_id>   (ej. 1 cajón = 18 kg) */
export type ConversionValue = { unit_id: string; quantity: string | null };

type Props = {
  value: ConversionValue[];
  onChange: (value: ConversionValue[]) => void;
  units: Unit[];
  baseUnitId: string;
  disabled?: boolean;
};

/** Equivalencias propias del producto: 1 cajón = 18 kg, 1 bin = 20 cajones… */
export function ConversionsField({ value, onChange, units, baseUnitId, disabled }: Props) {
  const baseUnit = units.find((u) => u.id === baseUnitId);
  const options = units
    .filter((u) => u.id !== baseUnitId)
    .map((u) => ({ value: u.id, label: `${u.code} (${u.name})` }));

  const update = (index: number, patch: Partial<ConversionValue>) =>
    onChange(value.map((row, i) => (i === index ? { ...row, ...patch } : row)));

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Equivalencias
      </Text>
      {value.length === 0 && (
        <Text size="xs" c="dimmed">
          Opcional. Ej.: 1 {baseUnit?.code ?? 'cajón'} = 18 kg.
        </Text>
      )}
      {value.map((row, index) => (
        <Group key={index} gap="xs" wrap="nowrap" align="center">
          <Text size="sm" w={70} ta="right">
            1 {baseUnit?.code}
          </Text>
          <Text size="sm">=</Text>
          <NumberInput
            kind="quantity"
            value={row.quantity}
            onChange={(quantity) => update(index, { quantity })}
            disabled={disabled}
            w={110}
          />
          <Select
            data={options}
            value={row.unit_id || null}
            onChange={(unitId) => update(index, { unit_id: unitId ?? '' })}
            placeholder="Unidad"
            disabled={disabled}
            w={160}
          />
          {!disabled && (
            <ActionIcon
              variant="subtle"
              color="red"
              aria-label="Quitar"
              onClick={() => onChange(value.filter((_, i) => i !== index))}
            >
              <IconTrash size={16} />
            </ActionIcon>
          )}
        </Group>
      ))}
      {!disabled && (
        <Button
          variant="light"
          size="xs"
          leftSection={<IconPlus size={14} />}
          onClick={() => onChange([...value, { unit_id: '', quantity: null }])}
          disabled={!baseUnitId}
          w="fit-content"
        >
          Agregar equivalencia
        </Button>
      )}
    </Stack>
  );
}
