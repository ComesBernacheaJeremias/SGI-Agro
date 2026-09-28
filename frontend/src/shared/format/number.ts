/**
 * Formato de números del sistema (ver docs: Requisitos-no-funcionales):
 *   - price:    siempre 2 decimales        → 1.234.567,89
 *   - quantity: 2 decimales, hasta 3       → 1.234,50 · 0,125
 * La API envía los decimales como string ("1234.56"); se aceptan string o number.
 */

export type NumberKind = 'price' | 'quantity';

export const DECIMALS: Record<NumberKind, { min: number; max: number }> = {
  price: { min: 2, max: 2 },
  quantity: { min: 2, max: 3 },
};

export const THOUSAND_SEPARATOR = '.';
export const DECIMAL_SEPARATOR = ',';

const formatters = Object.fromEntries(
  Object.entries(DECIMALS).map(([kind, { min, max }]) => [
    kind,
    new Intl.NumberFormat('es-AR', {
      minimumFractionDigits: min,
      maximumFractionDigits: max,
      // 'always': agrupa también los miles de 4 dígitos (1.234), que es-AR no agrupa por defecto
      useGrouping: 'always' as unknown as boolean,
      // sin "-0,00": signo solo si el número redondeado es negativo (ES2023, falta en los tipos)
      signDisplay: 'negative' as unknown as 'auto',
    }),
  ]),
) as Record<NumberKind, Intl.NumberFormat>;

export function formatNumber(
  value: number | string | null | undefined,
  kind: NumberKind = 'price',
): string {
  if (value === null || value === undefined || value === '') return '';
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? formatters[kind].format(number) : '';
}

/** Formato de moneda: $ 1.234,56 */
export function formatMoney(value: number | string | null | undefined): string {
  const formatted = formatNumber(value, 'price');
  return formatted && `$ ${formatted}`;
}
