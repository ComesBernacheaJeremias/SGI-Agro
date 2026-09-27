/** Alta que funciona sin conexión: si no hay red, queda en la cola y se envía después. */
import { notifications } from '@mantine/notifications';

import { isNetworkError, outbox, type OutboxKind } from './outbox';

type Submission<T> = {
  kind: OutboxKind;
  path: string;
  body: Record<string, unknown>;
  label: string;
  /** El envío normal (con el id ya incluido en el body). */
  send: (body: Record<string, unknown>) => Promise<T>;
};

export type SubmitResult<T> = { queued: true } | { queued: false; data: T };

export async function submitOrQueue<T>({
  kind,
  path,
  body,
  label,
  send,
}: Submission<T>): Promise<SubmitResult<T>> {
  const id = (body.id as string | undefined) ?? crypto.randomUUID();
  const withId = { ...body, id };
  const queue = async (): Promise<SubmitResult<T>> => {
    await outbox.add({ id, kind, path, body: withId, label });
    notifications.show({
      color: 'blue',
      title: 'Guardado sin conexión',
      message: `${label}: se va a enviar cuando vuelva la señal.`,
    });
    return { queued: true };
  };
  if (!navigator.onLine) return queue();
  try {
    return { queued: false, data: await send(withId) };
  } catch (err) {
    if (isNetworkError(err)) return queue();
    throw err;
  }
}
