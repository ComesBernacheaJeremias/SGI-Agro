import { Alert, Button, Checkbox, Fieldset, Stack, Textarea, TextInput } from '@mantine/core';
import { useQueryClient } from '@tanstack/react-query';
import { IconTrash } from '@tabler/icons-react';

import { EntityDrawer } from '@/shared/crud/EntityDrawer';
import { HistoryButton } from '@/shared/crud/HistoryButton';
import { required, useDrawerForm } from '@/shared/crud/useDrawerForm';
import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';

import { type Role, ROLES_KEY, rolesApi, usePermissionGroups } from './api';

type Values = { name: string; description: string; permissions: string[] };

const EMPTY: Values = { name: '', description: '', permissions: [] };

type Props = { role: Role | null; opened: boolean; onClose: () => void; canManage: boolean };

export function RoleDrawer({ role, opened, onClose, canManage }: Props) {
  const isEdit = role !== null;
  const queryClient = useQueryClient();
  const { data: groups = [] } = usePermissionGroups();
  const permissionsLocked = !canManage || (role !== null && !role.permissions_editable);
  const nameLocked = !canManage || (role?.is_system ?? false);

  const form = useDrawerForm<Role, Values>({
    opened,
    record: role,
    empty: EMPTY,
    toValues: (r) => ({ name: r.name, description: r.description, permissions: r.permissions }),
    validate: { name: required },
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: [ROLES_KEY] });

  async function submit(values: Values) {
    if (role) {
      await rolesApi.update(role.id, {
        name: role.is_system ? undefined : values.name,
        description: values.description,
        permissions: role.permissions_editable ? values.permissions : undefined,
      });
      notifySuccess('Cambios guardados.');
    } else {
      await rolesApi.create(values);
      notifySuccess('Se creó el rol.');
    }
    await refresh();
  }

  async function remove() {
    if (!role) return;
    const confirmed = await confirmAction({
      message: `Se va a eliminar el rol "${role.name}".`,
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!confirmed) return;
    try {
      await rolesApi.remove(role.id);
      notifySuccess('Rol eliminado.');
      onClose();
      await refresh();
    } catch (err) {
      notifyError(err);
    }
  }

  return (
    <EntityDrawer
      opened={opened}
      onClose={onClose}
      title={isEdit ? `Rol: ${role.name}` : 'Nuevo rol'}
      form={form}
      isEdit={isEdit}
      onSubmit={submit}
      extraActions={
        role && (
          <>
            <HistoryButton table="roles" recordId={role.id} />
            {canManage && !role.is_system && (
              <Button
                variant="subtle"
                color="red"
                leftSection={<IconTrash size={16} />}
                onClick={remove}
              >
                Eliminar
              </Button>
            )}
          </>
        )
      }
    >
      {role && !role.permissions_editable && (
        <Alert variant="light">
          Rol fijo del sistema: sus permisos se calculan automáticamente y no se pueden modificar.
        </Alert>
      )}
      <TextInput label="Nombre" required disabled={nameLocked} {...form.getInputProps('name')} />
      <Textarea
        label="Descripción"
        autosize
        disabled={!canManage}
        {...form.getInputProps('description')}
      />
      <Stack gap="xs">
        {groups.map((group) => (
          <Fieldset key={group.group} legend={group.group}>
            <Checkbox.Group {...form.getInputProps('permissions')}>
              <Stack gap={6}>
                {group.permissions.map((p) => (
                  <Checkbox
                    key={p.code}
                    value={p.code}
                    label={p.label}
                    disabled={permissionsLocked || p.support_only}
                  />
                ))}
              </Stack>
            </Checkbox.Group>
          </Fieldset>
        ))}
      </Stack>
    </EntityDrawer>
  );
}
