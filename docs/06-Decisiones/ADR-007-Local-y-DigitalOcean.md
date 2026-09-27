---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-007 · Desarrollo en local y deploy final a DigitalOcean

## Contexto
No hay servidor todavía. El desarrollador trabaja en local y despliega al final.

## Decisión
- Todo el desarrollo en **local con Docker Compose** (db, api, web).
- Deploy a **DigitalOcean** en F7: un droplet con Docker Compose + Caddy (HTTPS) + backups a Spaces.
- Sin entorno de pruebas separado, sin Terraform ni pipeline de deploy por ahora (se reevalúa en F7).
Detalle: [[Entorno-local-y-deploy]].

## Consecuencias
- ➕ Simple y sin costos hasta la puesta en marcha. Docker garantiza que local y servidor se comporten igual.
- ➖ El cliente solo puede probar cuando el desarrollador le muestra en local, hasta F7.
