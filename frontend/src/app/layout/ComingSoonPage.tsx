import { Stack, Text, Title } from '@mantine/core';

import type { NavItem } from '@/app/navigation';

/** Página provisoria para módulos que todavía no están implementados. */
export function ComingSoonPage({ item }: { item: NavItem }) {
  return (
    <Stack gap="xs">
      <Title order={2}>{item.label}</Title>
      <Text c="dimmed">Próximamente (etapa {item.stage}).</Text>
    </Stack>
  );
}
