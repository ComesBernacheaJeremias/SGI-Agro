---
tags: [arquitectura, offline]
actualizado: 2026-09-28
---

# Offline y sincronización

**No hay carga sin conexión** ([[ADR-024-Sin-carga-offline]], reemplaza a [[ADR-006-Offline-limitado]]). El sistema se usa con internet; si se corta en la oficina, con los datos del celular.

## Qué queda
- **App instalable** (`vite-plugin-pwa`): manifiesto, íconos y service worker (abre más rápido y se actualiza sola al publicar). Solo en la versión compilada.
- **Aviso "Sin conexión"** en la barra superior (`app/layout/OfflineBadge.tsx`): sin internet no se puede guardar.
- **Id generado en el dispositivo** en las altas de labores/cosechas (`OperationIn`), comprobantes de stock (`DocumentIn`) y preparaciones (`OrderIn`): `useNewId` (`shared/crud/newId.ts`) crea uno cada vez que se abre el formulario; si se corta la red justo al guardar y se reintenta, el servidor devuelve el registro existente sin procesarlo de nuevo (test `test_client_id.py`).
- Sin red al abrir la app → pantalla de login. Si se corta con la sesión abierta, se sigue en la app y los pedidos muestran error hasta que vuelva la conexión.

## Qué se quitó (28/09/2026)
Cola de pendientes (`outbox`, `submitOrQueue`), caché de consultas en IndexedDB, precarga de maestros, ingreso sin señal con el último usuario y búsqueda de productos sin señal. Dependencias quitadas: `idb-keyval`, `@tanstack/react-query-persist-client`, `@tanstack/query-async-storage-persister`.
