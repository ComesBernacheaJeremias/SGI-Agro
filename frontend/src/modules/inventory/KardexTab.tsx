import { Group, Paper, ScrollArea, Select, Table, Text } from '@mantine/core';
import { useState } from 'react';

import { type Product, useActiveList, warehousesResource } from '@/modules/masterdata/api';
import { ProductSelect } from '@/modules/masterdata/ProductSelect';
import { DateInput } from '@/shared/components/DateInput';
import { formatDate } from '@/shared/format/date';
import { formatMoney, formatNumber } from '@/shared/format/number';

import { type DocumentType, useKardex } from './api';

type Props = {
  product: Product | null;
  onProductChange: (product: Product | null) => void;
  onOpenDocument: (id: string, type: DocumentType) => void;
};

/** Movimientos de un producto con saldo acumulado. */
export function KardexTab({ product, onProductChange, onOpenDocument }: Props) {
  const { data: warehouses = [] } = useActiveList(warehousesResource);
  const [warehouseId, setWarehouseId] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);

  const { data: kardex } = useKardex(
    product
      ? {
          product_id: product.id,
          warehouse_id: warehouseId ?? undefined,
          date_from: dateFrom ?? undefined,
          date_to: dateTo ?? undefined,
        }
      : null,
  );
  const qty = (value: string | number) =>
    `${formatNumber(value, 'quantity')} ${kardex?.unit ?? ''}`;

  return (
    <>
      <Group mb="sm" wrap="wrap">
        <ProductSelect
          placeholder="Elegí un producto"
          stockOnly
          value={product}
          onChange={onProductChange}
          w={{ base: '100%', sm: 320 }}
        />
        <Select
          placeholder="Todos los almacenes"
          data={warehouses.map((w) => ({ value: w.id, label: w.name }))}
          value={warehouseId}
          onChange={setWarehouseId}
          clearable
          w={200}
        />
        <DateInput placeholder="Desde" value={dateFrom} onChange={setDateFrom} w={140} />
        <DateInput placeholder="Hasta" value={dateTo} onChange={setDateTo} w={140} />
      </Group>

      {!product && <Text c="dimmed">Elegí un producto para ver sus movimientos.</Text>}
      {kardex && (
        <Paper withBorder>
          <ScrollArea>
            <Table striped highlightOnHover verticalSpacing="xs">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Fecha</Table.Th>
                  <Table.Th>Comprobante</Table.Th>
                  <Table.Th visibleFrom="sm">Almacén</Table.Th>
                  <Table.Th ta="right">Entrada</Table.Th>
                  <Table.Th ta="right">Salida</Table.Th>
                  <Table.Th ta="right">Saldo</Table.Th>
                  <Table.Th ta="right" visibleFrom="sm">
                    Costo unit.
                  </Table.Th>
                  <Table.Th ta="right" visibleFrom="sm">
                    Costo total
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Text size="sm" fw={500}>
                      Saldo inicial
                    </Text>
                  </Table.Td>
                  <Table.Td ta="right">{qty(kardex.opening_balance)}</Table.Td>
                  <Table.Td colSpan={2} visibleFrom="sm" />
                </Table.Tr>
                {kardex.rows.map((r) => {
                  const quantity = Number(r.quantity);
                  return (
                    <Table.Tr
                      key={`${r.document_id}-${r.warehouse.id}-${r.quantity}`}
                      onClick={() => onOpenDocument(r.document_id, r.document_type)}
                      style={{ cursor: 'pointer' }}
                    >
                      <Table.Td>{formatDate(r.date)}</Table.Td>
                      <Table.Td>{r.document_number}</Table.Td>
                      <Table.Td visibleFrom="sm">{r.warehouse.name}</Table.Td>
                      <Table.Td ta="right">{quantity > 0 ? qty(quantity) : ''}</Table.Td>
                      <Table.Td ta="right">{quantity < 0 ? qty(-quantity) : ''}</Table.Td>
                      <Table.Td ta="right" fw={500}>
                        {qty(r.balance)}
                      </Table.Td>
                      <Table.Td ta="right" visibleFrom="sm">
                        {formatMoney(r.unit_cost)}
                      </Table.Td>
                      <Table.Td ta="right" visibleFrom="sm">
                        {formatMoney(Math.abs(Number(r.total_cost)))}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </ScrollArea>
          {kardex.rows.length === 0 && (
            <Text c="dimmed" ta="center" py="md">
              Sin movimientos en el período.
            </Text>
          )}
        </Paper>
      )}
    </>
  );
}
