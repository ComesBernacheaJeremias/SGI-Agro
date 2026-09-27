import { Badge } from '@mantine/core';

import { useCan } from '@/app/auth/session';
import { CrudTab } from '@/shared/crud/CrudTab';
import type { Column } from '@/shared/crud/DataTable';
import { formatDate } from '@/shared/format/date';

import { type User, usersResource } from './api';
import { UserDrawer } from './UserDrawer';

const COLUMNS: Column<User>[] = [
  { key: 'full_name', header: 'Nombre', sortable: true },
  { key: 'username', header: 'Usuario', sortable: true },
  { key: 'role', header: 'Rol', render: (u) => u.role.name },
  {
    key: 'last_login_at',
    header: 'Último ingreso',
    sortable: true,
    hideOnMobile: true,
    render: (u) => formatDate(u.last_login_at, 'dateTime') || '—',
  },
  {
    key: 'is_active',
    header: 'Estado',
    render: (u) => (
      <Badge color={u.is_active ? 'green' : 'gray'} variant="light">
        {u.is_active ? 'Activo' : 'Inactivo'}
      </Badge>
    ),
  },
];

export function UsersTab() {
  const canManage = useCan()('users:manage');
  return (
    <CrudTab
      resource={usersResource}
      columns={COLUMNS}
      newLabel="Nuevo usuario"
      canCreate={canManage}
      defaultSort="full_name"
      searchPlaceholder="Buscar por nombre o usuario…"
      renderDrawer={(props) => <UserDrawer {...props} canManage={canManage} />}
    />
  );
}
