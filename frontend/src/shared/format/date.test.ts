import { formatDate, parseDateInput } from './date';

describe('formatDate', () => {
  it('muestra dd/mm/aaaa', () => {
    expect(formatDate('2026-09-27')).toBe('27/09/2026');
    expect(formatDate('2026-01-05')).toBe('05/01/2026');
  });

  it('formatos de mes: mm/aaaa y mm/aa', () => {
    expect(formatDate('2026-09-27', 'month')).toBe('09/2026');
    expect(formatDate('2026-09-27', 'monthShort')).toBe('09/26');
  });

  it('vacío o inválido no se muestra', () => {
    expect(formatDate(null)).toBe('');
    expect(formatDate('no-es-fecha')).toBe('');
  });
});

describe('parseDateInput', () => {
  it('acepta dd/mm/aaaa, d/m/aa y ddmmaaaa', () => {
    expect(parseDateInput('27/09/2026')).toBe('2026-09-27');
    expect(parseDateInput('5/1/26')).toBe('2026-01-05');
    expect(parseDateInput('27092026')).toBe('2026-09-27');
  });

  it('rechaza fechas inexistentes o en formato estadounidense', () => {
    expect(parseDateInput('31/02/2026')).toBeNull();
    expect(parseDateInput('2026-09-27')).toBeNull();
    expect(parseDateInput('09/27/2026')).toBeNull();
  });
});
