import { Group, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

type Props = { title: string; subtitle?: ReactNode; actions?: ReactNode };

/** Título de pantalla (con subtítulo opcional) y acciones a la derecha. */
export function PageHeader({ title, subtitle, actions }: Props) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <div>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed">{subtitle}</Text>}
      </div>
      {actions && <Group gap="xs">{actions}</Group>}
    </Group>
  );
}
