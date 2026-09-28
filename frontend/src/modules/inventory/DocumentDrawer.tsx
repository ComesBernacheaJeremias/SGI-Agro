import {
  Alert,
  Badge,
  Button,
  Group,
  Select,
  SimpleGrid,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { useEffect } from 'react';

import { useCan } from '@/app/auth/session';
import {
  labelOf,
  partiesResource,
  productsResource,
  unitsResource,
  useActiveList,
  warehousesResource,
} from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';
import { useNewId } from '@/shared/crud/newId';

import {
  documentsApi,
  type DocumentType,
  fetchDocument,
  notifyStockAlerts,
  useInvalidateInventory,
  useInventoryOptions,
  useStock,
} from './api';
import { emptyLine, type LineValue } from './lines';
import { LinesField } from './LinesField';

type Values = {
  date: string | null;
  warehouse_id: string | null;
  target_warehouse_id: string | null;
  party_id: string | null;
  reference: string;
  reason: string;
  notes: string;
  lines: LineValue[];
};

const empty = (): Values => ({
  date: dayjs().format('YYYY-MM-DD'),
  warehouse_id: null,
  target_warehouse_id: null,
  party_id: null,
  reference: '',
  reason: '',
  notes: '',
  lines: [emptyLine()],
});

type Props = {
  /** null = comprobante nuevo del tipo `type` */
  documentId: string | null;
  type: DocumentType;
  opened: boolean;
  onClose: () => void;
};

export function DocumentDrawer({ documentId, type, opened, onClose }: Props) {
  const can = useCan();
  const newId = useNewId(opened);
  const invalidate = useInvalidateInventory();
  const { data: options } = useInventoryOptions();
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const { data: parties = [] } = useActiveList(partiesResource);
  const { data: units = [] } = useActiveList(unitsResource);

  const { data: document } = useQuery({
    queryKey: ['stock-documents', 'detail', documentId],
    queryFn: () => fetchDocument(documentId as string),
    enabled: opened && documentId !== null,
  });

  const isNew = documentId === null;
  const docType = document?.type ?? type;
  const isAdjustment = docType === 'adjustment';
  const writePermission = isAdjustment ? 'inventory:adjust' : 'inventory:write';
  const readOnly =
    !can(writePermission) ||
    (document !== undefined && (document.status === 'cancelled' || !document.is_manual));

  const form = useForm<Values>({
    initialValues: empty(),
    validate: {
      date: (v) => (v ? null : 'Obligatorio'),
      warehouse_id: (v) => (v ? null : 'Obligatorio'),
      target_warehouse_id: (v, values) =>
        docType !== 'transfer' || v
          ? v && v === values.warehouse_id
            ? 'Tiene que ser distinto del origen'
            : null
          : 'Obligatorio',
      reason: (v) => (isAdjustment && !v.trim() ? 'Indicá el motivo del ajuste' : null),
      lines: (lines) => {
        if (lines.length === 0) return 'Agregá al menos un producto';
        const incomplete = lines.some(
          (l) =>
            !l.product ||
            !l.unit_id ||
            l.quantity === null ||
            (!isAdjustment && Number(l.quantity) <= 0) ||
            (docType === 'manual_in' && l.unit_cost === null),
        );
        return incomplete
          ? 'Completá producto, unidad, cantidad y costo en todas las líneas'
          : null;
      },
    },
  });

  // Cargar valores: nuevo → vacío; existente → datos del comprobante (con productos completos)
  useEffect(() => {
    if (!opened) return;
    if (isNew) {
      form.setValues(empty());
      form.resetDirty();
      return;
    }
    if (!document) return;
    void Promise.all(document.lines.map((l) => productsResource.get(l.product.id))).then(
      (products) => {
        form.setValues({
          date: document.date,
          warehouse_id: document.warehouse.id,
          target_warehouse_id: document.target_warehouse?.id ?? null,
          party_id: document.party?.id ?? null,
          reference: document.reference,
          reason: document.reason,
          notes: document.notes,
          lines: document.lines.map((l, i) => ({
            key: crypto.randomUUID(),
            product: products[i] ?? null,
            unit_id: l.unit.id,
            quantity: l.quantity,
            unit_cost: l.unit_cost,
          })),
        });
        form.resetDirty();
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps -- al abrir o al llegar el comprobante
  }, [opened, isNew, document]);

  // Ajuste: stock según el sistema en el almacén elegido (a la fecha del ajuste)
  const { data: stock } = useStock({
    warehouse_id: form.values.warehouse_id ?? undefined,
    at: form.values.date ?? undefined,
    include_zero: true,
    page_size: 200,
  });
  const systemStock =
    isAdjustment && isNew && form.values.warehouse_id
      ? Object.fromEntries((stock?.items ?? []).map((r) => [r.product.id, Number(r.quantity)]))
      : undefined;

  async function submit(values: Values) {
    const body = {
      type: docType,
      date: values.date as string,
      warehouse_id: values.warehouse_id as string,
      target_warehouse_id: docType === 'transfer' ? values.target_warehouse_id : null,
      party_id: values.party_id,
      reference: values.reference,
      reason: values.reason,
      notes: values.notes,
      lines: values.lines.map((l) => ({
        product_id: l.product?.id ?? '',
        unit_id: l.unit_id as string,
        quantity: l.quantity ?? '0',
        unit_cost: docType === 'manual_in' ? l.unit_cost : null,
      })),
    };
    const saved = isNew
      ? await documentsApi.create({ ...body, id: newId })
      : await documentsApi.update(documentId, body);
    notifySuccess(`Comprobante ${saved.document.number} guardado.`);
    notifyStockAlerts(saved.alerts);
    await invalidate();
  }

  async function cancelDocument() {
    if (!document) return;
    const confirmed = await confirmAction({
      message: `Se va a anular el comprobante ${document.number}. El stock y los costos se recalculan.`,
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!confirmed) return;
    try {
      const result = await documentsApi.cancel(document.id);
      notifySuccess(`Comprobante ${document.number} anulado.`);
      notifyStockAlerts(result.alerts);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  const typeLabel = labelOf(options?.document_types, docType);
  const warehouseOptions = warehouses.map((w) => ({ value: w.id, label: w.name }));
  const canCancel =
    document?.status === 'active' &&
    document.is_manual &&
    can('inventory:cancel') &&
    can(writePermission);

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={isNew ? `Nuevo ${typeLabel.toLowerCase()}` : `${typeLabel} ${document?.number ?? ''}`}
      form={form}
      isEdit={!isNew}
      onSubmit={submit}
      readOnly={readOnly}
      size="xl"
      extraActions={
        document && (
          <>
            <HistoryButton table="stock_documents" recordId={document.id} />
            {canCancel && (
              <Button variant="subtle" color="red" onClick={cancelDocument}>
                Anular
              </Button>
            )}
          </>
        )
      }
    >
      {document?.status === 'cancelled' && (
        <Group>
          <Badge color="red">Anulado</Badge>
        </Group>
      )}
      {document && !document.is_manual && (
        <Alert variant="light">
          Este comprobante lo generó otro módulo: se modifica desde su origen.
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <DateInput label="Fecha" required disabled={readOnly} {...form.getInputProps('date')} />
        <Select
          label={docType === 'transfer' ? 'Almacén de origen' : 'Almacén'}
          required
          data={warehouseOptions}
          disabled={readOnly}
          {...form.getInputProps('warehouse_id')}
        />
        {docType === 'transfer' && (
          <Select
            label="Almacén de destino"
            required
            data={warehouseOptions}
            disabled={readOnly}
            {...form.getInputProps('target_warehouse_id')}
          />
        )}
        {(docType === 'manual_in' || docType === 'manual_out') && (
          <Select
            label={docType === 'manual_in' ? 'Proveedor' : 'Cliente / destinatario'}
            data={parties.map((p) => ({ value: p.id, label: p.name }))}
            searchable
            clearable
            disabled={readOnly}
            {...form.getInputProps('party_id')}
          />
        )}
        {!isAdjustment && (
          <TextInput
            label="Comprobante de referencia"
            placeholder="Ej.: Remito 0001-00001234"
            disabled={readOnly}
            {...form.getInputProps('reference')}
          />
        )}
        {isAdjustment && (
          <TextInput
            label="Motivo"
            required
            placeholder="Ej.: Conteo mensual, rotura, vencimiento"
            disabled={readOnly}
            {...form.getInputProps('reason')}
          />
        )}
      </SimpleGrid>
      <LinesField
        value={form.values.lines}
        onChange={(lines) => form.setFieldValue('lines', lines)}
        units={units}
        withCost={docType === 'manual_in'}
        systemStock={systemStock}
        readOnly={readOnly}
        error={form.errors.lines as string | undefined}
      />
      <Textarea
        label="Observaciones"
        autosize
        disabled={readOnly}
        {...form.getInputProps('notes')}
      />
    </EntityDrawer>
  );
}
