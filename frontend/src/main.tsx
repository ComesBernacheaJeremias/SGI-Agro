import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';
// Fuente instalada en el proyecto (la CSP no permite fuentes de otros sitios)
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-sans/700.css';
import '@/app/theme/global.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { registerSW } from 'virtual:pwa-register';

import { App } from '@/app/App';

// Service worker: app instalable, abre más rápido y se actualiza sola al publicar una versión nueva
registerSW({ immediate: true });

const root = document.getElementById('root');
if (!root) throw new Error('Falta el elemento #root en index.html');

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
