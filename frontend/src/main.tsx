import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { registerSW } from 'virtual:pwa-register';

import { App } from '@/app/App';

// Service worker: la app abre sin conexión y se actualiza sola al publicar una versión nueva
registerSW({ immediate: true });

const root = document.getElementById('root');
if (!root) throw new Error('Falta el elemento #root en index.html');

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
