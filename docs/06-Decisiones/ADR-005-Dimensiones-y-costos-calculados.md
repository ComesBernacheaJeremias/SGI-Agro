---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-005 · Dimensiones en cada registro y costos calculados por consulta

## Contexto
El PDF pide centros de costo por lote, producto o actividad, con imputación automática. Si los centros de costo se cargan aparte, se desincronizan; y como se permite editar ([[ADR-004-Edicion-auditoria-y-bloqueo]]), cualquier tabla de costos "precalculada" quedaría desactualizada.

## Decisión
- Todo registro que genera costo guarda sus **dimensiones** como columnas: `farm_id`, `plot_id`, `crop_cycle_id`, `field_operation_id`, `asset_id` (el producto ya está en la línea). La temporada se deduce de la fecha.
- La dimensión la aporta la operación misma (una labor ya sabe su ciclo) → imputación automática.
- **No hay tabla de costos**: los costos y la rentabilidad se calculan con consultas sobre stock, labores, gastos y ventas. Si un reporte se vuelve lento, se agregan índices o vistas materializadas.

## Consecuencias
- ➕ Una edición se refleja sola en los costos; nada que sincronizar.
- ➕ Cualquier corte (lote, ciclo, cultivo, labor, activo, temporada, categoría) es un `GROUP BY`.
- ➖ Una dimensión nueva requiere migración (son pocas y estables).
- Obligatorio desde F2: sin dimensiones en los movimientos, los costos de F5 no se pueden reconstruir.
