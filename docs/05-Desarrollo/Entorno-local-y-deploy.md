---
tags: [desarrollo, infraestructura]
actualizado: 2026-09-30
---

# Entorno local y deploy

Decisión: [[ADR-007-Local-y-DigitalOcean]].

## Local (todo el desarrollo)
Docker Compose con tres servicios:
- `db`: PostgreSQL 16 (datos en un volumen persistente).
- `api`: FastAPI con recarga automática al guardar.
- `web`: Vite con recarga automática.

```bash
./dev.sh           # levanta todo y muestra los logs de api y web; Ctrl+C lo apaga (docker compose stop)
./dev.sh --build   # reconstruye las imágenes antes (tras cambiar dependencias)
# API y Swagger: http://localhost:8000/api/docs
# Frontend:      http://localhost:5173
```
`dev.sh` crea el `.env` desde `.env.example` si falta. Los datos quedan en el volumen `db_data`.
Datos de prueba: script `seed` con establecimientos, lotes, productos y ciclos de ejemplo.

## Producción (F7, DigitalOcean)
Decisiones: [[ADR-007-Local-y-DigitalOcean]], [[ADR-022-Infraestructura-de-produccion]]. Archivos en `deploy/`:

| Archivo | Qué es |
|---|---|
| `docker-compose.prod.yml` | Proyecto `sgi-agro-prod`: `web` (Caddy: HTTPS + app compilada + `/api` → API), `api` (sin recarga, 2 procesos, migraciones al arrancar), `db` (PostgreSQL 16, sin puertos publicados), `backup`. |
| `web.Dockerfile` | Compila el frontend (`npm run build`) y lo sirve con Caddy. |
| `Caddyfile` | Dominio, encabezados de seguridad, caché (archivos con hash: 1 año; index/service worker: sin caché). |
| `backup/` | `pg_dump` diario (formato custom) a la hora `BACKUP_HOUR`; 7 días en el servidor y 30 en Spaces (rclone). |
| `deploy.sh` | `git pull` + build + `up -d` (anota la versión en `APP_VERSION`). |
| `restore.sh` | Lista backups (servidor y Spaces) y restaura uno; antes hace un backup "antes-de-restaurar". |
| `postgres-init/` | Primera inicialización: usuario de la aplicación sin superusuario, dueño de su base. |
| `harden.sh` | Endurece el droplet: SSH solo con clave, fail2ban, actualizaciones automáticas, ufw. |
| `.env.prod.example` | Variables de producción (se copia a `deploy/.env`, que nunca se sube). |

Probado en local (27/09/2026, proyecto aparte `sgi-agro-prodtest`): app y rutas por Caddy, API detrás del proxy, Swagger oculto en producción, backup y **restauración verificada** (la base vuelve al momento del backup).

### Primera instalación (paso a paso)
1. **DigitalOcean:** crear un droplet Ubuntu 24.04, 2 GB / 1 vCPU (~USD 12/mes), región Nueva York o San Francisco, con backups semanales del droplet activados (~USD 2,40/mes) y acceso por clave SSH.
2. **Firewall** (panel de DigitalOcean → Networking → Firewalls): permitir solo 22 (SSH), 80 y 443.
3. **Endurecer y Docker** en el droplet: copiar `deploy/harden.sh` y correr `sh harden.sh` (con la clave SSH ya funcionando); después `curl -fsSL https://get.docker.com | sh`.
4. **Código:** en el droplet, `git clone <repo privado> /opt/sgi-agro` (con una deploy key de solo lectura del repositorio).
5. **Dominio:** en el DNS del dominio, un registro `A` `gestion.empresa.com.ar` → IP del droplet.
6. **Spaces:** crear un bucket privado (ej. `sgi-agro-backups`) y una clave de acceso (Spaces Keys).
7. **Variables:** `cd /opt/sgi-agro/deploy && cp .env.prod.example .env` y completar: `DOMAIN`, `DB_ADMIN_PASSWORD`, `POSTGRES_PASSWORD` y `JWT_SECRET` (aleatorias, ver comentarios; con valores débiles la API no arranca), `SPACES_*`, opcional `SENTRY_DSN`.
8. **Publicar:** `./deploy.sh` → Caddy saca el certificado HTTPS solo.
9. **Primer usuario:** `docker compose -f docker-compose.prod.yml exec api python -m app.cli create-user` (rol `support` para el desarrollador y `owner` para el dueño). Otros comandos: `list-users`, `reset-password`, `deactivate-user`, `activate-user`, `revoke-sessions` (los usuarios no se borran, se desactivan).
10. **Probar el backup:** `docker compose -f docker-compose.prod.yml exec backup backup.sh now` → ver que aparezca en Spaces; `./restore.sh` lista los disponibles. Hacer una restauración de prueba **antes** de la carga real.
11. **Monitoreo:** en DigitalOcean, alertas de CPU > 80 %, memoria > 85 % y disco > 80 % por email. En Sentry (si se usa), alertas por email ante errores nuevos.

### Actualizar a una versión nueva
En el droplet: `cd /opt/sgi-agro/deploy && ./deploy.sh`. Las migraciones corren solas al arrancar la API; la app instalada en los dispositivos se actualiza sola (service worker).

### Operación
- Logs: `docker compose -f docker-compose.prod.yml logs -f api` (en JSON).
- Estado: `docker compose -f docker-compose.prod.yml ps`.
- Restaurar: `./restore.sh` (lista) y `./restore.sh <archivo>` (pide escribir RESTAURAR).
