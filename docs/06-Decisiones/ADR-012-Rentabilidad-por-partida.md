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

### Resultado de gestión: el costo de lo cosechado se descuenta aunque siga en stock
El resultado de gestión descuenta como **costos de producción** todo lo que se gastó en los ciclos en el período (insumos aplicados, maquinaria, servicios y gastos con destino a un ciclo), **se haya vendido o no la cosecha**. Por eso la producción propia sale a costo cero en "costo de lo vendido". Motivos:
- **No contar dos veces:** si la cosecha entrara con costo, al venderla se descontaría de nuevo como costo de lo vendido.
- **Simple y estable:** el costo de un ciclo cambia hasta que se finaliza (labores posteriores a la cosecha, cosechas en varias veces, reaperturas); valorizar el stock con ese costo obligaría a recalcularlo todo el tiempo.
- **Coincide con cómo lo mira el cliente:** lo que gastó en el campo en la temporada, contra lo que vendió.
- Consecuencia: en una temporada con mucha cosecha sin vender, el resultado de gestión se ve peor que la rentabilidad "económica"; la **rentabilidad por ciclo** (ingresos de sus partidas − costos del ciclo) es la que muestra el margen real de cada cultivo.

### Valor informativo de la producción propia en stock (28/09/2026)
Para que Inventario y el tablero no muestren la producción propia en $0, se **muestra** valorizada con el **costo por unidad de su ciclo** (costo del ciclo ÷ cantidad cosechada), por partida (`backend/app/modules/production/valuation.py`, `estimated_value` en el listado de stock, `own_produce_value` en el tablero).
- **Solo para mostrar:** NO se usa en costo de lo vendido, kardex, costo promedio ni resultado (esos siguen en cero). Está advertido en el código.
- Si el ciclo está **en curso**, el valor se marca **provisorio** (el costo sigue cambiando).
- "Valor del stock" del tablero y "Valor total" de Inventario lo incluyen y aclaran cuánto corresponde a producción propia.
- Alternativa descartada por ahora: que la cosecha **entre al stock con costo** (cambio de fondo en costos y resultado); solo si el cliente lo pide explícitamente.

## Consecuencias
- ➕ Rentabilidad exacta por ciclo, lote, cultivo y temporada; trazabilidad cosecha → cliente.
- ➖ Un dato más al vender (mitigado con la propuesta automática).
- ➖ El stock contable no incluye el valor de la producción propia; se muestra aparte, valorizada por costo del ciclo, como dato informativo.
