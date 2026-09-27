---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-004 · Edición con confirmación, historial completo y bloqueo de ciclos finalizados

## Contexto
El cliente quiere poder corregir datos (no le sirve el esquema "inmutable" de un sistema contable) y a la vez tener trazabilidad (PDF 2.7) y costos confiables.

## Decisión
1. **Se puede editar** cualquier registro operativo, con confirmación "¿Estás seguro?" en la UI.
2. **Eliminar = anular:** el registro sale de listas y cálculos pero queda consultable.
3. **Historial automático** de todo cambio: quién, cuándo, acción y valores antes → después.
4. Las ediciones mantienen la consistencia:
   - Stock: se rechaza la edición si deja stock negativo en algún momento posterior.
   - Costo promedio: si cambia el costo de un ingreso, se recalcula desde esa fecha.
   - Cobros: si un comprobante baja de monto por debajo de lo cobrado, el excedente queda como anticipo.
5. **Ciclo finalizado = bloqueado:** no se editan ni anulan sus labores, consumos ni gastos; su costo queda congelado (el recálculo del costo promedio **no** toca sus consumos; las horas de maquinaria usan la tarifa copiada al cargar). Las ediciones posteriores solo afectan a ciclos activos. Las ventas de sus partidas siguen sumando ingresos.
6. Solo el rol **`support`** (desarrollador) reabre un ciclo, con motivo registrado. El cliente lo pide al desarrollador.
7. No hay bloqueo por temporada ni por mes.

## Alternativas descartadas
- Registros inmutables con contra-asientos (estilo contable): el cliente no lo quiere y no hay contabilidad formal.
- Bloqueo por temporada en ciclos largos: descartado por el cliente.

## Consecuencias
- ➕ Flexible para el usuario, trazable y con costos cerrados estables.
- ➖ El recálculo de costo promedio es la parte más delicada → tests dedicados.
- ➖ En ciclos largos (frutales, forestales) los datos de temporadas pasadas siguen editables mientras el ciclo esté activo (aceptado).
