import { Tabs } from '@mantine/core';

import { PageHeader } from '@/shared/ui/PageHeader';

import { RolesTab } from './RolesTab';
import { UsersTab } from './UsersTab';

export function UsersPage() {
  return (
    <>
      <PageHeader title="Usuarios y roles" />
      <Tabs defaultValue="users" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="users">Usuarios</Tabs.Tab>
          <Tabs.Tab value="roles">Roles</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="users">
          <UsersTab />
        </Tabs.Panel>
        <Tabs.Panel value="roles">
          <RolesTab />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}
