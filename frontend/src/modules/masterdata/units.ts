/** Unidades en las que se puede cargar un producto (misma lógica que el backend). */
import type { Product, Unit } from './api';

type ProductUnits = Pick<Product, 'unit' | 'conversions'>;

/** Unidad base + unidades de la misma magnitud (g, tn para kg) + equivalencias propias. */
export function allowedUnits(product: ProductUnits, units: Unit[]): Unit[] {
  const conversionIds = new Set(product.conversions.map((c) => c.unit.id));
  return units.filter(
    (u) =>
      u.id === product.unit.id ||
      conversionIds.has(u.id) ||
      (u.kind === product.unit.kind && u.kind !== 'package'),
  );
}
