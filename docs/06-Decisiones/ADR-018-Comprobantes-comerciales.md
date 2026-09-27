---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-018 · Comprobantes comerciales: stock, imputaciones y gastos

## Contexto
F4 registra compras, ventas, cobros, pagos y caja sin contabilidad formal ([[ADR-011-Gestion-sin-contabilidad-formal]]). Hay que decidir cómo se relacionan con el stock, cómo se saldan las deudas y cómo llegan los gastos al costo de un ciclo.

## Decisión
1. **Un comprobante comercial con productos genera un comprobante de stock de sistema** ([[ADR-016-Motor-de-stock]]), que se edita y anula solo desde el comercial. Compra: entrada con costo propio = precio neto ÷ factor de la unidad. Venta y devoluciones: costo promedio.
2. **Numeración doble:** siempre un número interno (`CPR-`/`VTA-`); si hubo factura, además letra, punto de venta y número (identifica al comprobante en pantallas). Series separadas de las de stock (`RCP-`/`DSP-`).
3. **Saldos calculados con imputaciones:** un cobro/pago se imputa a comprobantes (`allocations`); lo no imputado es **anticipo**. Pendiente = total − imputado vigente. No hay saldos guardados.
4. **Recorte automático:** si un comprobante baja de total o se anula, se desimputa desde el cobro/pago más reciente; el excedente queda como anticipo (la edición no se rechaza por esto).
5. **Venta de producción propia por partida, las más antiguas primero** ([[ADR-012-Rentabilidad-por-partida]]): la salida se parte en varias partidas si hace falta.
6. **Gastos al costo del ciclo, neto de IVA:** líneas de gasto de compras y gastos de caja con destino en un ciclo se suman al resumen del ciclo al consultarlo (no se guardan). Destino en ciclo finalizado: rechazado, así el costo congelado no cambia.

## Consecuencias
- ➕ Stock, cuenta corriente y costos quedan consistentes ante cualquier edición.
- ➕ Anticipos y pagos parciales sin lógica especial.
- ➖ Calcular saldos recorre comprobantes y cobros; si el volumen crece mucho, se puede cachear (no hace falta a esta escala).
