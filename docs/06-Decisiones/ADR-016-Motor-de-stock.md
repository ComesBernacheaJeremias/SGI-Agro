---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-016 · Motor de stock: líneas, movimientos y recálculo cronológico

## Contexto
Se permite editar y cargar con fecha pasada ([[ADR-004-Edicion-auditoria-y-bloqueo]]), el costo es promedio ponderado ([[ADR-010-Costo-promedio-ponderado]]) y nunca puede haber stock negativo. Además los costos de F5 dependen de que cada salida tenga su costo correcto.

## Decisión
1. **Tres niveles**: comprobante (`stock_documents`) → líneas tal como las cargó el usuario (`stock_document_lines`: cantidad y unidad elegida, costo por esa unidad) → **movimientos** en unidad base con signo y costo (`stock_moves`), que calcula el sistema. El historial se registra sobre comprobante + líneas; los movimientos son derivados.
2. **Sin tabla de saldos**: el stock es la suma de movimientos no anulados (con índices por producto/fecha y producto/almacén). Evita desincronizaciones; si en el futuro hay volumen, se agregan saldos materializados.
3. **Orden cronológico estable**: `(fecha, comprobante, línea, sub-línea)`. El id del comprobante es UUIDv7 (ordenado por creación) y no cambia al editar.
4. **Recálculo por producto** desde la fecha afectada (alta, edición, anulación, fecha pasada): recorre los movimientos en orden, recalcula el promedio (solo las entradas con costo propio lo mueven), asigna costo a las salidas, guarda `avg_cost_after` / `balance_after` y **rechaza** si algún almacén queda negativo en cualquier momento (mensaje con producto, almacén, fecha y cantidades).
5. **Bloqueo por producto** (`SELECT … FOR UPDATE` en orden de id) antes de leer stock: cargas simultáneas del mismo producto se serializan, sin deadlocks.
6. **Movimientos congelados** (`frozen`): conservan su costo en el recálculo (para ciclos finalizados, F3).
7. **Dimensiones de costo** ya presentes en `stock_moves` (sin FK hasta que existan sus tablas en F3).
8. **Anular** = estado `cancelled` en el comprobante + movimientos marcados `cancelled` (siguen visibles en el historial).

## Consecuencias
- ➕ Stock y costos siempre coherentes con lo cargado, aun con ediciones retroactivas.
- ➕ Kardex con saldo y costo promedio en cada momento sin cálculos extra.
- ➖ Editar un movimiento viejo recalcula todos los posteriores del producto (costo lineal en la cantidad de movimientos; aceptable a esta escala).
