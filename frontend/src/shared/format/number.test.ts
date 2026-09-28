import { formatMoney, formatNumber } from './number';

describe('formatNumber', () => {
  it('precios: puntos de miles, coma decimal y siempre 2 decimales', () => {
    expect(formatNumber(1234567.891, 'price')).toBe('1.234.567,89');
    expect(formatNumber('10000', 'price')).toBe('10.000,00');
    expect(formatNumber(1234, 'price')).toBe('1.234,00');
    expect(formatNumber(0.5, 'price')).toBe('0,50');
  });

  it('cantidades: 2 decimales y hasta 3 si hace falta', () => {
    expect(formatNumber(1234567.891, 'quantity')).toBe('1.234.567,891');
    expect(formatNumber('0.125', 'quantity')).toBe('0,125');
    expect(formatNumber(10, 'quantity')).toBe('10,00');
    expect(formatNumber('10.000', 'quantity')).toBe('10,00');
  });

  it('valores vacíos o inválidos no se muestran', () => {
    expect(formatNumber(null)).toBe('');
    expect(formatNumber('')).toBe('');
    expect(formatNumber('abc')).toBe('');
  });

  it('el cero nunca lleva signo menos', () => {
    expect(formatNumber(-0)).toBe('0,00');
    expect(formatNumber(-0.001)).toBe('0,00');
    expect(formatNumber(-1.5)).toBe('-1,50');
  });

  it('formatMoney agrega el signo $', () => {
    expect(formatMoney('10000')).toBe('$ 10.000,00');
    expect(formatMoney(null)).toBe('');
  });

  it('formatMoney pone el menos delante del $', () => {
    expect(formatMoney(-57500)).toBe('-$ 57.500,00');
    expect(formatMoney('-0.001')).toBe('$ 0,00');
  });
});
