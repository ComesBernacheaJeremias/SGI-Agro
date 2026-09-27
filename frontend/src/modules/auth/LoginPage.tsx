import {
  Alert,
  Anchor,
  Button,
  Center,
  Paper,
  PasswordInput,
  Stack,
  TextInput,
  Title,
} from '@mantine/core';
import { type FormEvent, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import { errorMessage } from '@/api/errors';
import { login } from '@/app/auth/auth';
import { useSession } from '@/app/auth/session';

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
    <Center mih="100vh" p="md" bg="gray.0">
      <Paper withBorder shadow="sm" p="xl" radius="md" w="100%" maw={380}>
        <form onSubmit={handleSubmit}>
          <Stack>
            <Title order={2} ta="center" c="green.8">
              SGI Agro
            </Title>
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
      </Paper>
    </Center>
  );
}
