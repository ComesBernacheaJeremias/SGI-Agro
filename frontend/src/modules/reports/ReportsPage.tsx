import { Box, Flex, Loader, NavLink, Paper, Stack, Text } from '@mantine/core';
import { useState } from 'react';

import { PageHeader } from '@/shared/ui/PageHeader';

import { type ReportLink, useReportCatalog } from './api';
import { LinkedRecord } from './LinkedRecord';
import { ReportView } from './ReportView';

/** Catálogo de reportes (según permisos), agrupado por módulo. */
export function ReportsPage() {
  const { data: catalog } = useReportCatalog();
  const [key, setKey] = useState<string | null>(null);
  const [link, setLink] = useState<ReportLink | null>(null);
  const groups = [...new Set(catalog?.map((r) => r.group))];
  const selected = catalog?.find((r) => r.key === (key ?? catalog[0]?.key));
  return (
    <>
      <PageHeader title="Reportes" />
      {!catalog && <Loader />}
      {catalog && catalog.length === 0 && <Text c="dimmed">No tenés reportes disponibles.</Text>}
      {selected && (
        <Flex direction={{ base: 'column', sm: 'row' }} gap="md" align="flex-start">
          <Paper withBorder p="xs" w={{ base: '100%', sm: 220 }} style={{ flexShrink: 0 }}>
            <Stack gap={0}>
              {groups.map((group) => (
                <div key={group}>
                  <Text size="xs" fw={700} c="dimmed" tt="uppercase" px="sm" pt="sm" pb={4}>
                    {group}
                  </Text>
                  {(catalog ?? [])
                    .filter((r) => r.group === group)
                    .map((r) => (
                      <NavLink
                        key={r.key}
                        label={r.title}
                        active={r.key === selected.key}
                        onClick={() => setKey(r.key)}
                      />
                    ))}
                </div>
              ))}
            </Stack>
          </Paper>
          {/* minWidth 0: la tabla ancha hace scroll horizontal en vez de desbordar */}
          <Box w="100%" style={{ flex: 1, minWidth: 0 }}>
            <ReportView key={selected.key} info={selected} onOpenLink={setLink} withTitle />
          </Box>
        </Flex>
      )}
      <LinkedRecord link={link} onClose={() => setLink(null)} />
    </>
  );
}
