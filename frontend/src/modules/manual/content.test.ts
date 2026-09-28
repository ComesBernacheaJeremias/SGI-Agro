import { describe, expect, it } from 'vitest';

import { MANUAL, searchManual, sectionForPath } from './content';

const titles = (query: string) => searchManual(query).flatMap((s) => s.topics.map((t) => t.title));

describe('searchManual', () => {
  it('sin texto devuelve todo el manual', () => {
    expect(searchManual('  ')).toBe(MANUAL);
  });

  it('busca sin importar tildes ni mayúsculas', () => {
    expect(titles('COSECHA')).toContain('Cargar una cosecha');
  });

  it('busca por comienzo de palabra', () => {
    expect(searchManual('inventario').length).toBeGreaterThan(0);
    expect(searchManual('ventario')).toEqual([]);
  });

  it('encuentra por sinónimos del campo', () => {
    expect(titles('fumigación')).toContain('Cargar una labor (aplicación, fertilización, poda…)');
    expect(titles('pulverizacion')).toContain(
      'Cargar una labor (aplicación, fertilización, poda…)',
    );
    expect(titles('remito')).toEqual(
      expect.arrayContaining(['Cargar una compra', 'Cargar una venta']),
    );
    expect(titles('gasoil')).toContain('Cargar un gasto (gasoil, reparación, servicio…)');
  });

  it('todas las palabras tienen que aparecer', () => {
    expect(searchManual('venta excel inexistentexyz')).toEqual([]);
  });
});

describe('manual', () => {
  it('títulos en infinitivo, sin preguntas', () => {
    const all = MANUAL.flatMap((s) => s.topics.map((t) => t.title));
    expect(all.filter((t) => t.includes('?'))).toEqual([]);
  });

  it('el "?" de cada pantalla abre su sección', () => {
    expect(sectionForPath('/produccion')).toBe('campo');
    expect(sectionForPath('/comercial')).toBe('plata');
    expect(sectionForPath('/')).toBe('numeros');
    expect(sectionForPath('/pantalla-sin-seccion')).toBeNull();
  });
});
