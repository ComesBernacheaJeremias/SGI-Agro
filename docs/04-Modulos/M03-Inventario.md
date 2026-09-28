---
modulo: M03
codigo: inventory
etapa: F2
estado: implementado
depende_de: [M01, M02]
actualizado: 2026-09-27
---

# M03 · Inventario

## Objetivo
Stock al momento por producto, almacén y partida, con cada movimiento respaldado por un comprobante (PDF 2.1). Es la base del cálculo de costos.

## Historias de usuario

**HU-03-01 · Ingreso manual de stock**
- Fecha, almacén, tercero (opcional), comprobante de referencia (tipo y número), líneas (producto, cantidad, unidad, costo unitario).
- Aumenta el stock y recalcula el costo promedio ([[ADR-010-Costo-promedio-ponderado]]).
- Los ingresos por compra se generan desde [[M06-Comercial-y-Caja]].

**HU-03-02 · Egreso manual de stock**
- Igual, pero resta. El costo lo pone el sistema (promedio vigente).
- Sin stock suficiente → error indicando producto, almacén y cantidad disponible.

**HU-03-03 · Transferencia entre almacenes** — origen, destino, líneas; el costo viaja con la mercadería.

**HU-03-04 · Ajuste de inventario**
- El usuario carga lo contado y el sistema genera la diferencia (+/−) con motivo obligatorio (rotura, vencimiento, diferencia de conteo…).

**HU-03-05 · Consultar stock** — por producto, almacén, categoría y partida: cantidad, costo promedio, valor. Stock a una fecha pasada. Alerta de stock mínimo.

**HU-03-06 · Movimientos de un producto (kardex)** — fecha, documento, entrada, salida, saldo, costo; cada línea abre su documento de origen.

**HU-03-07 · Editar un movimiento**
- Con confirmación "¿Estás seguro?". Queda en el historial.
- Si la edición deja stock negativo en algún momento posterior → se rechaza con mensaje claro.
- Si cambia un costo de ingreso → se recalcula el costo promedio desde esa fecha; las salidas de **ciclos finalizados no cambian** ([[ADR-004-Edicion-auditoria-y-bloqueo]]).
- Movimientos que pertenecen a un ciclo finalizado no se pueden editar.

**HU-03-08 · Anular un documento** — desaparece de listas y cálculos, queda en el historial. Mismas validaciones que editar.

## Reglas de negocio
- Stock nunca negativo (con bloqueo de fila para evitar cargas simultáneas en conflicto).
- Todo movimiento guarda sus dimensiones cuando corresponde: lote, ciclo, labor, activo ([[ADR-005-Dimensiones-y-costos-calculados]]).
- Tipos: `manual_in`, `manual_out`, `transfer`, `adjustment` (desde este módulo); `purchase`, `sale`, `consumption`, `harvest`, `production` (generados por otros módulos, se editan desde su origen).
- Numeración correlativa por tipo (ej. `ING-000123`).

## Datos
`stock_documents`, `stock_moves`, `stock_balances`, `batches`.

## Pantallas
Stock actual · Kardex · Documentos (lista + formulario por tipo) · Conteo/ajuste.

## Endpoints (tentativo)
`/stock-documents` (+ `/cancel`) · `GET /stock/balances` · `GET /stock/moves?product_id=`

## Implementación

**F7:** alta con id generado en el dispositivo (reintentar no duplica; la carga sin conexión se quitó: [[ADR-024-Sin-carga-offline]]). Importación del **stock inicial** desde Excel (`inventory/imports.py`): un ingreso con referencia "Stock inicial" por almacén y fecha ([[ADR-021-Importacion-desde-Excel]]).

### F2 (2026-09-27) ✅
Decisión de diseño: [[ADR-016-Motor-de-stock]].

| Historia | Estado |
|---|---|
| HU-03-01 Ingreso (costo obligatorio, puede ser 0; sirve para stock inicial) | ✅ |
| HU-03-02 Egreso (a costo promedio) | ✅ |
| HU-03-03 Transferencia entre almacenes | ✅ |
| HU-03-04 Ajuste por conteo (motivo obligatorio; permiso aparte `inventory:adjust`) | ✅ |
| HU-03-05 Stock (por producto o por almacén, a fecha, bajo mínimo, valor) | ✅ |
| HU-03-06 Kardex con saldo inicial/acumulado | ✅ |
| HU-03-07/08 Editar y anular (con recálculo y control de negativos) | ✅ |
| Aviso "Necesitás comprar" (stock total ≤ mínimo) | ✅ |

**Backend** `app/modules/inventory/`
- `models.py`: `StockDocument` (tipo, número, fecha, almacén/destino, tercero, referencia, motivo, estado, origen si lo generó otro módulo), `StockDocumentLine` (lo cargado: producto, unidad, cantidad, factor a unidad base, costo por unidad cargada), `StockMove` (unidad base, signo, `cost_mode` own/average, costo, `avg_cost_after`, `balance_after`, `cancelled`, `frozen`, dimensiones de costo).
- `engine.py` → `StockEngine`: `lock_products` y `recalculate(product, desde)` (costo promedio + control de negativos).
- `service.py` → `StockDocumentService`: create / update (reemplaza líneas y movimientos, recalcula desde la fecha más vieja) / cancel. Tipos manuales: `manual_in`, `manual_out`, `transfer`, `adjustment` (los demás tipos quedan reservados para compras, ventas, consumo, cosecha y elaboración). Validaciones: fecha no futura, almacenes activos y distintos en transferencias, costo en ingresos, sin servicios ni productos inactivos, producto no repetido en ajustes.
- `queries.py` → `StockQueries`: `quantity` (saldo puntual), `stock` (listado paginado), `alerts` (mínimos), `kardex`.
- Unidades: `masterdata/units.py` → `unit_factor(producto, unidad)`: misma unidad, equivalencia propia o misma magnitud; si no hay equivalencia, error `NO_UNIT_CONVERSION`.
- Numeración: `core/sequences.py` (`ING-000001`, `EGR-`, `TRF-`, `AJU-`), con bloqueo de fila.
- Formato de textos del backend: `core/formatting.py` (mismas reglas que el frontend).
- Endpoints: `/api/v1/stock-documents` (GET lista con filtros, GET detalle, POST, PUT, POST `/{id}/cancel`); `/api/v1/stock` (GET), `/stock/alerts`, `/stock/kardex`, `/stock/options`. Guardar/anular devuelven `{document, alerts}`.
- Permisos: `inventory:read`, `inventory:write`, `inventory:cancel`, `inventory:adjust` (staff: todos menos adjust).

**Frontend** `modules/inventory/`: pantalla Inventario (botón "Nuevo" → Ingreso / Egreso / Transferencia / Ajuste según permisos), pestañas Stock (filtros almacén, categoría, a fecha, por almacén, bajo mínimo; clic → kardex), Movimientos (filtros tipo, almacén, estado, fechas), Kardex. `DocumentDrawer` + `LinesField` (producto con buscador en servidor, unidades válidas del producto, subtotales, stock del sistema y diferencia en ajustes). Campana "Necesitás comprar" en la barra superior (`StockAlertsBell`) y aviso al guardar.
- Piezas nuevas reutilizables: `masterdata/ProductSelect.tsx` (buscador de productos), `masterdata/units.ts` (`allowedUnits`).

**Tests**: `tests/integration/test_inventory.py` (23: costo promedio, ejemplo del cliente, recálculo al editar, negativos con fecha pasada, anulaciones, transferencias, conversiones, ajustes y permiso, validaciones, alertas, stock a fecha, kardex, historial).

**Pendiente**: congelar movimientos de ciclos finalizados (F3); FK de dimensiones cuando existan establecimientos/lotes/ciclos (F3); impedir cambiar la unidad base de un producto con movimientos (`TODO(F2)` en maestros → hacer junto con F3).

**Ajuste 27/09:** `GET /api/v1/stock` acepta `product_id` (stock de un producto, por almacén con `by_warehouse=true`), usado para proponer el almacén de los insumos de una labor. El listado de productos acepta varios tipos (`type=input&type=finished`).
