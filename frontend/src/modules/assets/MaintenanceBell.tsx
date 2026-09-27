import { ActionIcon, Indicator, Popover, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconTool } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

import { useCan } from '@/app/auth/session';

import { PLAN_STATE, planAlertText, useMaintenanceAlerts } from './api';

/** Campana de mantenimientos próximos o vencidos. */
export function MaintenanceBell() {
  const canRead = useCan()('assets:read');
  const navigate = useNavigate();
  const { data: alerts = [] } = useMaintenanceAlerts(canRead);
  if (!canRead) return null;
  const overdue = alerts.some((a) => a.state === 'overdue');
  return (
    <Popover position="bottom-end" width={360} shadow="md">
      <Popover.Target>
        <Indicator
          label={alerts.length}
          size={16}
          color={overdue ? 'red' : 'orange'}
          disabled={alerts.length === 0}
        >
          <ActionIcon variant="subtle" color="gray" aria-label="Mantenimientos">
            <IconTool size={20} />
          </ActionIcon>
        </Indicator>
      </Popover.Target>
      <Popover.Dropdown>
        <Text fw={600} mb="xs">
          Mantenimientos
        </Text>
        {alerts.length === 0 ? (
          <Text size="sm" c="dimmed">
            Todos los planes están al día.
          </Text>
        ) : (
          <Stack gap={6}>
            {alerts.map((a) => (
              <Text size="sm" key={a.plan.id} c={PLAN_STATE[a.state].color}>
                {planAlertText(a)}
              </Text>
            ))}
            <UnstyledButton onClick={() => navigate('/activos')}>
              <Text size="sm" c="green.8" fw={500}>
                Ver activos →
              </Text>
            </UnstyledButton>
          </Stack>
        )}
      </Popover.Dropdown>
    </Popover>
  );
}
