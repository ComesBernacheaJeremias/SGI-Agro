---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-022 · Infraestructura de producción

## Contexto
Hay que publicar el sistema para un solo cliente con costo bajo y operación simple ([[ADR-007-Local-y-DigitalOcean]]). Pendientes de F7: tamaño del servidor, base administrada o no, dominio, entorno de pruebas.

## Decisión
1. **Un droplet de 2 GB** con Docker Compose (proyecto `sgi-agro-prod`): Caddy + API + PostgreSQL + backup. Mismas imágenes que en desarrollo.
2. **PostgreSQL en el mismo droplet** (no la base administrada: +USD 15/mes innecesarios para un cliente), sin puerto publicado.
3. **Backups:** `pg_dump` diario en formato custom, 7 días en el servidor y **30 días en DigitalOcean Spaces** (rclone), + snapshots semanales del droplet. Restauración con script que primero guarda un backup del estado actual. Probada antes de salir.
4. **Caddy** con HTTPS automático (Let's Encrypt) y encabezados de seguridad; la API no se expone directamente.
5. **Producción endurecida:** documentación de la API (Swagger/OpenAPI) desactivada, cookie de sesión `secure`, bloqueo de cuenta por intentos fallidos (ya existente), secretos solo en `deploy/.env`.
6. **Errores:** Sentry opcional (`SENTRY_DSN`), sin datos personales. Monitoreo con las alertas de DigitalOcean.
7. **Deploy:** `git pull` + build en el servidor (`deploy.sh`); sin registro de imágenes ni pipeline por ahora. **Sin entorno de pruebas separado**: se prueba en local con el mismo compose de producción.

## Consecuencias
- ➕ ~USD 20/mes en total (droplet + backups + Spaces), un solo servidor fácil de entender.
- ➕ Un backup restaurado es la única prueba de que los backups sirven: queda en el procedimiento.
- ➖ La base comparte recursos con la app; si el volumen crece mucho, se pasa a la base administrada (cambio de `DB_HOST`).
- ➖ Build en el servidor: cada deploy tarda unos minutos.
