import { NumberInput as MantineNumberInput, type NumberInputProps } from '@mantine/core';

import {
  DECIMAL_SEPARATOR,
  DECIMALS,
  type NumberKind,
  THOUSAND_SEPARATOR,
} from '@/shared/format/number';

type Props = Omit<
  NumberInputProps,
  | 'value'
  | 'onChange'
  | 'thousandSeparator'
  | 'decimalSeparator'
  | 'decimalScale'
  | 'fixedDecimalScale'
> & {
  /** price: siempre 2 decimales · quantity: hasta 3 decimales */
  kind?: NumberKind;
  /** Valor en formato API: "1234.56" (string decimal con punto) o null. */
  value?: string | null;
  onChange?: (value: string | null) => void;
};

/**
 * Input numérico del sistema: formatea mientras se escribe (1.234.567,89).
 * Usar SIEMPRE este componente para números; nunca el de Mantine directo.
 */
export function NumberInput({
  kind = 'price',
  value,
  onChange,
  allowNegative = false,
  ...props
}: Props) {
  const { max } = DECIMALS[kind];
  return (
    <MantineNumberInput
      {...props}
      value={value === null || value === undefined ? '' : Number(value)}
      onChange={(next) => onChange?.(next === '' ? null : String(next))}
      thousandSeparator={THOUSAND_SEPARATOR}
      decimalSeparator={DECIMAL_SEPARATOR}
      decimalScale={max}
      fixedDecimalScale={kind === 'price'}
      allowNegative={allowNegative}
      hideControls
      inputMode="decimal"
    />
  );
}
