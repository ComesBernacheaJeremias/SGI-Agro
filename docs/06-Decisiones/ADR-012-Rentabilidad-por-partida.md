---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-012 · Rentabilidad por ciclo mediante partidas

## Contexto
Para saber cuánto ganó un ciclo ("Tomate del Lote 3") hay que saber cuánto se vendió de **su** producción.

## Alternativas
1. **Partidas:** cada cosecha genera una partida con su ciclo de origen; la venta indica la partida. Exacto y con trazabilidad.
2. **Estimada:** kg cosechados × precio promedio del período. Simple pero impreciso.

## Decisión
**Partidas.** Al vender producción propia, el sistema propone la partida más antigua con stock (el usuario puede cambiarla).
- La partida guarda el ciclo de origen → ingreso por ciclo = ventas de sus partidas.
- El producto cosechado ingresa al stock con **costo cero**: el costo real vive en el ciclo, y rentabilidad del ciclo = ingresos de sus partidas − costos del ciclo. Así editar costos de un ciclo no obliga a revaluar stock.

## Consecuencias
- ➕ Rentabilidad exacta por ciclo, lote, cultivo y temporada; trazabilidad cosecha → cliente.
- ➖ Un dato más al vender (mitigado con la propuesta automática).
- ➖ El stock valorizado no incluye el valor de la producción propia (se muestra en cantidades; se puede mostrar valorizado a precio de venta de referencia si se pide).
