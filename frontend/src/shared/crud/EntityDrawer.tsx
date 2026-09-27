import { Alert, Button, Drawer, Group, Stack } from '@mantine/core';
import type { UseFormReturnType } from '@mantine/form';
import { type ReactNode, useState } from 'react';

import { ApiError, errorMessage } from '@/api/errors';
import { confirmAction } from '@/shared/ui/feedback';

type Props<V extends Record<string, unknown>> = {
  opened: boolean;
  onClose: () => void;
  title: string;
  form: UseFormReturnType<V>;
  /** true = edición de un registro existente → pide confirmación antes de guardar. */
  isEdit: boolean;
  onSubmit: (values: V) => Promise<unknown>;
  children: ReactNode;
  /** Acciones extra al pie (historial, desactivar…). */
  extraActions?: ReactNode;
  /** Solo lectura: sin botón Guardar (ej. comprobante anulado). */
  readOnly?: boolean;
  size?: 'md' | 'lg' | 'xl';
};

type FieldError = { field: string; message: string };

/**
 * Panel lateral estándar para crear/editar un registro.
 * - Edición: "¿Estás seguro?" antes de guardar.
 * - Errores de la API: los de un campo se muestran en ese campo; el resto, arriba.
 */
export function EntityDrawer<V extends Record<string, unknown>>({
  opened,
  onClose,
  title,
  form,
  isEdit,
  onSubmit,
  children,
  extraActions,
  readOnly = false,
  size = 'md',
}: Props<V>) {
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function close() {
    setError(null);
    onClose();
  }

  async function handleSubmit(values: V) {
    setError(null);
    if (isEdit) {
      const confirmed = await confirmAction({ message: 'Se van a guardar los cambios.' });
      if (!confirmed) return;
    }
    setSaving(true);
    try {
      await onSubmit(values);
      close();
    } catch (err) {
      const fields =
        err instanceof ApiError ? (err.details.fields as FieldError[] | undefined) : undefined;
      if (fields?.length) {
        form.setErrors(Object.fromEntries(fields.map((f) => [f.field, f.message])));
      } else {
        setError(errorMessage(err));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Drawer opened={opened} onClose={close} title={title} position="right" size={size}>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack>
          {error && (
            <Alert color="red" variant="light">
              {error}
            </Alert>
          )}
          {children}
          <Group justify="space-between" mt="md">
            <Group gap="xs">{extraActions}</Group>
            <Group gap="xs">
              <Button variant="default" onClick={close}>
                {readOnly ? 'Cerrar' : 'Cancelar'}
              </Button>
              {!readOnly && (
                <Button type="submit" loading={saving}>
                  Guardar
                </Button>
              )}
            </Group>
          </Group>
        </Stack>
      </form>
    </Drawer>
  );
}
