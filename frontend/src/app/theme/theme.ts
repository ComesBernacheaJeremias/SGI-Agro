/** Tema de Mantine: un único lugar para colores, fuente y estilos por defecto (ADR-025). */
import {
  AppShell,
  Badge,
  createTheme,
  type CSSVariablesResolver,
  type MantineColorsTuple,
  Paper,
  Table,
  Title,
} from '@mantine/core';

import { COLORS, FONT, shades, VARS } from './palette';

const font = `'${FONT}', system-ui, -apple-system, 'Segoe UI', sans-serif`;

export const theme = createTheme({
  primaryColor: 'brand',
  primaryShade: 6,
  colors: Object.fromEntries(
    Object.entries(COLORS).map(([name, base]) => [name, shades(base)]),
  ) as Record<keyof typeof COLORS, MantineColorsTuple>,
  fontFamily: font,
  headings: { fontFamily: font, fontWeight: '700' },
  defaultRadius: 'md',
  components: {
    AppShell: AppShell.extend({ styles: { main: { background: 'var(--app-bg)' } } }),
    // Las etiquetas nunca se cortan ("ACTI…"): si no entran, la tabla hace scroll
    Badge: Badge.extend({
      styles: { root: { flexShrink: 0, overflow: 'visible' }, label: { overflow: 'visible' } },
    }),
    Paper: Paper.extend({ defaultProps: { radius: 'md' } }),
    Table: Table.extend({ defaultProps: { verticalSpacing: 'xs' } }),
    Title: Title.extend({ styles: { root: { letterSpacing: '-0.01em' } } }),
  },
});

/** Variables propias (`--app-*`) y texto secundario con el verde apagado de la paleta. */
export const cssVariables: CSSVariablesResolver = () => ({
  variables: {
    '--app-bg': VARS.bg,
    '--app-panel': VARS.panel,
    '--app-panel-text': VARS.panelText,
  },
  light: {
    '--mantine-color-text': VARS.text,
    '--mantine-color-dimmed': VARS.muted,
    '--mantine-color-default-border': VARS.border,
  },
  dark: {},
});
