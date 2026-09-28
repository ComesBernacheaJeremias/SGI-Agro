import { ActionIcon, Indicator, Popover, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconBell } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

import { useCan } from '@/app/auth/session';

import { alertText, STOCK_ALERT_COLOR, useStockAlerts } from './api';

/** Campana de la barra superior: productos por debajo de su stock mínimo ("Necesitás comprar"). */
export function StockAlertsBell() {
  const canRead = useCan()('inventory:read');
  const navigate = useNavigate();
  const { data: alerts = [] } = useStockAlerts(canRead);

  if (!canRead) return null;
  return (
    <Popover position="bottom-end" width={340} shadow="md">
      <Popover.Target>
        <Indicator
          label={alerts.length}
          size={16}
          color={STOCK_ALERT_COLOR}
          disabled={alerts.length === 0}
        >
          <ActionIcon variant="subtle" color="gray" aria-label="Necesitás comprar">
            <IconBell size={20} />
          </ActionIcon>
        </Indicator>
      </Popover.Target>
      <Popover.Dropdown>
        <Text fw={600} mb="xs">
          Necesitás comprar
        </Text>
        {alerts.length === 0 ? (
          <Text size="sm" c="dimmed">
            Ningún producto por debajo del mínimo.
          </Text>
        ) : (
          <Stack gap={6}>
            {alerts.map((a) => (
              <Text size="sm" key={a.product.id}>
                {alertText(a)}
              </Text>
            ))}
            <UnstyledButton onClick={() => navigate('/inventario')}>
              <Text size="sm" c="brand.6" fw={500}>
                Ver stock →
              </Text>
            </UnstyledButton>
          </Stack>
        )}
      </Popover.Dropdown>
    </Popover>
  );
}
