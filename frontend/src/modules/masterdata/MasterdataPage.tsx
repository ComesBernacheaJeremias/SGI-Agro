import { Tabs } from '@mantine/core';

import { PageHeader } from '@/shared/ui/PageHeader';

import { CategoriesTab } from './CategoriesTab';
import { PartiesTab } from './PartiesTab';
import { ProductsTab } from './ProductsTab';
import { UnitsTab } from './UnitsTab';
import { WarehousesTab } from './WarehousesTab';

const TABS = [
  { value: 'products', label: 'Productos', content: <ProductsTab /> },
  { value: 'parties', label: 'Clientes y proveedores', content: <PartiesTab /> },
  { value: 'warehouses', label: 'Almacenes', content: <WarehousesTab /> },
  { value: 'categories', label: 'Categorías', content: <CategoriesTab /> },
  { value: 'units', label: 'Unidades', content: <UnitsTab /> },
];

export function MasterdataPage() {
  return (
    <>
      <PageHeader title="Maestros" />
      <Tabs defaultValue="products" keepMounted={false}>
        <Tabs.List mb="md">
          {TABS.map((tab) => (
            <Tabs.Tab key={tab.value} value={tab.value}>
              {tab.label}
            </Tabs.Tab>
          ))}
        </Tabs.List>
        {TABS.map((tab) => (
          <Tabs.Panel key={tab.value} value={tab.value}>
            {tab.content}
          </Tabs.Panel>
        ))}
      </Tabs>
    </>
  );
}
