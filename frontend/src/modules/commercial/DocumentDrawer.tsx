import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Paper,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import dayjs from 'dayjs';
import { useEffect } from 'react';

import { useCan } from '@/app/auth/session';
import { notifyStockAlerts } from '@/modules/inventory/api';
import {
  partiesResource,
  productsResource,
  unitsResource,
  useActiveList,
  warehousesResource,
} from '@/modules/masterdata/api';
import { DateInput } from '@/shared/components/DateInput';
import { NumberInput } from '@/shared/components/NumberInput';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { formatDate } from '@/shared/format/date';
import { formatMoney } from '@/shared/format/number';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import {
  type CommercialDocument,
  DIRECTION_TEXT,
  type Direction,
  documentsApi,
  type DocumentIn,
  expenseCategoriesResource,
  useCommercialOptions,
  useDocument,
  useDocuments,
  useInvalidateCommercial,
} from './api';
import { destinationValues } from './destination';
import { type DocLineValue, emptyDocLine, lineAmounts } from './documentLines';
import { DocumentLinesField } from './DocumentLinesField';

type Values = {
  kind: DocumentIn['kind'];
  has_invoice: boolean;
  letter: string | null;
  pos_number: string;
  number: string;
  party_id: string | null;
  date: string | null;
  due_date: string | null;
  warehouse_id: string | null;
  related_document_id: string | null;
  other_taxes: string | null;
  notes: string;
  lines: DocLineValue[];
};

const empty = (direction: Direction): Values => ({
  kind: 'invoice',
  has_invoice: direction === 'purchase',
  letter: direction === 'purchase' ? 'A' : null,
  pos_number: '',
  number: '',
  party_id: null,
  date: dayjs().format('YYYY-MM-DD'),
  due_date: null,
  warehouse_id: null,
  related_document_id: null,
  other_taxes: null,
  notes: '',
  lines: [emptyDocLine('product')],
});

const LETTERS = ['A', 'B', 'C', 'M', 'E'];

async function toValues(doc: CommercialDocument): Promise<Values> {
  const products = await Promise.all(
    doc.lines.map((l) => (l.product ? productsResource.get(l.product.id) : null)),
  );
  return {
    kind: doc.kind,
    has_invoice: doc.has_invoice,
    letter: doc.letter || null,
    pos_number: doc.pos_number,
    number: doc.number,
    party_id: doc.party.id,
    date: doc.date,
    due_date: doc.due_date,
    warehouse_id: doc.warehouse?.id ?? null,
    related_document_id: doc.related_document?.id ?? null,
    other_taxes: doc.other_taxes,
    notes: doc.notes,
    lines: doc.lines.map((l, i) => ({
      key: crypto.randomUUID(),
      kind: l.kind,
      product: products[i] ?? null,
      unit_id: l.unit?.id ?? null,
      quantity: l.quantity,
      batch_id: l.batch_id,
      description: l.description,
      expense_category_id: l.expense_category?.id ?? null,
      destination: destinationValues(l.destination),
      unit_price: l.unit_price,
      vat_rate: String(Number(l.vat_rate)),
    })),
  };
}

type Props = {
  direction: Direction;
  /** null = comprobante nuevo */
  documentId: string | null;
  opened: boolean;
  onClose: () => void;
};

export function DocumentDrawer({ direction, documentId, opened, onClose }: Props) {
  const can = useCan();
  const text = DIRECTION_TEXT[direction];
  const invalidate = useInvalidateCommercial();
  const { data: options } = useCommercialOptions();
  const { data: parties = [] } = useActiveList(partiesResource);
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const { data: units = [] } = useActiveList(unitsResource);
  const { data: categories = [] } = useActiveList(expenseCategoriesResource);
  const { data: document } = useDocument(opened ? documentId : null);

  const isNew = documentId === null;
  const readOnly = !can('commercial:write') || document?.status === 'cancelled';

  const form = useForm<Values>({
    initialValues: empty(direction),
    validate: {
      party_id: (v) => (v ? null : 'Obligatorio'),
      date: (v) => (v ? null : 'Obligatorio'),
      letter: (v, values) => (values.has_invoice && !v ? 'Obligatorio' : null),
      pos_number: (v, values) => (values.has_invoice && !v.trim() ? 'Obligatorio' : null),
      number: (v, values) => (values.has_invoice && !v.trim() ? 'Obligatorio' : null),
      warehouse_id: (v, values) =>
        !v && values.lines.some((l) => l.kind === 'product') ? 'Obligatorio con productos' : null,
      lines: (lines) => {
        if (lines.length === 0) return 'Agregá al menos una línea';
        const incomplete = lines.some(
          (l) =>
            l.unit_price === null ||
            (l.kind === 'product' && (!l.product || !l.unit_id || !Number(l.quantity))) ||
            (l.kind === 'expense' && direction === 'purchase' && !l.expense_category_id) ||
            (l.kind === 'expense' && direction === 'sale' && !l.description.trim()),
        );
        return incomplete ? 'Completá todos los datos de cada línea' : null;
      },
    },
  });

  useEffect(() => {
    if (!opened) return;
    if (isNew) {
      form.setValues(empty(direction));
      form.resetDirty();
      return;
    }
    if (!document) return;
    void toValues(document).then((values) => {
      form.setValues(values);
      form.resetDirty();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- al abrir o al llegar el comprobante
  }, [opened, isNew, document]);

  const values = form.values;
  const amounts = values.lines.map(lineAmounts);
  const net = amounts.reduce((s, a) => s + a.net, 0);
  const vat = amounts.reduce((s, a) => s + a.vat, 0);
  const total = net + vat + Number(values.other_taxes ?? 0);

  async function submit(v: Values) {
    const body: DocumentIn = {
      direction,
      kind: v.kind,
      has_invoice: v.has_invoice,
      letter: v.has_invoice ? (v.letter ?? '') : '',
      pos_number: v.has_invoice ? v.pos_number : '',
      number: v.has_invoice ? v.number : '',
      party_id: v.party_id as string,
      date: v.date as string,
      due_date: v.due_date,
      warehouse_id: v.lines.some((l) => l.kind === 'product') ? v.warehouse_id : null,
      related_document_id: v.kind === 'invoice' ? null : v.related_document_id,
      other_taxes: v.other_taxes ?? '0',
      notes: v.notes,
      lines: v.lines.map((l) => ({
        kind: l.kind,
        description: l.description,
        product_id: l.product?.id ?? null,
        unit_id: l.kind === 'product' ? l.unit_id : null,
        quantity: l.quantity ?? '1',
        batch_id: l.kind === 'product' ? l.batch_id : null,
        expense_category_id: l.kind === 'expense' ? l.expense_category_id : null,
        ...(l.kind === 'expense' ? l.destination : {}),
        unit_price: l.unit_price ?? '0',
        vat_rate: l.vat_rate,
      })),
    };
    const saved = isNew
      ? await documentsApi.create(body)
      : await documentsApi.update(documentId, body);
    notifySuccess(`${text.document} ${saved.document.invoice_label} guardada.`);
    notifyStockAlerts(saved.alerts);
    await invalidate();
  }

  async function cancelDocument() {
    if (!document) return;
    const confirmed = await confirmAction({
      message: `Se va a anular ${document.invoice_label}. Se revierte el stock y se liberan los ${text.payments.toLowerCase()} imputados.`,
      confirmLabel: 'Anular',
      danger: true,
    });
    if (!confirmed) return;
    try {
      const result = await documentsApi.cancel(document.id);
      notifySuccess(`${document.invoice_label} anulada.`);
      notifyStockAlerts(result.alerts);
      await invalidate();
      onClose();
    } catch (err) {
      notifyError(err);
    }
  }

  const { data: partyDocuments } = useDocuments(
    { direction, party_id: values.party_id, status: 'active', page_size: 200 },
    opened && values.kind !== 'invoice' && values.party_id !== null,
  );
  const relatedOptions = (partyDocuments?.items ?? [])
    .filter((d) => d.kind !== 'credit_note' && d.id !== documentId)
    .map((d) => ({
      value: d.id,
      label: `${d.invoice_label} · ${formatDate(d.date)} · ${formatMoney(d.total)}`,
    }));
  const partyOptions = parties
    .filter((p) => (direction === 'sale' ? p.is_customer : p.is_supplier))
    .map((p) => ({ value: p.id, label: p.name }));
  const hasProducts = values.lines.some((l) => l.kind === 'product');
  const canCancel =
    document?.status === 'active' && can('commercial:cancel') && can('commercial:write');

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={isNew ? `Nueva ${text.document.toLowerCase()}` : (document?.invoice_label ?? '')}
      form={form}
      isEdit={!isNew}
      onSubmit={submit}
      readOnly={readOnly}
      size="xl"
      extraActions={
        document && (
          <>
            <HistoryButton table="commercial_documents" recordId={document.id} />
            {canCancel && (
              <Button variant="subtle" color="red" onClick={cancelDocument}>
                Anular
              </Button>
            )}
          </>
        )
      }
    >
      {document && (
        <Group gap="xs">
          <Text size="sm" c="dimmed">
            {document.internal_number}
          </Text>
          {document.status === 'cancelled' && <Badge color="red">Anulada</Badge>}
          {document.status === 'active' && document.kind !== 'credit_note' && (
            <Badge color={Number(document.pending) > 0 ? 'orange' : 'green'} variant="light">
              {Number(document.pending) > 0
                ? `Pendiente ${formatMoney(document.pending)}`
                : direction === 'sale'
                  ? 'Cobrada'
                  : 'Pagada'}
            </Badge>
          )}
        </Group>
      )}
      <SegmentedControl
        data={options?.document_kinds ?? []}
        disabled={readOnly}
        {...form.getInputProps('kind')}
      />
      {values.kind !== 'invoice' && values.party_id && (
        <Select
          label="Comprobante asociado"
          description={
            values.kind === 'credit_note'
              ? 'Opcional. La nota de crédito baja lo pendiente de ese comprobante; si ya estaba pagado, queda a favor.'
              : 'Opcional: el comprobante que corrige.'
          }
          placeholder="Ninguno"
          data={relatedOptions}
          searchable
          clearable
          disabled={readOnly}
          {...form.getInputProps('related_document_id')}
        />
      )}
      {values.kind === 'debit_note' && (
        <Alert variant="light">
          La nota de débito no mueve mercadería: cargá conceptos (intereses, diferencias de
          precio…).
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Select
          label={text.party}
          required
          data={partyOptions}
          searchable
          disabled={readOnly}
          {...form.getInputProps('party_id')}
        />
        <DateInput label="Fecha" required disabled={readOnly} {...form.getInputProps('date')} />
      </SimpleGrid>
      <Checkbox
        label="Con factura"
        disabled={readOnly}
        {...form.getInputProps('has_invoice', { type: 'checkbox' })}
      />
      {values.has_invoice && (
        <SimpleGrid cols={3}>
          <Select
            label="Letra"
            required
            data={LETTERS}
            disabled={readOnly}
            {...form.getInputProps('letter')}
          />
          <TextInput
            label="Punto de venta"
            required
            maxLength={5}
            placeholder="00001"
            disabled={readOnly}
            {...form.getInputProps('pos_number')}
          />
          <TextInput
            label="Número"
            required
            maxLength={8}
            placeholder="00001234"
            disabled={readOnly}
            {...form.getInputProps('number')}
          />
        </SimpleGrid>
      )}
      {!values.has_invoice && isNew && (
        <Text size="xs" c="dimmed">
          Sin factura: se identifica con el número interno ({direction === 'sale' ? 'VTA' : 'CPR'}
          -000001…).
        </Text>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <DateInput
          label="Vencimiento"
          description={isNew ? 'Vacío: fecha + días de pago del tercero' : undefined}
          disabled={readOnly}
          {...form.getInputProps('due_date')}
        />
        {hasProducts && (
          <Select
            label={direction === 'sale' ? 'Sale del almacén' : 'Entra al almacén'}
            required
            data={warehouses.map((w) => ({ value: w.id, label: w.name }))}
            disabled={readOnly}
            {...form.getInputProps('warehouse_id')}
          />
        )}
      </SimpleGrid>
      <DocumentLinesField
        direction={direction}
        value={values.lines}
        onChange={(lines) => form.setFieldValue('lines', lines)}
        units={units}
        categories={categories}
        batch={
          direction === 'sale' && values.kind !== 'debit_note'
            ? {
                warehouseId: values.warehouse_id,
                date: values.date,
                stockDocumentId: document?.stock_document_id ?? null,
                returning: values.kind === 'credit_note',
              }
            : undefined
        }
        readOnly={readOnly}
        error={form.errors.lines as string | undefined}
      />
      <Paper withBorder p="sm">
        <Stack gap={4}>
          <Group justify="space-between">
            <Text size="sm">Neto</Text>
            <Text size="sm">{formatMoney(net)}</Text>
          </Group>
          <Group justify="space-between">
            <Text size="sm">IVA</Text>
            <Text size="sm">{formatMoney(vat)}</Text>
          </Group>
          <Group justify="space-between" align="center">
            <Text size="sm">Percepciones y otros impuestos</Text>
            <NumberInput
              kind="price"
              leftSection="$"
              size="xs"
              w={150}
              disabled={readOnly}
              {...form.getInputProps('other_taxes')}
            />
          </Group>
          <Group justify="space-between">
            <Text fw={700}>Total</Text>
            <Text fw={700}>{formatMoney(total)}</Text>
          </Group>
        </Stack>
      </Paper>
      <Textarea
        label="Observaciones"
        autosize
        disabled={readOnly}
        {...form.getInputProps('notes')}
      />
    </EntityDrawer>
  );
}
