---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-017 · Costo derivado en elaboración, recálculo en cascada y congelamiento de ciclos

## Contexto
Con recetas de varios niveles ([[ADR-014-Recetas-multinivel]]) el costo de un elaborado depende del costo de sus componentes, que puede cambiar después (se edita una compra vieja). Además, al finalizar un ciclo sus costos deben quedar fijos ([[ADR-004-Edicion-auditoria-y-bloqueo]]).

## Decisión
1. **Modo de costo `derived`** en `stock_moves`: la entrada del producto elaborado vale **lo consumido en el mismo comprobante** (suma de las salidas). Mueve el costo promedio como cualquier entrada con costo.
2. **Recálculo en cascada** (`StockEngine.recalculate_many`): al recalcular un producto desde una fecha, se buscan los comprobantes de elaboración donde se consumió y se recalculan los elaborados desde esa fecha (y así sucesivamente). Tope de 1.000 pasos para cortar bucles.
3. **Congelamiento**: finalizar un ciclo marca `frozen = true` sus movimientos; el recálculo respeta su costo. Las **entradas** congeladas igual cuentan para el promedio. Reabrir (solo Soporte) descongela y recalcula.
4. **Reparto por superficie** en labores de varios ciclos: cada insumo genera un movimiento por ciclo proporcional a sus hectáreas (el último absorbe el redondeo); la maquinaria se reparte al calcular costos.
5. **Tarifa de maquinaria copiada** en cada labor (`field_operation_assets.rate`): cambiar la tarifa del activo no altera labores pasadas; al editar una labor se conserva la tarifa de los activos que ya tenía.

## Consecuencias
- ➕ El costo de mezclas y semielaborados siempre refleja lo que realmente se consumió, aun con ediciones retroactivas.
- ➕ Los ciclos cerrados no cambian de costo por hechos posteriores.
- ➖ Una edición vieja puede disparar varios recálculos encadenados (aceptable a esta escala).
