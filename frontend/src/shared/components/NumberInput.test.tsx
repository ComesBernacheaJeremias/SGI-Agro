import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';

import type { NumberKind } from '@/shared/format/number';

import { NumberInput } from './NumberInput';

function Harness({ kind }: { kind: NumberKind }) {
  const [value, setValue] = useState<string | null>(null);
  return (
    <MantineProvider env="test">
      <NumberInput label="Monto" kind={kind} value={value} onChange={setValue} />
      <output data-testid="api-value">{value ?? 'null'}</output>
    </MantineProvider>
  );
}

describe('NumberInput', () => {
  it('pone puntos de miles mientras se escribe y devuelve el valor en formato API', async () => {
    render(<Harness kind="quantity" />);
    const input = screen.getByLabelText('Monto');

    await userEvent.type(input, '1234567,891');

    expect(input).toHaveValue('1.234.567,891');
    expect(screen.getByTestId('api-value')).toHaveTextContent('1234567.891');
  });

  it('precio: no permite más de 2 decimales', async () => {
    render(<Harness kind="price" />);
    const input = screen.getByLabelText('Monto');

    await userEvent.type(input, '10000,999');

    expect(input).toHaveValue('10.000,99');
    expect(screen.getByTestId('api-value')).toHaveTextContent('10000.99');
  });
});
