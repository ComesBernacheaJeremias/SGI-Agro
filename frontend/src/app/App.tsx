import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { ModalsProvider } from '@mantine/modals';
import { Notifications } from '@mantine/notifications';
import { QueryClient } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import 'dayjs/locale/es';
import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';

import { restoreSession } from '@/app/auth/auth';
import { PERSIST_OPTIONS } from '@/app/offline/network';
import { router } from '@/app/router';
import { theme } from '@/app/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    // gcTime largo: lo guardado para usar sin conexión no se descarta enseguida
    queries: { retry: 1, refetchOnWindowFocus: false, gcTime: 24 * 60 * 60 * 1000 },
  },
});

export function App() {
  useEffect(() => {
    void restoreSession();
  }, []);

  return (
    <MantineProvider theme={theme}>
      <DatesProvider settings={{ locale: 'es', firstDayOfWeek: 1 }}>
        <Notifications position="top-right" />
        <ModalsProvider>
          <PersistQueryClientProvider client={queryClient} persistOptions={PERSIST_OPTIONS}>
            <RouterProvider router={router} />
          </PersistQueryClientProvider>
        </ModalsProvider>
      </DatesProvider>
    </MantineProvider>
  );
}
