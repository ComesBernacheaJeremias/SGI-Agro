import { Grid, Loader, NavLink, Paper, Stack, Text } from '@mantine/core';
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
        <Grid>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <Paper withBorder p="xs">
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
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 9 }}>
            <ReportView key={selected.key} info={selected} onOpenLink={setLink} withTitle />
          </Grid.Col>
        </Grid>
      )}
      <LinkedRecord link={link} onClose={() => setLink(null)} />
    </>
  );
}
