import { Button, Drawer, Loader, Stack, Text, Timeline } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconHistory } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { formatAuditValue } from '@/shared/format/audit';
import { formatDate } from '@/shared/format/date';

const ACTION_LABELS: Record<string, string> = {
  create: 'Creó',
  update: 'Modificó',
  deactivate: 'Desactivó',
  activate: 'Reactivó',
  cancel: 'Anuló',
  delete: 'Eliminó',
};

type Props = { table: string; recordId: string };

/** Botón "Historial": muestra quién cambió qué y cuándo en un registro. */
export function HistoryButton({ table, recordId }: Props) {
  const [opened, { open, close }] = useDisclosure();

  const query = useQuery({
    queryKey: ['audit', table, recordId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/audit/records/{table}/{record_id}', {
          params: { path: { table, record_id: recordId }, query: { page_size: 200 } },
        }),
      ),
    enabled: opened,
  });

  return (
    <>
      <Button variant="subtle" leftSection={<IconHistory size={16} />} onClick={open}>
        Historial
      </Button>
      <Drawer opened={opened} onClose={close} title="Historial de cambios" position="right">
        {query.isLoading && <Loader />}
        {query.data && query.data.items.length === 0 && (
          <Text c="dimmed">Sin cambios registrados.</Text>
        )}
        <Timeline bulletSize={14} lineWidth={2}>
          {query.data?.items.map((entry) => (
            <Timeline.Item
              key={entry.id}
              title={`${ACTION_LABELS[entry.action] ?? entry.action} · ${entry.user_name ?? 'Sistema'}`}
            >
              <Text size="xs" c="dimmed">
                {formatDate(entry.at, 'dateTime')}
              </Text>
              <Stack gap={2} mt={4}>
                {entry.changes.map((change) => (
                  <Text size="sm" key={change.field}>
                    <b>{change.label}:</b>{' '}
                    {entry.action === 'create'
                      ? formatAuditValue(change.after)
                      : `${formatAuditValue(change.before)} → ${formatAuditValue(change.after)}`}
                  </Text>
                ))}
              </Stack>
            </Timeline.Item>
          ))}
        </Timeline>
      </Drawer>
    </>
  );
}
