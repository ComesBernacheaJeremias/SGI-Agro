import { Button, PasswordInput, Select, TextInput } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconKey, IconLogout } from '@tabler/icons-react';

import { useSession } from '@/app/auth/session';
import type { DrawerProps } from '@/shared/crud/CrudTab';
import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { useResourceMutations } from '@/shared/crud/hooks';
import { RecordActions } from '@/shared/crud/RecordActions';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import { revokeSessions, type User, usersResource, useRoles } from './api';
import { ResetPasswordForm } from './ResetPasswordForm';

const MIN_PASSWORD = 10;

type Values = { username: string; full_name: string; role_id: string; password: string };

const EMPTY: Values = { username: '', full_name: '', role_id: '', password: '' };

export function UserDrawer({
  record,
  opened,
  onClose,
  canManage,
}: DrawerProps<User> & { canManage: boolean }) {
  const isEdit = record !== null;
  const session = useSession();
  const isSupport = session.status === 'authenticated' && session.user.role.code === 'support';
  const { data: roles = [] } = useRoles();
  const { create, update } = useResourceMutations(usersResource);

  const form = useDrawerForm<User, Values>({
    opened,
    record,
    empty: EMPTY,
    toValues: (u) => ({
      username: u.username,
      full_name: u.full_name,
      role_id: u.role.id,
      password: '',
    }),
    validate: {
      username: required,
      full_name: required,
      role_id: required,
      password: (v) =>
        isEdit || v.length >= MIN_PASSWORD ? null : `Mínimo ${MIN_PASSWORD} caracteres`,
    },
  });

  // Solo Soporte puede asignar el rol Soporte
  const roleOptions = roles
    .filter((r) => r.code !== 'support' || isSupport || r.id === record?.role.id)
    .map((r) => ({ value: r.id, label: r.name }));

  async function submit(values: Values) {
    if (record) {
      const { username, full_name, role_id } = values; // la contraseña no se edita acá
      await update.mutateAsync({ id: record.id, body: { username, full_name, role_id } });
    } else {
      await create.mutateAsync(values);
    }
  }

  function openResetPassword() {
    if (!record) return;
    const modalId = modals.open({
      title: `Nueva contraseña para ${record.full_name}`,
      children: <ResetPasswordForm userId={record.id} onDone={() => modals.close(modalId)} />,
    });
  }

  async function closeSessions(user: User) {
    const ok = await confirmAction({
      message: `Se van a cerrar todas las sesiones abiertas de ${user.full_name} (en todos sus dispositivos). Va a tener que volver a entrar.`,
      confirmLabel: 'Cerrar sesiones',
      danger: true,
    });
    if (!ok) return;
    try {
      await revokeSessions(user.id);
      notifySuccess(`Se cerraron las sesiones de ${user.full_name}.`);
    } catch (err) {
      notifyError(err);
    }
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={isEdit ? 'Editar usuario' : 'Nuevo usuario'}
      form={form}
      isEdit={isEdit}
      onSubmit={submit}
      extraActions={
        record && (
          <RecordActions
            resource={usersResource}
            record={record}
            name={record.full_name}
            canDeactivate={canManage}
            onClose={onClose}
          >
            {canManage && (
              <Button
                variant="subtle"
                leftSection={<IconKey size={16} />}
                onClick={openResetPassword}
              >
                Contraseña
              </Button>
            )}
            {canManage && (
              <Button
                variant="subtle"
                leftSection={<IconLogout size={16} />}
                onClick={() => void closeSessions(record)}
              >
                Cerrar sesiones
              </Button>
            )}
          </RecordActions>
        )
      }
    >
      <TextInput
        label="Nombre completo"
        required
        disabled={!canManage}
        {...form.getInputProps('full_name')}
      />
      <TextInput
        label="Usuario"
        required
        disabled={!canManage}
        {...form.getInputProps('username')}
      />
      <Select
        label="Rol"
        required
        disabled={!canManage}
        data={roleOptions}
        {...form.getInputProps('role_id')}
      />
      {!isEdit && (
        <PasswordInput
          label="Contraseña"
          description={`Mínimo ${MIN_PASSWORD} caracteres`}
          required
          {...form.getInputProps('password')}
        />
      )}
    </EntityDrawer>
  );
}
