import { Select } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { formatDate } from '@/shared/format/date';
import { formatNumber } from '@/shared/format/number';

type Props = {
  productId: string;
  unitCode: string;
  warehouseId: string | null;
  date: string | null;
  /** Al editar una venta: su propio comprobante de stock no descuenta. */
  excludeDocumentId: string | null;
  /** Devolución (NC): todas las partidas del producto, aunque ya no tengan stock. */
  returning?: boolean;
  value: string | null;
  onChange: (batchId: string | null) => void;
  disabled?: boolean;
};

/** Partida de producción propia a vender (vacío = las más antiguas primero). */
export function BatchSelect({
  productId,
  unitCode,
  warehouseId,
  date,
  excludeDocumentId,
  returning = false,
  value,
  onChange,
  disabled,
}: Props) {
  const { data = [] } = useQuery({
    queryKey: ['stock', 'batches', productId, warehouseId, date, excludeDocumentId, returning],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/stock/batches', {
          params: {
            query: {
              product_id: productId,
              warehouse_id: warehouseId as string,
              at: date,
              exclude_document_id: excludeDocumentId,
              only_available: !returning,
            },
          },
        }),
      ),
    enabled: warehouseId !== null,
  });
  const options = data.map((b) => ({
    value: b.id,
    label: `${b.code} · ${formatDate(b.date)} · ${formatNumber(b.quantity, 'quantity')} ${unitCode}`,
  }));
  return (
    <Select
      label="Partida"
      placeholder={
        warehouseId ? (returning ? 'Sin partida' : 'Las más antiguas') : 'Elegí el almacén'
      }
      data={options}
      value={value}
      onChange={onChange}
      clearable
      disabled={disabled || !warehouseId}
      style={{ flex: '1 1 240px' }}
    />
  );
}
