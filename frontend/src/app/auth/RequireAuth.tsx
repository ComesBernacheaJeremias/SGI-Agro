import { Center, Loader } from '@mantine/core';
import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useSession } from './session';

/** Protege las rutas: sin sesión, redirige al login (y vuelve a donde estaba después). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const session = useSession();
  const location = useLocation();

  if (session.status === 'checking') {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }
  if (session.status === 'anonymous') {
    // Con la búsqueda (?abrir=…): después de entrar se abre lo que se pidió
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return children;
}
