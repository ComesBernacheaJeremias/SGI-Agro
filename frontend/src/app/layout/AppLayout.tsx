import { AppShell, Burger, Group, Menu, NavLink, Text, UnstyledButton } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { IconChevronDown, IconHelp, IconLogout, IconUser } from '@tabler/icons-react';
import { NavLink as RouterNavLink, Outlet, useNavigate } from 'react-router-dom';

import { logout } from '@/app/auth/auth';
import { useCan, useSession } from '@/app/auth/session';
import { NAV_ITEMS } from '@/app/navigation';
import { MaintenanceBell } from '@/modules/assets/MaintenanceBell';
import { StockAlertsBell } from '@/modules/inventory/StockAlertsBell';

import { OfflineBadge } from './OfflineBadge';

/** Estructura de todas las pantallas internas: barra superior + menú lateral + contenido. */
export function AppLayout() {
  const queryClient = useQueryClient();
  const [menuOpen, { toggle, close }] = useDisclosure();
  const session = useSession();
  const can = useCan();
  const navigate = useNavigate();
  const userName = session.status === 'authenticated' ? session.user.full_name : '';

  async function handleLogout() {
    await logout();
    queryClient.clear(); // que no quede nada del usuario anterior en memoria
    navigate('/login', { replace: true });
  }

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !menuOpen } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger
              opened={menuOpen}
              onClick={toggle}
              hiddenFrom="sm"
              size="sm"
              aria-label="Menú"
            />
            <Text fw={700} c="green.8">
              SGI Agro
            </Text>
          </Group>
          <Group gap="xs">
            <OfflineBadge />
            <MaintenanceBell />
            <StockAlertsBell />
            <Menu position="bottom-end">
              <Menu.Target>
                <UnstyledButton>
                  <Group gap={6}>
                    <IconUser size={18} />
                    <Text size="sm">{userName}</Text>
                    <IconChevronDown size={14} />
                  </Group>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item leftSection={<IconUser size={16} />} onClick={() => navigate('/perfil')}>
                  Mi perfil
                </Menu.Item>
                <Menu.Item leftSection={<IconLogout size={16} />} onClick={handleLogout}>
                  Cerrar sesión
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        {NAV_ITEMS.filter((item) => !item.permission || can(item.permission)).map((item) => (
          <NavLink
            key={item.path}
            component={RouterNavLink}
            to={item.path}
            end={item.path === '/'}
            label={item.label}
            leftSection={<item.icon size={18} />}
            onClick={close}
          />
        ))}
        <NavLink
          component={RouterNavLink}
          to="/manual"
          label="Manual de uso"
          leftSection={<IconHelp size={18} />}
          mt="auto"
        />
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
