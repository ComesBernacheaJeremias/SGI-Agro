import { DateInput as MantineDateInput, type DateInputProps } from '@mantine/dates';

import { DATE_FORMATS, parseDateInput } from '@/shared/format/date';

type Props = Omit<DateInputProps, 'value' | 'onChange' | 'valueFormat' | 'dateParser'> & {
  /** Valor en formato API: "AAAA-MM-DD" o null. */
  value?: string | null;
  onChange?: (value: string | null) => void;
};

/**
 * Input de fecha del sistema: muestra y acepta dd/mm/aaaa (también d/m/aa).
 * Usar SIEMPRE este componente para fechas.
 */
export function DateInput({ value, onChange, ...props }: Props) {
  return (
    <MantineDateInput
      {...props}
      value={value ?? null}
      onChange={(next) => onChange?.(next)}
      valueFormat={DATE_FORMATS.date}
      dateParser={parseDateInput}
      placeholder={props.placeholder ?? 'dd/mm/aaaa'}
      clearable={props.clearable ?? true}
    />
  );
}
