---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-020 · Medidor estimado, planes de mantenimiento y costo real de activos

## Contexto
F6 agrega mantenimientos con avisos y el costo real de cada activo. Los avisos dependen de las horas/km, que no siempre se leen del tablero; y el servicio de taller ya se carga como compra con destino = activo ([[ADR-018-Comprobantes-comerciales]]).

## Decisión
1. **Lectura actual estimada** = última lectura cargada (a mano o en un mantenimiento) + horas/km de las labores posteriores. Sin lecturas: suma del uso en labores.
2. **Plan de mantenimiento** por activo: cada X horas/km y/o cada N meses, lo que llegue primero, contado desde el último mantenimiento de ese plan (o desde el inicio del plan). Estados: al día / **próximo** (falta ≤ 10 % del intervalo o ≤ 15 días) / **vencido**.
3. **Mantenimiento:** los repuestos salen del stock como consumo con dimensión activo (costo promedio); el **servicio externo es la compra** con destino = activo, que se vincula al mantenimiento (no se carga un importe aparte, así no se duplica).
4. **Costo real del activo** en un período = gastos con destino al activo (compras y caja) + repuestos; **costo real por hora/km** = eso ÷ uso en labores. Se compara con la tarifa (que sigue siendo lo que se imputa a los ciclos, [[ADR-017-Costo-derivado-y-cascada]]). La ficha muestra los últimos 12 meses por defecto, con filtro.
5. En el **resultado de gestión** los repuestos suman a "Costos de producción" (gasto real, coherente con [[ADR-019-Reportes-y-resultado-de-gestion]]).

## Consecuencias
- ➕ Los avisos funcionan aunque no carguen lecturas seguido; cargar una lectura corrige la estimación.
- ➕ El dueño ve si la tarifa está bien calibrada.
- ➖ Si una labor carga mal las horas, el medidor estimado se desvía hasta la próxima lectura.
