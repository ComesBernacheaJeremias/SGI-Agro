import { Alert, Button, Group, PasswordInput, Stack, Text } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useState } from 'react';

import { errorMessage } from '@/api/errors';
import { notifySuccess } from '@/shared/ui/feedback';

import { resetPassword } from './api';

const MIN_PASSWORD = 10;

type Props = { userId: string; onDone: () => void };

/** Asignar una contraseña nueva a otro usuario (se le cierran las sesiones abiertas). */
export function ResetPasswordForm({ userId, onDone }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const form = useForm({
    initialValues: { password: '', repeat: '' },
    validate: {
      password: (v) => (v.length >= MIN_PASSWORD ? null : `Mínimo ${MIN_PASSWORD} caracteres`),
      repeat: (v, values) => (v === values.password ? null : 'Las contraseñas no coinciden'),
    },
  });

  async function submit({ password }: { password: string }) {
    setSaving(true);
    setError(null);
    try {
      await resetPassword(userId, password);
      notifySuccess('Contraseña actualizada. El usuario deberá volver a ingresar.');
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={form.onSubmit(submit)}>
      <Stack>
        <Text size="sm" c="dimmed">
          Se cerrarán todas las sesiones abiertas de este usuario.
        </Text>
        {error && <Alert color="red">{error}</Alert>}
        <PasswordInput label="Contraseña nueva" required {...form.getInputProps('password')} />
        <PasswordInput label="Repetir contraseña" required {...form.getInputProps('repeat')} />
        <Group justify="flex-end">
          <Button type="submit" loading={saving}>
            Guardar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
