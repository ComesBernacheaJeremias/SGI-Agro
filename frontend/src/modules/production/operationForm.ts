/** Formulario de labor/cosecha: valores, vacíos y conversión al cuerpo de la API. */
import dayjs from 'dayjs';

import type { Product } from '@/modules/masterdata/api';

import type { OperationIn } from './api';

export type InputValue = {
  key: string;
  product: Product | null;
  unit_id: string | null;
  /** 'total' = cantidad total · 'dose' = dosis por hectárea */
  mode: 'total' | 'dose';
  value: string | null;
  warehouse_id: string | null;
};

export type AssetValue = { key: string; asset_id: string | null; usage: string | null };

export type HarvestValue = {
  product: Product | null;
  unit_id: string | null;
  quantity: string | null;
  warehouse_id: string | null;
  is_final: boolean;
};

export type OperationValues = {
  date: string | null;
  operation_type_id: string | null;
  cycle_ids: string[];
  /** Superficie trabajada por ciclo (vacío = la del ciclo) */
  areas: Record<string, string | null>;
  inputs: InputValue[];
  assets: AssetValue[];
  harvest: HarvestValue;
  notes: string;
};

const key = () => crypto.randomUUID();

export const emptyInput = (warehouseId: string | null = null): InputValue => ({
  key: key(),
  product: null,
  unit_id: null,
  mode: 'total',
  value: null,
  warehouse_id: warehouseId,
});

export const emptyAsset = (): AssetValue => ({ key: key(), asset_id: null, usage: null });

export const emptyOperation = (cycleId?: string): OperationValues => ({
  date: dayjs().format('YYYY-MM-DD'),
  operation_type_id: null,
  cycle_ids: cycleId ? [cycleId] : [],
  areas: {},
  inputs: [],
  assets: [],
  harvest: { product: null, unit_id: null, quantity: null, warehouse_id: null, is_final: false },
  notes: '',
});

export function toBody(values: OperationValues, isHarvest: boolean): OperationIn {
  return {
    date: values.date as string,
    operation_type_id: values.operation_type_id as string,
    cycles: values.cycle_ids.map((id) => ({
      crop_cycle_id: id,
      area_ha: values.areas[id] || null,
    })),
    inputs: values.inputs.map((i) => ({
      product_id: i.product?.id ?? '',
      unit_id: i.unit_id ?? '',
      warehouse_id: i.warehouse_id ?? '',
      quantity: i.mode === 'total' ? i.value : null,
      dose_per_ha: i.mode === 'dose' ? i.value : null,
    })),
    assets: values.assets.map((a) => ({ asset_id: a.asset_id ?? '', usage: a.usage ?? '0' })),
    harvest: isHarvest
      ? {
          product_id: values.harvest.product?.id ?? null,
          unit_id: values.harvest.unit_id ?? '',
          quantity: values.harvest.quantity ?? '0',
          warehouse_id: values.harvest.warehouse_id ?? '',
          is_final: values.harvest.is_final,
        }
      : null,
    notes: values.notes,
  };
}

/** Mensaje de validación del formulario (null = ok). */
export function validateOperation(values: OperationValues, isHarvest: boolean): string | null {
  if (!values.date || !values.operation_type_id) return 'Completá fecha y tipo de labor.';
  if (values.cycle_ids.length === 0) return 'Elegí al menos un ciclo.';
  if (isHarvest && values.cycle_ids.length !== 1)
    return 'Una cosecha se carga sobre un solo ciclo.';
  if (values.inputs.some((i) => !i.product || !i.unit_id || !i.value || !i.warehouse_id))
    return 'Completá producto, unidad, cantidad y almacén de cada insumo.';
  if (values.assets.some((a) => !a.asset_id || !a.usage))
    return 'Completá el activo y el uso (horas o km) de cada máquina.';
  const h = values.harvest;
  if (isHarvest && (!h.unit_id || !h.quantity || !h.warehouse_id))
    return 'Completá unidad, cantidad y almacén de la cosecha.';
  return null;
}
