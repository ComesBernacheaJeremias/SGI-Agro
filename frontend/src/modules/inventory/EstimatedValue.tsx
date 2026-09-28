/**
 * Producción propia valorizada por el costo de su ciclo: SOLO INFORMATIVO (ADR-012).
 * El stock contable la tiene a costo cero; este valor no se usa en costos ni en el resultado.
 */
import { Text, Tooltip } from '@mantine/core';

import { formatMoney } from '@/shared/format/number';

type Props = { value: string | number; provisional: boolean };

const HELP =
  'Según el costo de su ciclo (costo ÷ cosechado). Solo informativo: no es costo contable.';
const PROVISIONAL_HELP = ' Provisorio: el ciclo sigue en curso y el costo puede cambiar.';

/** "$ 2.000,00 costo del ciclo · provisorio" con la explicación al pasar el mouse. */
export function EstimatedValue({ value, provisional }: Props) {
  return (
    <Tooltip label={HELP + (provisional ? PROVISIONAL_HELP : '')} multiline w={280}>
      <span style={{ whiteSpace: 'nowrap' }}>
        {formatMoney(value)}{' '}
        <Text span size="xs" c="dimmed">
          {provisional ? 'costo del ciclo · provisorio' : 'costo del ciclo'}
        </Text>
      </span>
    </Tooltip>
  );
}
