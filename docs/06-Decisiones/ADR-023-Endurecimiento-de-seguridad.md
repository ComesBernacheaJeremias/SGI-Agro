---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-023 · Endurecimiento de seguridad antes de salir a producción

## Contexto
Revisión de seguridad pedida por el usuario (27/09) antes del deploy. La base ya era sólida (Argon2id, sesiones rotativas en cookie segura, permisos en el servidor, ORM, auditoría), pero había huecos y la documentación prometía cosas no hechas (Dependabot, auditoría de dependencias, contenedores sin root).

## Decisión (aprobada: puntos 1 a 8)
1. **Topes por IP**: 20 intentos de login fallidos en 10 min (en la base, vale entre procesos) y 600 pedidos/min por proceso (en memoria, solo en producción).
2. **Encabezados** en Caddy: CSP estricta (`script-src 'self'`; `style-src` admite inline por los estilos de Mantine), HSTS, COOP y tope de 10 MB por pedido.
3. **Mínimo privilegio**: API sin root; usuario de base de la aplicación sin superusuario (dueño de su base; `unaccent` es una extensión "trusted"); la API recibe variables explícitas, no el `.env` completo; backups con el administrador y restauración como el usuario de la app.
4. **CI en GitHub** (tests, tipos, lint, build, `pip-audit`, `npm audit`, `gitleaks`) + **Dependabot**.
5. **`harden.sh`** para el droplet (SSH solo con clave, fail2ban, actualizaciones automáticas, ufw).
6. **Dispositivos**: al cerrar sesión se borran los datos guardados para usar sin señal (desde el 28/09 ya no se guardan: [[ADR-024-Sin-carga-offline]]); el administrador puede cerrar todas las sesiones de un usuario; cambiar la propia contraseña cierra las demás sesiones.
7. **Arranque seguro**: en producción la API no inicia con secretos débiles o de ejemplo.
8. **Registro de accesos** con IP y resultado, visible en *Historial → Accesos*.
Además: comandos de consola para administrar usuarios (`list-users`, `reset-password`, `deactivate-user`, `activate-user`, `revoke-sessions`); los usuarios se desactivan, no se borran (el historial conserva quién hizo qué).

## Consecuencias
- ➕ Probado en local con el compose de producción: CSP/HSTS presentes, usuario de base sin superusuario (migraciones y restauración OK), 429 por IP en login y en la API, 413 por encima de 10 MB.
- ➖ El tope general es por proceso (aproximado); para algo exacto haría falta un almacén compartido (Redis): no se justifica hoy.
- ➖ La CSP admite estilos inline; eliminarlo exigiría cambiar la librería de componentes.
