import { Group, Paper, type PaperProps, Text } from '@mantine/core';
import type { ReactNode } from 'react';

type Props = PaperProps & {
  /** Título chico en mayúsculas */
  title?: string;
  /** A la derecha del título (ej. "Ver más") */
  action?: ReactNode;
  onClick?: () => void;
  children: ReactNode;
};

/**
 * Tarjeta de resumen (tablero, ciclos). Todas iguales: el color se usa solo con significado
 * (rojo vencido o negativo, ámbar faltantes), no para decorar.
 */
export function InfoCard({ title, action, onClick, children, style, ...props }: Props) {
  return (
    <Paper
      withBorder
      p="md"
      onClick={onClick}
      style={[onClick ? { cursor: 'pointer' } : undefined, style]}
      {...props}
    >
      {(title || action) && (
        <Group justify="space-between" mb="xs" wrap="nowrap">
          <Text size="xs" fw={700} tt="uppercase" c="dimmed" style={{ letterSpacing: '0.06em' }}>
            {title}
          </Text>
          {action}
        </Group>
      )}
      {children}
    </Paper>
  );
}
