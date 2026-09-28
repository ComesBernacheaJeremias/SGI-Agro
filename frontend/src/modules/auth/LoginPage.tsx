import {
  Alert,
  Anchor,
  Button,
  Center,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { type FormEvent, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import { errorMessage } from '@/api/errors';
import { login } from '@/app/auth/auth';
import { useSession } from '@/app/auth/session';
import { Logo } from '@/shared/ui/Logo';

import classes from './LoginPage.module.css';

export function LoginPage() {
  const session = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/';

  if (session.status === 'authenticated') return <Navigate to={redirectTo} replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={classes.layout}>
      <div className={classes.panel}>
        {/* En un div: si el panel (flex) estira la imagen, el SVG se centra */}
        <div>
          <Logo on="dark" height={40} />
        </div>
        <div>
          <div className={classes.claim}>Costos y rentabilidad del campo, en un solo lugar.</div>
          <Text className={classes.detail} mt="md" maw={420}>
            Producción, stock, compras y ventas, caja y maquinaria.
          </Text>
        </div>
        <Text size="xs" className={classes.detail}>
          Sistema de gestión integral
        </Text>
      </div>
      <Center p="xl" className={classes.form}>
        <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: 360 }}>
          <Stack>
            <div>
              <Title order={2}>Ingresar</Title>
              <Text c="dimmed" size="sm">
                Con tu usuario y contraseña.
              </Text>
            </div>
            {error && (
              <Alert color="red" variant="light">
                {error}
              </Alert>
            )}
            <TextInput
              label="Usuario"
              value={username}
              onChange={(e) => setUsername(e.currentTarget.value)}
              autoComplete="username"
              autoFocus
              required
            />
            <PasswordInput
              label="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              autoComplete="current-password"
              required
            />
            <Button type="submit" loading={loading} fullWidth>
              Ingresar
            </Button>
            <Anchor component={Link} to="/manual" size="sm" ta="center">
              ¿Cómo se usa? Ver el manual
            </Anchor>
          </Stack>
        </form>
      </Center>
    </div>
  );
}
