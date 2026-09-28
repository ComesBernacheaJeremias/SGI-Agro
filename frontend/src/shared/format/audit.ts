/** Formato de los valores del historial de cambios. */
import { formatDate } from './date';

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_DATETIME = /^\d{4}-\d{2}-\d{2}T/;

/** Valor del historial para mostrar (fechas, sí/no, listas, vacío). */
export function formatAuditValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (Array.isArray(value)) return value.length ? value.join(', ') : '(ninguno)';
  if (typeof value === 'string' && ISO_DATE.test(value)) return formatDate(value);
  if (typeof value === 'string' && ISO_DATETIME.test(value)) return formatDate(value, 'dateTime');
  return String(value);
}

type Change = { label: string; before?: unknown; after?: unknown };

/** "Precio: 100 → 120" (en un alta, solo el valor nuevo). */
export function formatChange(change: Change, action: string): string {
  const after = formatAuditValue(change.after);
  return action === 'create'
    ? `${change.label}: ${after}`
    : `${change.label}: ${formatAuditValue(change.before)} → ${after}`;
}
