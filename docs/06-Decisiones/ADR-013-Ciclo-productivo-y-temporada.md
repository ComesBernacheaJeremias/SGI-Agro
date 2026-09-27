---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-013 · Ciclo productivo y temporada como conceptos separados

## Contexto
El cliente produce hortalizas (ciclos de meses), frutas (montes que producen durante décadas) y madera (ciclos de 15–20 años). "Costo por lote" no alcanza.

## Decisión
- **Ciclo productivo** = un cultivo en (parte de) un lote entre dos fechas. Estados: planificado → en curso → finalizado. Acumula costos.
  - Comienza con el primer trabajo (incluida la preparación de suelo).
  - Termina cuando el usuario lo finaliza (hortalizas: última cosecha — el sistema pregunta "¿es la cosecha final?"; frutales: arranque; forestal: tala final).
  - Finalizado = bloqueado; solo `support` lo reabre ([[ADR-004-Edicion-auditoria-y-bloqueo]]).
  - Un lote puede tener varios ciclos a la vez; la suma de hectáreas activas no supera la del lote.
- **Temporada** = período **1/7 → 30/6**, única para toda la empresa. La crea el dueño; termina sola. Los registros caen en una temporada por su fecha. Sirve para analizar ciclos largos y comparar años.

## Consecuencias
- ➕ Ciclos cortos se analizan por ciclo; largos por temporada; ambos salen de los mismos datos.
- ➕ Modelo único para frutas, hortalizas y madera.
