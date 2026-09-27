---
tags: [adr]
estado: aceptada
fecha: 2026-09-26
---

# ADR-001 · Desarrollo desde cero (sin Odoo)

## Contexto
La propuesta original ([[Propuesta-original]]) usaba Odoo como base. Odoo resuelve mucho pero obliga a adaptarse a su modelo y limita la personalización.

## Decisión
Desarrollar el sistema **desde cero** con las mismas funcionalidades del PDF.

## Consecuencias
- ➕ Control total; se personaliza según lo que pida el cliente; modelo de datos hecho para este negocio.
- ➕ Código propio, reutilizable para otros productores (en otras instancias).
- ➖ Más esfuerzo: usuarios, historial, reportes, etc. se construyen. Se compensa acotando alcance ([[ADR-011-Gestion-sin-contabilidad-formal]]).
