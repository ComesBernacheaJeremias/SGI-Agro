import { Button, Group, Tabs } from '@mantine/core';
import { IconPlant2, IconPlus, IconTractor } from '@tabler/icons-react';
import { useState } from 'react';

import { useCan } from '@/app/auth/session';
import { PageHeader } from '@/shared/ui/PageHeader';

import type { Cycle } from './api';
import { ConfigTab } from './ConfigTab';
import { CycleDrawer } from './CycleDrawer';
import { CyclesTab } from './CyclesTab';
import { FieldBookModal } from './FieldBookModal';
import { OperationDrawer } from './OperationDrawer';
import { OperationsTab } from './OperationsTab';

type OperationState = { id: string | null; harvest: boolean; cycleId?: string };

export function ProductionPage() {
  const can = useCan();
  const canWrite = can('production:write');
  const [cycle, setCycle] = useState<{ record: Cycle | null } | null>(null);
  const [fieldBook, setFieldBook] = useState<Cycle | null>(null);
  const [operation, setOperation] = useState<OperationState | null>(null);

  return (
    <>
      <PageHeader
        title="Producción"
        actions={
          canWrite && (
            <Group gap="xs">
              <Button
                leftSection={<IconTractor size={16} />}
                onClick={() => setOperation({ id: null, harvest: false })}
              >
                Cargar labor
              </Button>
              <Button
                variant="light"
                leftSection={<IconPlant2 size={16} />}
                onClick={() => setOperation({ id: null, harvest: true })}
              >
                Cargar cosecha
              </Button>
              <Button
                variant="default"
                leftSection={<IconPlus size={16} />}
                onClick={() => setCycle({ record: null })}
              >
                Abrir ciclo
              </Button>
            </Group>
          )
        }
      />
      <Tabs defaultValue="cycles" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="cycles">Ciclos</Tabs.Tab>
          <Tabs.Tab value="operations">Labores</Tabs.Tab>
          <Tabs.Tab value="config">Configuración</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="cycles">
          <CyclesTab onOpen={(record) => setCycle({ record })} />
        </Tabs.Panel>
        <Tabs.Panel value="operations">
          <OperationsTab onOpen={(o) => setOperation({ id: o.id, harvest: o.is_harvest })} />
        </Tabs.Panel>
        <Tabs.Panel value="config">
          <ConfigTab />
        </Tabs.Panel>
      </Tabs>

      <CycleDrawer
        cycle={cycle?.record ?? null}
        opened={cycle !== null}
        onClose={() => setCycle(null)}
        onOpenFieldBook={(c) => setFieldBook(c)}
      />
      <FieldBookModal
        cycle={fieldBook}
        onClose={() => setFieldBook(null)}
        onOpenOperation={(id) => setOperation({ id, harvest: false })}
      />
      <OperationDrawer
        operationId={operation?.id ?? null}
        harvest={operation?.harvest ?? false}
        defaultCycleId={operation?.cycleId}
        opened={operation !== null}
        onClose={() => setOperation(null)}
      />
    </>
  );
}
