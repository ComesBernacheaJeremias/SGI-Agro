---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-019 · Reportes genéricos, exportación y resultado de gestión

## Contexto
F5 suma muchos reportes (costos, rentabilidad, ventas, compras, contador, caja, stock) que se ven en pantalla y se exportan a Excel y PDF. Además hay que definir cómo se calcula el resultado de gestión sin contabilidad formal ([[ADR-011-Gestion-sin-contabilidad-formal]]).

## Decisión
1. **Un reporte = una función** que devuelve un `TableReport` (columnas tipadas: texto, importe, cantidad, %, fecha + filas con estilo y vínculo). Se registra con `@define_report` en el `reports.py` de su módulo, con su permiso y sus filtros. La API expone el catálogo (según permisos), los datos y la exportación; el frontend tiene **un solo visor** (`ReportView`) que arma filtros, tabla y botones Excel/PDF.
2. **Exportación en el backend:** Excel con **openpyxl** (números y fechas reales con formato de celda) y PDF con **reportlab** (en lugar de WeasyPrint: no necesita librerías del sistema en la imagen Docker).
3. **Costos desde "hechos" con dimensiones** (`costs/facts.py`): insumos de labores, maquinaria repartida por superficie, gastos (compras + caja) y mermas. Las consultas de gastos y maquinaria se definen una vez y las comparten producción y costos.
4. **Ingresos por ciclo:** cada línea vendida se reparte entre sus movimientos de stock (partidas) en proporción a la cantidad; la partida da el ciclo ([[ADR-012-Rentabilidad-por-partida]]). La NC de venta resta, en la partida indicada.
5. **Resultado de gestión** de un período = ventas − costo de lo vendido (reventa/elaborados; la producción propia entra a costo 0) − costos de producción (insumos aplicados + gastos con destino) − mermas (ajustes y egresos manuales) − gastos de estructura. **La maquinaria cuenta por gastos reales, no por tarifa** (la tarifa se usa solo en el costo de cada ciclo, para no contar dos veces). Retiros y aportes no son resultado.
6. **Permiso aparte `costs:read`** para costos, rentabilidad y resultado (el secretario no lo tiene salvo que el dueño se lo asigne).

## Consecuencias
- ➕ Sumar un reporte es escribir una función; pantalla, Excel y PDF salen solos.
- ➕ Todos los números se calculan desde la misma fuente: una edición se refleja en todos los reportes.
- ➖ Los reportes calculan en Python sobre los hechos del período; con mucho volumen habría que agregar en SQL (no hace falta a esta escala).
