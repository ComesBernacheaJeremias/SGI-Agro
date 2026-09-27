import { Loader, Tabs } from '@mantine/core';
import { useState } from 'react';

import type { ReportLink } from '@/modules/reports/api';
import { useReportCatalog } from '@/modules/reports/api';
import { LinkedRecord } from '@/modules/reports/LinkedRecord';
import { ReportView } from '@/modules/reports/ReportView';
import { PageHeader } from '@/shared/ui/PageHeader';

/** Pestañas de la pantalla: cada una es un reporte del catálogo (mismos filtros y exportación). */
const TABS = [
  { key: 'profitability', label: 'Rentabilidad' },
  { key: 'management_result', label: 'Resultado de gestión' },
  { key: 'plot_costs', label: 'Costos por lote' },
  { key: 'expenses', label: 'Gastos' },
  { key: 'product_margin', label: 'Margen por producto' },
];

export function CostsPage() {
  const { data: catalog } = useReportCatalog();
  const [link, setLink] = useState<ReportLink | null>(null);
  return (
    <>
      <PageHeader title="Costos y rentabilidad" />
      {!catalog && <Loader />}
      {catalog && (
        <Tabs defaultValue="profitability" keepMounted={false}>
          <Tabs.List mb="md">
            {TABS.map((t) => (
              <Tabs.Tab key={t.key} value={t.key}>
                {t.label}
              </Tabs.Tab>
            ))}
          </Tabs.List>
          {TABS.map((t) => {
            const info = catalog.find((r) => r.key === t.key);
            return (
              <Tabs.Panel key={t.key} value={t.key}>
                {info && <ReportView info={info} onOpenLink={setLink} />}
              </Tabs.Panel>
            );
          })}
        </Tabs>
      )}
      <LinkedRecord link={link} onClose={() => setLink(null)} />
    </>
  );
}
