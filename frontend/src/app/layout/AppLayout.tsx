import {
  AppShell,
  Avatar,
  Burger,
  em,
  Group,
  Menu,
  NavLink,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { useDisclosure, useMediaQuery } from '@mantine/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { IconChevronDown, IconHelp } from '@tabler/icons-react';
import { Fragment } from 'react';
import { NavLink as RouterNavLink, Outlet, useNavigate } from 'react-router-dom';

import { logout } from '@/app/auth/auth';
import { useCan, useSession } from '@/app/auth/session';
import { NAV_ITEMS, NAV_SECTIONS } from '@/app/navigation';
import { MaintenanceBell } from '@/modules/assets/MaintenanceBell';
import { StockAlertsBell } from '@/modules/inventory/StockAlertsBell';
import { Logo } from '@/shared/ui/Logo';

import classes from './AppLayout.module.css';
import { HelpButton } from './HelpButton';
import { OfflineBadge } from './OfflineBadge';

const LINK_CLASSES = { root: classes.link, section: classes.icon };

/** Estructura de todas las pantallas internas: menú lateral oscuro + barra superior + contenido. */
export function AppLayout() {
  const queryClient = useQueryClient();
  const [menuOpen, { toggle, close }] = useDisclosure();
  // En pantallas grandes el menú es una columna completa (con el nombre arriba); en el
  // celular abre debajo de la barra, para que el botón de cerrar siga a la vista
  const isDesktop = useMediaQuery(`(min-width: ${em(768)})`);
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
      layout={isDesktop ? 'alt' : 'default'}
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !menuOpen } }}
      padding="md"
    >
      <AppShell.Header>
        {/* Una sola línea siempre: en el celular el usuario se muestra con sus iniciales */}
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" hiddenFrom="sm" wrap="nowrap">
            <Burger opened={menuOpen} onClick={toggle} size="sm" aria-label="Menú" />
            <Logo on="light" height={24} />
          </Group>
          <Group gap={4} ml="auto" wrap="nowrap">
            <OfflineBadge />
            <HelpButton />
            <MaintenanceBell />
            <StockAlertsBell />
            <Menu position="bottom-end">
              <Menu.Target>
                <UnstyledButton aria-label={`Usuario: ${userName}`} ml={4}>
                  <Group gap={6} wrap="nowrap">
                    <Avatar name={userName} color="brand" size={30} hiddenFrom="sm" />
                    <Text size="sm" fw={600} visibleFrom="sm" style={{ whiteSpace: 'nowrap' }}>
                      {userName}
                    </Text>
                    <IconChevronDown size={14} />
                  </Group>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label hiddenFrom="sm">{userName}</Menu.Label>
                <Menu.Item onClick={() => navigate('/perfil')}>Mi perfil</Menu.Item>
                <Menu.Item onClick={handleLogout}>Cerrar sesión</Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs" pt={0} className={classes.navbar}>
        <div className={classes.brand}>
          <Logo on="dark" height={30} />
        </div>
        {NAV_SECTIONS.map((section) => {
          const items = NAV_ITEMS.filter(
            (item) => item.section === section.key && (!item.permission || can(item.permission)),
          );
          if (items.length === 0) return null;
          return (
            <Fragment key={section.key}>
              <div className={classes.section}>{section.label}</div>
              {items.map((item) => (
                <NavLink
                  key={item.path}
                  component={RouterNavLink}
                  to={item.path}
                  end={item.path === '/'}
                  label={item.label}
                  classNames={LINK_CLASSES}
                  leftSection={<item.icon size={18} />}
                  onClick={close}
                />
              ))}
            </Fragment>
          );
        })}
        <NavLink
          component={RouterNavLink}
          to="/manual"
          label="Manual de uso"
          classNames={LINK_CLASSES}
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
