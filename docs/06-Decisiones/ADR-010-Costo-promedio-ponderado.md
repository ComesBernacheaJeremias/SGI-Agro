---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-010 · Valuación de stock por costo promedio ponderado

## Contexto
Las salidas de stock (consumos, ventas) necesitan un costo. Opciones: promedio ponderado, FIFO, estándar.

## Decisión
**Costo promedio ponderado móvil por producto** (global, no por almacén):
`nuevo_promedio = (stock × promedio + cantidad_ingreso × costo_ingreso) / (stock + cantidad_ingreso)`.
Las salidas toman el promedio vigente; las transferencias no cambian el costo.
- Si se edita/anula un ingreso o se carga uno con fecha pasada → se recalcula la cadena del producto desde esa fecha, **sin tocar consumos de ciclos finalizados** ([[ADR-004-Edicion-auditoria-y-bloqueo]]).
- Producción propia cosechada: ingresa con costo cero (su costo está en el ciclo, ver [[ADR-012-Rentabilidad-por-partida]]).

## Por qué
Simple de entender y de implementar; suaviza la variación de precios. FIFO requiere capas de costo por ingreso sin beneficio claro acá.

## Consecuencias
- El recálculo es la operación más delicada del inventario → tests dedicados.
