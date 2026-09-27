import { ActionIcon, Badge, Button, Group, Popover, Stack, Text, Tooltip } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useQueryClient } from '@tanstack/react-query';
import { IconCloudOff, IconCloudUpload, IconTrash } from '@tabler/icons-react';
import { useCallback, useEffect, useState } from 'react';

import { useCan } from '@/app/auth/session';
import { assetsResource } from '@/modules/assets/api';
import { recipesResource } from '@/modules/manufacturing/api';
import {
  productsResource,
  unitsResource,
  useActiveList,
  warehousesResource,
} from '@/modules/masterdata/api';
import { operationTypesResource, useActiveCycles, useSeasons } from '@/modules/production/api';
import { formatDate } from '@/shared/format/date';

import { useOnline } from './network';
import { outbox, type OutboxItem, syncOutbox } from './outbox';

/** Consulta los maestros que usan los formularios sin conexión, así quedan guardados. */
function PrefetchProduction() {
  useActiveCycles();
  useSeasons();
  useActiveList(operationTypesResource);
  useActiveList(assetsResource);
  return null;
}

function PrefetchStock() {
  useActiveList(productsResource);
  useActiveList(unitsResource);
  useActiveList(warehousesResource);
  return null;
}

function PrefetchManufacturing() {
  useActiveList(recipesResource);
  return null;
}

function useOutbox(): OutboxItem[] {
  const [items, setItems] = useState<OutboxItem[]>([]);
  useEffect(() => {
    const load = () => void outbox.list().then(setItems);
    load();
    return outbox.subscribe(load);
  }, []);
  return items;
}

/** Barra superior: "Sin conexión" y pendientes de enviar; sincroniza al volver la señal. */
export function OfflineStatus() {
  const can = useCan();
  const online = useOnline();
  const items = useOutbox();
  const queryClient = useQueryClient();
  const pending = items.filter((i) => i.status === 'pending').length;
  const failed = items.filter((i) => i.status === 'error');

  const sync = useCallback(async () => {
    const sent = await syncOutbox();
    if (sent > 0) {
      notifications.show({
        color: 'green',
        title: 'Sincronizado',
        message: `Se enviaron ${sent} registros cargados sin conexión.`,
      });
      await queryClient.invalidateQueries();
    }
  }, [queryClient]);

  // Al volver la señal, al abrir la app y cada minuto mientras haya pendientes
  useEffect(() => {
    if (!online || pending === 0) return;
    void sync();
    const timer = window.setInterval(() => void sync(), 60_000);
    return () => window.clearInterval(timer);
  }, [online, pending, sync]);

  const prefetch = online && (
    <>
      {can('production:write') && <PrefetchProduction />}
      {(can('production:write') || can('inventory:write') || can('manufacturing:write')) && (
        <PrefetchStock />
      )}
      {can('manufacturing:write') && <PrefetchManufacturing />}
    </>
  );

  if (online && items.length === 0) return prefetch;
  return (
    <>
      {prefetch}
      <Popover position="bottom-end" width={360} shadow="md">
        <Popover.Target>
          <Group gap={4} style={{ cursor: 'pointer' }}>
            {!online && (
              <Badge color="gray" leftSection={<IconCloudOff size={12} />}>
                Sin conexión
              </Badge>
            )}
            {items.length > 0 && (
              <Badge
                color={failed.length ? 'red' : 'blue'}
                leftSection={<IconCloudUpload size={12} />}
              >
                {items.length} {items.length === 1 ? 'pendiente' : 'pendientes'}
              </Badge>
            )}
          </Group>
        </Popover.Target>
        <Popover.Dropdown>
          <Text fw={600} mb={4}>
            Carga sin conexión
          </Text>
          <Text size="xs" c="dimmed" mb="xs">
            {online
              ? 'Hay conexión: los pendientes se envían solos.'
              : 'Sin señal: podés cargar labores, cosechas, movimientos de stock y preparaciones; se envían al volver la conexión.'}
          </Text>
          <Stack gap={6}>
            {items.map((item) => (
              <Group key={item.id} justify="space-between" wrap="nowrap" align="flex-start">
                <div>
                  <Text size="sm">{item.label}</Text>
                  <Text size="xs" c={item.status === 'error' ? 'red' : 'dimmed'}>
                    {item.status === 'error'
                      ? item.error
                      : `Pendiente desde ${formatDate(item.createdAt, 'dateTime')}`}
                  </Text>
                </div>
                {item.status === 'error' && (
                  <Tooltip label="Descartar (cargalo de nuevo corregido)">
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      aria-label="Descartar"
                      onClick={() => void outbox.discard(item.id)}
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Tooltip>
                )}
              </Group>
            ))}
          </Stack>
          {online && pending > 0 && (
            <Button mt="sm" size="xs" fullWidth onClick={() => void sync()}>
              Enviar ahora
            </Button>
          )}
        </Popover.Dropdown>
      </Popover>
    </>
  );
}
