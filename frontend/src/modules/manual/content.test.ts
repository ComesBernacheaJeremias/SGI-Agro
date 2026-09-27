import { describe, expect, it } from 'vitest';

import { MANUAL, searchManual } from './content';

describe('searchManual', () => {
  it('sin texto devuelve todo el manual', () => {
    expect(searchManual('  ')).toBe(MANUAL);
  });

  it('busca sin importar tildes ni mayúsculas', () => {
    const questions = searchManual('COSECHA').flatMap((s) => s.topics.map((t) => t.question));
    expect(questions).toContain('Cargar una cosecha');
  });

  it('todas las palabras tienen que aparecer', () => {
    expect(searchManual('venta excel inexistentexyz')).toEqual([]);
  });
});
