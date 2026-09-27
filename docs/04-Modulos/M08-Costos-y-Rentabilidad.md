---
modulo: M08
codigo: costs
etapa: F5
estado: implementado
depende_de: [M03, M04, M06, M07]
actualizado: 2026-09-27
---

# M08 · Costos y rentabilidad

## Objetivo
Responder **cuánto cuesta producir cada cosa, en cada lote y temporada, y cuánto se gana** (PDF 2.4). Es lo que más le importa al cliente.

## Cómo se calcula
No se cargan centros de costo a mano: cada registro ya sabe a qué establecimiento, lote, ciclo, labor o activo pertenece ([[ADR-005-Dimensiones-y-costos-calculados]]). Los costos se **calculan con consultas**, por eso una edición se refleja sola.

### Costos directos de un ciclo
| Componente | Origen |
|---|---|
| Insumos | Consumos de las labores (cantidad × costo promedio) |
| Maquinaria | Horas de las labores × tarifa copiada del activo |
| Servicios y otros gastos | Compras o movimientos de caja con destino = ese ciclo o su lote* |

\* Un gasto con destino **lote** (sin ciclo) se muestra como costo del lote; en los reportes por ciclo se muestra aparte como "gastos del lote sin asignar a ciclo".

### Gastos de estructura
Gastos **sin destino** (luz de oficina, seguros generales, honorarios…). **No se reparten**: se muestran aparte, filtrables por categoría y período ([[ADR-011-Gestion-sin-contabilidad-formal]]).

### Ingresos de un ciclo
Ventas de las partidas que salieron de ese ciclo ([[ADR-012-Rentabilidad-por-partida]]). Siguen sumando aunque el ciclo esté finalizado.

### Ciclos finalizados
Sus costos quedan congelados: las ediciones posteriores (ej. el precio de una compra) solo afectan a ciclos activos ([[ADR-004-Edicion-auditoria-y-bloqueo]]).

## Historias de usuario
**HU-08-01 · Costo de un ciclo** — total y desglose (insumos, maquinaria, servicios/gastos por categoría), por tipo de labor y por mes; costo/ha y costo/kg cosechado.
**HU-08-02 · Costos de un lote** — filtros por lote, período/temporada y categoría (ej. "servicios del Lote 3 en 2026/27").
**HU-08-03 · Rentabilidad por ciclo** — ingresos − costos directos, margen, margen/ha.
**HU-08-04 · Rentabilidad por cultivo y temporada** — ej. "manzana 2026/27" en todos los lotes; ciclos largos cortados por temporada.
**HU-08-05 · Comparativos** — mismo cultivo entre lotes o entre temporadas.
**HU-08-06 · Margen de reventa y productos elaborados (terminados y semielaborados)** — por producto: ventas − costo.
**HU-08-07 · Resultado de gestión** — por período: ingresos − costos directos − gastos de estructura = resultado.

## Implementación

### F5 (2026-09-27) ✅
Decisión: [[ADR-019-Reportes-y-resultado-de-gestion]].

Backend `app/modules/costs/`:
- `facts.py`: hechos de costo con dimensiones (insumos de labores, maquinaria repartida por superficie, gastos de compras y caja, mermas). Comparte con producción `machinery_rows()` (producción) y `expense_rows()` (comercial).
- `service.py` (`CostQueries`): rentabilidad de ciclos (costos del resumen de producción + ingresos por partida de `commercial/sales.py`), detalle de un ciclo y resultado de gestión.
- `reports.py`: reportes Rentabilidad (por ciclo, cultivo y temporada, cultivo, temporada, lote o establecimiento; filtros temporada/cultivo/establecimiento/lote/estado), Resultado de gestión, Costos por lote (incluye "gastos sin asignar a ciclo" y gastos del establecimiento), Gastos (todos / estructura / con destino; por detalle, categoría, destino, mes o proveedor) y Margen por producto.
- `GET /api/v1/costs/cycles/{id}`: costo y rentabilidad de un ciclo con desgloses (insumos por producto, maquinaria por activo, gastos por categoría, por tipo de labor, por mes, ventas por partida).
- Permiso `costs:read` (staff no lo tiene por defecto).

Frontend: pantalla **Costos y rentabilidad** (`modules/costs/`) con pestañas Rentabilidad, Resultado de gestión, Costos por lote, Gastos y Margen por producto; tocar un ciclo abre su detalle de costos.

Tests: `tests/integration/test_costs.py`.

Pendiente / diferido:
- Ciclos largos cortados por temporada (hoy un ciclo pertenece a la temporada en que empezó).
- Costo real por activo: hecho en F6 ([[M07-Activos]]); los repuestos de mantenimientos suman a los costos de producción del resultado de gestión.
