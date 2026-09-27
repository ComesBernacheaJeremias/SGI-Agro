import { Alert, Button, Group, LoadingOverlay, Stack, Table, Text, Title } from '@mantine/core';
import { IconFileSpreadsheet, IconFileTypePdf } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { useState } from 'react';

import { useSeasons } from '@/modules/production/api';
import { notifyError } from '@/shared/ui/feedback';

import {
  downloadReport,
  formatCell,
  type ReportInfo,
  type ReportLink,
  type ReportParams,
  type TableReport,
  useReport,
} from './api';
import { FILTER_RESOURCES } from './filters';
import { ReportFilters } from './ReportFilters';

const NUMERIC = new Set(['money', 'quantity', 'percent']);
const ROW_BG = {
  normal: undefined,
  subtotal: 'var(--mantine-color-default-hover)',
  total: 'var(--mantine-color-green-light)',
};

/** Tabla de un reporte: formato por tipo de columna, subtotales, sangría y fila de totales. */
export function ReportTable({
  report,
  onOpenLink,
}: {
  report: TableReport;
  onOpenLink?: (link: ReportLink) => void;
}) {
  const align = (kind: string) => (NUMERIC.has(kind) ? 'right' : 'left');
  return (
    <Table.ScrollContainer minWidth={Math.min(report.columns.length * 130, 1200)}>
      <Table highlightOnHover={Boolean(onOpenLink)} striped={false} verticalSpacing={6}>
        <Table.Thead>
          <Table.Tr>
            {report.columns.map((c) => (
              <Table.Th key={c.key} ta={align(c.kind)}>
                {c.label}
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {report.rows.map((row, i) => {
            const clickable = Boolean(row.link && onOpenLink);
            return (
              <Table.Tr
                key={i}
                bg={ROW_BG[row.style ?? 'normal']}
                fw={row.style && row.style !== 'normal' ? 700 : undefined}
                style={clickable ? { cursor: 'pointer' } : undefined}
                onClick={clickable ? () => onOpenLink?.(row.link as ReportLink) : undefined}
              >
                {report.columns.map((c, j) => (
                  <Table.Td
                    key={c.key}
                    ta={align(c.kind)}
                    pl={j === 0 && row.indent ? `calc(${row.indent} * 1.5rem)` : undefined}
                    c={NUMERIC.has(c.kind) && Number(row.cells[c.key]) < 0 ? 'red' : undefined}
                  >
                    {formatCell(row.cells[c.key], c.kind)}
                  </Table.Td>
                ))}
              </Table.Tr>
            );
          })}
        </Table.Tbody>
        {report.totals && (
          <Table.Tfoot>
            <Table.Tr bg={ROW_BG.total}>
              {report.columns.map((c, j) => (
                <Table.Th key={c.key} ta={align(c.kind)}>
                  {j === 0 ? 'Total' : formatCell(report.totals?.[c.key], c.kind)}
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Tfoot>
        )}
      </Table>
    </Table.ScrollContainer>
  );
}

/** Valores iniciales: las opciones por defecto y, si hay período, la temporada actual. */
function useDefaults(info: ReportInfo): ReportParams {
  const { data: seasons = [] } = useSeasons();
  const today = dayjs().format('YYYY-MM-DD');
  const defaults: ReportParams = {};
  for (const f of info.filters) {
    if (f.kind === 'choice' && f.name) defaults[f.name] = f.default ?? null;
    if (f.kind === 'period') {
      defaults.season_id =
        seasons.find((s) => s.start_date <= today && s.end_date >= today)?.id ?? null;
    }
  }
  return defaults;
}

type Props = {
  info: ReportInfo;
  onOpenLink?: (link: ReportLink) => void;
  /** Mostrar título y descripción (en la pantalla Reportes sí; en pestañas no). */
  withTitle?: boolean;
};

/** Un reporte completo: filtros, tabla y exportación a Excel/PDF. */
export function ReportView({ info, onOpenLink, withTitle = false }: Props) {
  const defaults = useDefaults(info);
  const [chosen, setChosen] = useState<ReportParams>({});
  const params = { ...defaults, ...chosen };
  const missing = info.filters.filter(
    (f) => f.required && !params[FILTER_RESOURCES[f.kind]?.param ?? ''],
  );
  const { data, isFetching, error } = useReport(info.key, params, missing.length === 0);
  const [exporting, setExporting] = useState<'xlsx' | 'pdf' | null>(null);

  async function exportAs(format: 'xlsx' | 'pdf') {
    setExporting(format);
    try {
      await downloadReport(info.key, params, format);
    } catch (err) {
      notifyError(err);
    } finally {
      setExporting(null);
    }
  }

  return (
    <Stack gap="xs" pos="relative">
      {withTitle && (
        <div>
          <Title order={3}>{info.title}</Title>
          <Text size="sm" c="dimmed">
            {info.description}
          </Text>
        </div>
      )}
      <ReportFilters
        filters={info.filters}
        values={params}
        onChange={(patch) => setChosen((current) => ({ ...current, ...patch }))}
      />
      {missing.length > 0 && (
        <Text c="dimmed">Elegí: {missing.map((f) => f.label.toLowerCase()).join(', ')}.</Text>
      )}
      {error && <Alert color="red">{error.message}</Alert>}
      {data && missing.length === 0 && (
        <>
          <Group justify="space-between" wrap="wrap">
            <div>
              <Text fw={600}>{data.title}</Text>
              <Text size="sm" c="dimmed">
                {data.subtitle}
              </Text>
            </div>
            <Group gap="xs">
              <Button
                variant="light"
                size="xs"
                leftSection={<IconFileSpreadsheet size={16} />}
                loading={exporting === 'xlsx'}
                onClick={() => exportAs('xlsx')}
              >
                Excel
              </Button>
              <Button
                variant="light"
                size="xs"
                color="red"
                leftSection={<IconFileTypePdf size={16} />}
                loading={exporting === 'pdf'}
                onClick={() => exportAs('pdf')}
              >
                PDF
              </Button>
            </Group>
          </Group>
          <div style={{ position: 'relative' }}>
            <LoadingOverlay visible={isFetching} />
            {data.rows.length === 0 ? (
              <Text c="dimmed">Sin datos para los filtros elegidos.</Text>
            ) : (
              <ReportTable report={data} onOpenLink={onOpenLink} />
            )}
          </div>
          {data.notes?.map((note) => (
            <Text key={note} size="xs" c="dimmed">
              {note}
            </Text>
          ))}
        </>
      )}
    </Stack>
  );
}
