import { Button, Menu, Tabs } from '@mantine/core';
import { IconChevronDown, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useCan } from '@/app/auth/session';
import { type Product, productsResource } from '@/modules/masterdata/api';
import { PageHeader } from '@/shared/ui/PageHeader';

import type { DocumentType } from './api';
import { DocumentDrawer } from './DocumentDrawer';
import { DocumentsTab } from './DocumentsTab';
import { KardexTab } from './KardexTab';
import { StockTab } from './StockTab';

const NEW_DOCUMENTS: { type: DocumentType; label: string; permission: string }[] = [
  { type: 'manual_in', label: 'Ingreso', permission: 'inventory:write' },
  { type: 'manual_out', label: 'Egreso', permission: 'inventory:write' },
  { type: 'transfer', label: 'Transferencia', permission: 'inventory:write' },
  { type: 'adjustment', label: 'Ajuste por conteo', permission: 'inventory:adjust' },
];

export function InventoryPage() {
  const can = useCan();
  const [tab, setTab] = useState<string | null>('stock');
  const [kardexProduct, setKardexProduct] = useState<Product | null>(null);
  const [drawer, setDrawer] = useState<{ id: string | null; type: DocumentType } | null>(null);

  const allowed = NEW_DOCUMENTS.filter((d) => can(d.permission));

  async function openKardex(productId: string) {
    setKardexProduct(await productsResource.get(productId));
    setTab('kardex');
  }

  return (
    <>
      <PageHeader
        title="Inventario"
        actions={
          allowed.length > 0 && (
            <Menu position="bottom-end">
              <Menu.Target>
                <Button
                  leftSection={<IconPlus size={16} />}
                  rightSection={<IconChevronDown size={14} />}
                >
                  Nuevo
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                {allowed.map((d) => (
                  <Menu.Item key={d.type} onClick={() => setDrawer({ id: null, type: d.type })}>
                    {d.label}
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
          )
        }
      />
      <Tabs value={tab} onChange={setTab} keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="stock">Stock</Tabs.Tab>
          <Tabs.Tab value="documents">Movimientos</Tabs.Tab>
          <Tabs.Tab value="kardex">Kardex</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="stock">
          <StockTab onOpenKardex={(id) => void openKardex(id)} />
        </Tabs.Panel>
        <Tabs.Panel value="documents">
          <DocumentsTab onOpen={(id, type) => setDrawer({ id, type })} />
        </Tabs.Panel>
        <Tabs.Panel value="kardex">
          <KardexTab
            product={kardexProduct}
            onProductChange={setKardexProduct}
            onOpenDocument={(id, type) => setDrawer({ id, type })}
          />
        </Tabs.Panel>
      </Tabs>
      <DocumentDrawer
        documentId={drawer?.id ?? null}
        type={drawer?.type ?? 'manual_in'}
        opened={drawer !== null}
        onClose={() => setDrawer(null)}
      />
    </>
  );
}
