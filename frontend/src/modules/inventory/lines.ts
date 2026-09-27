/** Línea de un comprobante de stock en el formulario. */
import type { Product } from '@/modules/masterdata/api';

export type LineValue = {
  key: string;
  product: Product | null;
  unit_id: string | null;
  quantity: string | null;
  unit_cost: string | null;
};

export const emptyLine = (): LineValue => ({
  key: crypto.randomUUID(),
  product: null,
  unit_id: null,
  quantity: null,
  unit_cost: null,
});
