/**
 * Paleta del sistema ("Monte": verde bosque y terracota, ADR-025). Cada color se define por su
 * tono base y se generan los 10 tonos que usa Mantine (el base queda en el índice 6).
 * Pisan los colores de Mantine (red, green…) para que todo el sistema use la paleta.
 */
import type { MantineColorsTuple } from '@mantine/core';

const WHITE_MIX = [0.93, 0.84, 0.7, 0.54, 0.38, 0.19]; // tonos 0–5: mezcla con blanco
const BLACK_MIX = [0.16, 0.32, 0.48]; // tonos 7–9: mezcla con negro

function mix(hex: string, target: number, amount: number): string {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return `#${channels
    .map((c) =>
      Math.round(c + (target - c) * amount)
        .toString(16)
        .padStart(2, '0'),
    )
    .join('')}`;
}

/** Los 10 tonos de un color a partir del base (`#RRGGBB`). */
export function shades(base: string): MantineColorsTuple {
  return [
    ...WHITE_MIX.map((t) => mix(base, 255, t)),
    base,
    ...BLACK_MIX.map((t) => mix(base, 0, t)),
  ] as unknown as MantineColorsTuple;
}

export const FONT = 'IBM Plex Sans';

/** Tono base de cada color. El color se usa solo con significado (vencido, faltante…). */
export const COLORS = {
  brand: '#1F4D3A', // verde bosque (principal)
  green: '#2E6A4F',
  yellow: '#B8892F', // ámbar / ocre: faltantes, avisos
  orange: '#C4622D', // terracota
  red: '#A8432F', // ladrillo: vencido, negativo, error
  cyan: '#2C6670',
  blue: '#4A6072',
  grape: '#5F4B6E',
  gray: '#6A716C', // gris piedra
};

export const VARS = {
  /** Fondo de la aplicación (las tarjetas van en blanco) */
  bg: '#F4F5F2',
  text: '#1E2521',
  /** Texto secundario: verde apagado (en vez de gris claro) */
  muted: '#5B6B62',
  border: '#DDE1DC',
  /** Menú lateral, logo y panel del login, y su texto */
  panel: '#16362A',
  panelText: '#E9EFEA',
};
