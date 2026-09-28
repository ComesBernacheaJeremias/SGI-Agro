---
tags: [adr]
estado: aceptada
fecha: 2026-09-28
---

# ADR-024 · Sin carga sin conexión: el sistema se usa con internet (o datos del celular)

Reemplaza a [[ADR-006-Offline-limitado]].

## Contexto
La carga sin conexión (F7) cubría solo labores, cosechas, movimientos de stock y preparaciones: compras, ventas, cobros, pagos y caja igual necesitaban conexión. En la prueba en Chrome (27/09) apareció un bug en la cola de pendientes, lo que mostró el costo de mantenerla. No es algo que se haya hablado con el cliente. El sistema se puede usar desde el celular, así que si se corta internet en la oficina se sigue con los datos móviles.

## Decisión
- Se **quita** la carga sin conexión: cola de pendientes, datos guardados en el dispositivo (IndexedDB), precarga de maestros e ingreso sin señal.
- Se **mantiene**:
  - **App instalable** (PWA: ícono en el celular o la PC).
  - **Aviso "Sin conexión"** en la barra superior: sin internet no se guarda.
  - **Id generado en el dispositivo** en las altas de labores/cosechas, comprobantes de stock y preparaciones (`useNewId`, se renueva al abrir el formulario): si se corta la red justo al guardar y se reintenta, no se duplica.
- Caso extremo (sin internet ni datos): anotar y cargar al volver la conexión.

## Alternativas descartadas
- **Arreglar el bug y mantener la carga sin conexión:** sirve para una parte chica del sistema y suma complejidad.
- **Planillas Excel para completar sin señal e importar después:** una plantilla y validación por cada tipo de carga (compras, ventas, cobros, caja, labores…), con errores que aparecen recién al importar; mucho trabajo para un caso rarísimo. Se evalúa si el cliente lo pide.

## Consecuencias
- ➕ Menos código y dependencias (`idb-keyval`, persistencia de TanStack Query); sin datos del negocio guardados en el dispositivo.
- ➕ Todo el sistema funciona igual con Wi-Fi o datos móviles.
- ➖ Sin ninguna conexión no se puede cargar nada.
