import { Button, Tabs } from '@mantine/core';
import { Fragment, useState } from 'react';

import { useCan } from '@/app/auth/session';
import { PageHeader } from '@/shared/ui/PageHeader';

import type { Direction } from './api';
import { CashTab } from './CashTab';
import { ConfigTab } from './ConfigTab';
import { CurrentAccountsTab } from './CurrentAccountsTab';
import { DocumentDrawer } from './DocumentDrawer';
import { DocumentsTab, PaymentsTab } from './DocumentsTab';
import { PaymentDrawer } from './PaymentDrawer';

type Tab = 'purchases' | 'sales' | 'receipts' | 'payments' | 'accounts' | 'cash' | 'config';

/** Botón "Nuevo…" de cada pestaña. */
const NEW_ACTION: Partial<
  Record<Tab, { label: string; kind: 'document' | 'payment'; direction: Direction }>
> = {
  purchases: { label: 'Nueva compra', kind: 'document', direction: 'purchase' },
  sales: { label: 'Nueva venta', kind: 'document', direction: 'sale' },
  receipts: { label: 'Nuevo cobro', kind: 'payment', direction: 'sale' },
  payments: { label: 'Nuevo pago', kind: 'payment', direction: 'purchase' },
};

type DocumentState = { direction: Direction; id: string | null };
type PaymentState = { direction: Direction; id: string | null; partyId?: string };

export function CommercialPage() {
  const can = useCan();
  const canWrite = can('commercial:write');
  const canRead = can('commercial:read');
  const canCash = can('cash:read');
  const [tab, setTab] = useState<Tab>(canRead ? 'sales' : 'cash');
  const [document, setDocument] = useState<DocumentState | null>(null);
  const [payment, setPayment] = useState<PaymentState | null>(null);

  const action = NEW_ACTION[tab];
  function openNew() {
    if (!action) return;
    if (action.kind === 'document') setDocument({ direction: action.direction, id: null });
    else setPayment({ direction: action.direction, id: null });
  }

  return (
    <>
      <PageHeader
        title="Comercial y caja"
        actions={action && canWrite && <Button onClick={openNew}>{action.label}</Button>}
      />
      <Tabs value={tab} onChange={(v) => setTab((v ?? 'sales') as Tab)} keepMounted={false}>
        <Tabs.List mb="md">
          {canRead && (
            <>
              <Tabs.Tab value="sales">Ventas</Tabs.Tab>
              <Tabs.Tab value="receipts">Cobros</Tabs.Tab>
              <Tabs.Tab value="purchases">Compras y gastos</Tabs.Tab>
              <Tabs.Tab value="payments">Pagos</Tabs.Tab>
              <Tabs.Tab value="accounts">Cuentas corrientes</Tabs.Tab>
            </>
          )}
          {canCash && <Tabs.Tab value="cash">Caja y bancos</Tabs.Tab>}
          <Tabs.Tab value="config">Configuración</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="sales">
          <DocumentsTab
            direction="sale"
            onOpen={(d) => setDocument({ direction: 'sale', id: d.id })}
          />
        </Tabs.Panel>
        <Tabs.Panel value="receipts">
          <PaymentsTab
            direction="sale"
            onOpen={(p) => setPayment({ direction: 'sale', id: p.id })}
          />
        </Tabs.Panel>
        <Tabs.Panel value="purchases">
          <DocumentsTab
            direction="purchase"
            onOpen={(d) => setDocument({ direction: 'purchase', id: d.id })}
          />
        </Tabs.Panel>
        <Tabs.Panel value="payments">
          <PaymentsTab
            direction="purchase"
            onOpen={(p) => setPayment({ direction: 'purchase', id: p.id })}
          />
        </Tabs.Panel>
        <Tabs.Panel value="accounts">
          <CurrentAccountsTab
            canWrite={canWrite}
            onOpenDocument={(direction, id) => setDocument({ direction, id })}
            onOpenPayment={(direction, id, partyId) => setPayment({ direction, id, partyId })}
          />
        </Tabs.Panel>
        <Tabs.Panel value="cash">
          <CashTab />
        </Tabs.Panel>
        <Tabs.Panel value="config">
          <ConfigTab />
        </Tabs.Panel>
      </Tabs>
      {/* Los paneles se vuelven a montar en cada apertura (formulario limpio) */}
      <Fragment key={document ? `${document.direction}-${document.id ?? 'new'}` : 'closed'}>
        <DocumentDrawer
          direction={document?.direction ?? 'sale'}
          documentId={document?.id ?? null}
          opened={document !== null}
          onClose={() => setDocument(null)}
        />
      </Fragment>
      <Fragment key={payment ? `${payment.direction}-${payment.id ?? 'new'}` : 'closed'}>
        <PaymentDrawer
          direction={payment?.direction ?? 'sale'}
          paymentId={payment?.id ?? null}
          partyId={payment?.partyId}
          opened={payment !== null}
          onClose={() => setPayment(null)}
        />
      </Fragment>
    </>
  );
}
