---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-006 · Carga sin conexión limitada, para dueño y secretario

## Contexto
Dueño y secretario tienen conexión pero quieren poder cargar sin señal "por las dudas". Los empleados no usan el sistema. Un sistema 100 % offline es muy costoso.

## Decisión
- PWA instalable. Sin conexión se cargan **labores, cosechas, movimientos de stock simples y preparaciones**. El resto requiere conexión.
- IDs generados en el cliente + endpoints idempotentes; el servidor revalida; los conflictos los resuelve el usuario.
- Se prepara desde F1 (IDs) y se habilita en F7.
Detalle: [[Offline-y-sincronizacion]].

## Consecuencias
- ➕ Cubre la necesidad con complejidad acotada; deja la base para una futura app de empleados.
- ➖ Un registro offline puede fallar al sincronizar (ej. stock consumido mientras tanto) → aviso claro al usuario.
