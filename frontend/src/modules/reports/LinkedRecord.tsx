import { Fragment } from 'react';

import { useDocument, useMovement, usePayment } from '@/modules/commercial/api';
import { MovementDrawer } from '@/modules/commercial/CashTab';
import { DocumentDrawer } from '@/modules/commercial/DocumentDrawer';
import { PaymentDrawer } from '@/modules/commercial/PaymentDrawer';

import type { ReportLink } from './api';
import { CycleCostModal } from './CycleCostModal';

type Props = { link: ReportLink | null; onClose: () => void };

/** Abre el registro al que lleva una fila de un reporte (ciclo, comprobante, cobro, caja). */
export function LinkedRecord({ link, onClose }: Props) {
  const id = (kind: ReportLink['kind']) => (link?.kind === kind ? link.id : null);
  const { data: document } = useDocument(id('commercial_document'));
  const { data: payment } = usePayment(id('payment'));
  const { data: movement } = useMovement(id('cash_movement'));
  return (
    <Fragment key={link?.id ?? 'none'}>
      <CycleCostModal cycleId={id('cycle')} onClose={onClose} />
      {document && link?.kind === 'commercial_document' && (
        <DocumentDrawer
          direction={document.direction}
          documentId={document.id}
          opened
          onClose={onClose}
        />
      )}
      {payment && link?.kind === 'payment' && (
        <PaymentDrawer
          direction={payment.direction}
          paymentId={payment.id}
          opened
          onClose={onClose}
        />
      )}
      {movement && link?.kind === 'cash_movement' && (
        <MovementDrawer movement={movement} opened onClose={onClose} />
      )}
    </Fragment>
  );
}
