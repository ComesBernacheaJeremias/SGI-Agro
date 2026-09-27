/** Avisos y confirmaciones comunes a todo el sistema. */
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';

import { errorMessage } from '@/api/errors';

export function notifySuccess(message: string): void {
  notifications.show({ color: 'green', message });
}

export function notifyError(error: unknown): void {
  notifications.show({ color: 'red', title: 'No se pudo completar', message: errorMessage(error) });
}

type ConfirmOptions = {
  title?: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
};

/** "¿Estás seguro?": resuelve true si el usuario confirma. */
export function confirmAction({
  title = '¿Estás seguro?',
  message,
  confirmLabel = 'Confirmar',
  danger = false,
}: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    modals.openConfirmModal({
      title,
      children: message,
      labels: { confirm: confirmLabel, cancel: 'Cancelar' },
      confirmProps: { color: danger ? 'red' : undefined },
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
      onClose: () => resolve(false),
    });
  });
}
