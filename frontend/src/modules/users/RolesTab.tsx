import { Badge, Button, Group, LoadingOverlay, Table } from '@mantine/core';
import { useState } from 'react';

import { useCan } from '@/app/auth/session';

import { type Role, useRoles } from './api';
import { RoleDrawer } from './RoleDrawer';

export function RolesTab() {
  const canManage = useCan()('users:manage');
  const { data: roles = [], isLoading } = useRoles();
  const [editing, setEditing] = useState<Role | null>(null);
  const [opened, setOpened] = useState(false);

  function open(role: Role | null) {
    setEditing(role);
    setOpened(true);
  }

  return (
    <>
      {canManage && (
        <Group justify="flex-end" mb="sm">
          <Button onClick={() => open(null)}>Nuevo rol</Button>
        </Group>
      )}
      <Table striped highlightOnHover pos="relative">
        <LoadingOverlay visible={isLoading} />
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Rol</Table.Th>
            <Table.Th visibleFrom="sm">Descripción</Table.Th>
            <Table.Th ta="right">Usuarios</Table.Th>
            <Table.Th ta="right">Permisos</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {roles.map((role) => (
            <Table.Tr key={role.id} onClick={() => open(role)} style={{ cursor: 'pointer' }}>
              <Table.Td>
                <Group gap="xs">
                  {role.name}
                  {role.is_system && (
                    <Badge size="xs" variant="light" color="gray">
                      Sistema
                    </Badge>
                  )}
                </Group>
              </Table.Td>
              <Table.Td visibleFrom="sm">{role.description}</Table.Td>
              <Table.Td ta="right">{role.user_count}</Table.Td>
              <Table.Td ta="right">{role.permissions.length}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <RoleDrawer
        role={editing}
        opened={opened}
        onClose={() => setOpened(false)}
        canManage={canManage}
      />
    </>
  );
}
