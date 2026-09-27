import { Alert, Button, Group, Paper, PasswordInput, Stack, Text, Title } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { useSession } from '@/app/auth/session';
import { sessionStore } from '@/app/auth/session';
import { PageHeader } from '@/shared/ui/PageHeader';
import { confirmAction, notifySuccess } from '@/shared/ui/feedback';

const MIN_PASSWORD = 10;

type Values = { current_password: string; new_password: string; repeat: string };

export function ProfilePage() {
  const session = useSession();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const form = useForm<Values>({
    initialValues: { current_password: '', new_password: '', repeat: '' },
    validate: {
      current_password: (v) => (v ? null : 'Obligatorio'),
      new_password: (v) => (v.length >= MIN_PASSWORD ? null : `Mínimo ${MIN_PASSWORD} caracteres`),
      repeat: (v, values) => (v === values.new_password ? null : 'Las contraseñas no coinciden'),
    },
  });

  if (session.status !== 'authenticated') return null;
  const { user } = session;

  async function changePassword({ current_password, new_password }: Values) {
    setError(null);
    setSaving(true);
    try {
      const result = await api.POST('/api/v1/auth/change-password', {
        body: { current_password, new_password },
      });
      if (result.error !== undefined) unwrap(result);
      notifySuccess('Contraseña actualizada.');
      form.reset();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function logoutEverywhere() {
    const confirmed = await confirmAction({
      message: 'Se cerrará la sesión en todos los dispositivos, incluido este.',
      confirmLabel: 'Cerrar todas',
      danger: true,
    });
    if (!confirmed) return;
    await api.POST('/api/v1/auth/logout-all');
    sessionStore.signOut();
    navigate('/login', { replace: true });
  }

  return (
    <>
      <PageHeader title="Mi perfil" />
      <Stack maw={480}>
        <Paper withBorder p="md">
          <Text fw={600}>{user.full_name}</Text>
          <Text size="sm" c="dimmed">
            Usuario: {user.username} · Rol: {user.role.name}
          </Text>
        </Paper>

        <Paper withBorder p="md">
          <form onSubmit={form.onSubmit(changePassword)}>
            <Stack>
              <Title order={4}>Cambiar contraseña</Title>
              {error && <Alert color="red">{error}</Alert>}
              <PasswordInput
                label="Contraseña actual"
                required
                {...form.getInputProps('current_password')}
              />
              <PasswordInput
                label="Contraseña nueva"
                description={`Mínimo ${MIN_PASSWORD} caracteres`}
                required
                {...form.getInputProps('new_password')}
              />
              <PasswordInput
                label="Repetir contraseña nueva"
                required
                {...form.getInputProps('repeat')}
              />
              <Group justify="flex-end">
                <Button type="submit" loading={saving}>
                  Cambiar contraseña
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>

        <Paper withBorder p="md">
          <Group justify="space-between">
            <Text size="sm">¿Dejaste la sesión abierta en otro dispositivo?</Text>
            <Button variant="light" color="red" onClick={logoutEverywhere}>
              Cerrar todas las sesiones
            </Button>
          </Group>
        </Paper>
      </Stack>
    </>
  );
}
