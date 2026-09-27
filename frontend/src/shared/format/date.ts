/**
 * Formato de fechas del sistema: dd/mm/aaaa (o mm/aaaa, mm/aa cuando solo importa el mes).
 * La API usa ISO ("2026-09-27" o "2026-09-27T10:00:00-03:00").
 */
import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(customParseFormat);

export const DATE_FORMATS = {
  date: 'DD/MM/YYYY',
  month: 'MM/YYYY',
  monthShort: 'MM/YY',
  dateTime: 'DD/MM/YYYY HH:mm',
} as const;

export type DateFormat = keyof typeof DATE_FORMATS;

/** Formatea una fecha para mostrar. */
export function formatDate(
  value: string | Date | null | undefined,
  format: DateFormat = 'date',
): string {
  if (!value) return '';
  const date = dayjs(value);
  return date.isValid() ? date.format(DATE_FORMATS[format]) : '';
}

/** Interpreta lo que escribe el usuario (dd/mm/aaaa, d/m/aa, ddmmaaaa) → "AAAA-MM-DD" o null. */
export function parseDateInput(text: string): string | null {
  const date = dayjs(
    text.trim(),
    ['DD/MM/YYYY', 'D/M/YYYY', 'DD/MM/YY', 'D/M/YY', 'DDMMYYYY'],
    true,
  );
  return date.isValid() ? date.format('YYYY-MM-DD') : null;
}
