import { Group, Title } from '@mantine/core';
import type { ReactNode } from 'react';

/** Título de pantalla con acciones a la derecha (ej. botón "Nuevo"). */
export function PageHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <Group justify="space-between" mb="md" wrap="wrap">
      <Title order={2}>{title}</Title>
      {actions && <Group gap="xs">{actions}</Group>}
    </Group>
  );
}
