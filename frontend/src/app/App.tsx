import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { ModalsProvider } from '@mantine/modals';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import 'dayjs/locale/es';
import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';

import { restoreSession } from '@/app/auth/auth';
import { router } from '@/app/router';
import { cssVariables, theme } from '@/app/theme/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

export function App() {
  useEffect(() => {
    void restoreSession();
  }, []);

  return (
    <MantineProvider theme={theme} cssVariablesResolver={cssVariables}>
      <DatesProvider settings={{ locale: 'es', firstDayOfWeek: 1 }}>
        <Notifications position="top-right" />
        <ModalsProvider>
          <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
          </QueryClientProvider>
        </ModalsProvider>
      </DatesProvider>
    </MantineProvider>
  );
}
