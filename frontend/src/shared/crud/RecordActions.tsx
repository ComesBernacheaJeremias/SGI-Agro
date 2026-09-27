import { Button } from '@mantine/core';
import type { ReactNode } from 'react';

import { HistoryButton } from './HistoryButton';
import { useResourceMutations } from './hooks';
import type { Entity, Resource } from './types';

type Props<T extends Entity & { is_active: boolean }, C, U> = {
  resource: Resource<T, C, U>;
  record: T;
  /** Nombre para mostrar en la confirmación ("Se va a desactivar …"). */
  name: string;
  canDeactivate: boolean;
  onClose: () => void;
  /** Acciones propias de la entidad (ej. resetear contraseña). */
  children?: ReactNode;
};

/** Acciones al pie del panel de un registro: Historial, [propias], Desactivar/Reactivar. */
export function RecordActions<T extends Entity & { is_active: boolean }, C, U>({
  resource,
  record,
  name,
  canDeactivate,
  onClose,
  children,
}: Props<T, C, U>) {
  const { toggleActive } = useResourceMutations(resource);
  return (
    <>
      <HistoryButton table={resource.table} recordId={record.id} />
      {children}
      {canDeactivate && resource.setActive && (
        <Button
          variant="subtle"
          color={record.is_active ? 'red' : 'green'}
          onClick={() => {
            onClose();
            void toggleActive(record.id, name, !record.is_active);
          }}
        >
          {record.is_active ? 'Desactivar' : 'Reactivar'}
        </Button>
      )}
    </>
  );
}
