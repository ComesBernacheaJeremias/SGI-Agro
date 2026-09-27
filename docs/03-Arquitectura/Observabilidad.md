---
tags: [arquitectura, observabilidad]
actualizado: 2026-09-27
---

# Observabilidad

Lo mínimo que funciona para un solo servidor.

| Necesidad | Cómo | Desde |
|---|---|---|
| Logs | structlog en JSON a la consola (`docker compose logs`). Cada request con `request_id`, usuario, ruta, status y duración. El `request_id` se muestra en los errores de la UI para rastrearlos. | F0 |
| Salud | `GET /api/health` (app viva) y `/api/health/ready` (base accesible) | F0 |
| Errores | Sentry (backend y frontend), sin datos sensibles | F7 |
| Servidor | Monitoreo de DigitalOcean (CPU, RAM, disco) + alerta si `/api/health` no responde | F7 |
| Backups | El script avisa si falla | F7 |
