/** Línea de una compra o venta en el formulario. */
import type { Product } from '@/modules/masterdata/api';

import { type Destination, emptyDestination } from './destination';

export type DocLineValue = {
  key: string;
  kind: 'product' | 'expense';
  product: Product | null;
  unit_id: string | null;
  quantity: string | null;
  /** Venta de producción propia: partida elegida (null = las más antiguas). */
  batch_id: string | null;
  description: string;
  expense_category_id: string | null;
  destination: Destination;
  unit_price: string | null;
  vat_rate: string;
};

export const emptyDocLine = (kind: DocLineValue['kind']): DocLineValue => ({
  key: crypto.randomUUID(),
  kind,
  product: null,
  unit_id: null,
  quantity: kind === 'expense' ? '1' : null,
  batch_id: null,
  description: '',
  expense_category_id: null,
  destination: emptyDestination(),
  unit_price: null,
  vat_rate: '21',
});

const VAT_RATES = ['21', '10.5', '27', '0'];

/** "10.50" (API) → "10.5" (valor del desplegable). */
export const rateText = (rate: string | number) => String(Number(rate));

/** Alícuotas del desplegable (incluye la de la línea si es otra, ej. la de un producto). */
export function vatOptions(current: string) {
  const rates = VAT_RATES.includes(current) ? VAT_RATES : [...VAT_RATES, current];
  return rates.map((v) => ({ value: v, label: `${v.replace('.', ',')} %` }));
}

/** Neto e IVA de una línea (el backend es el que calcula lo que se guarda). */
export function lineAmounts(line: DocLineValue): { net: number; vat: number } {
  const net = Math.round(Number(line.quantity ?? 0) * Number(line.unit_price ?? 0) * 100) / 100;
  return { net, vat: Math.round(net * Number(line.vat_rate)) / 100 };
}
