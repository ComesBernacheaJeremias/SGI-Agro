---
tags: [arquitectura, seguridad]
actualizado: 2026-09-28
---

# Seguridad

Estado real (revisado en el código el 27/09/2026). Decisiones: [[ADR-008-Autenticacion-y-roles]], [[ADR-022-Infraestructura-de-produccion]], [[ADR-023-Endurecimiento-de-seguridad]].

## Autenticación y sesiones
- Contraseñas con hash **Argon2id**; mínimo 10 caracteres.
- **Access token** JWT de 15 min, solo en memoria del navegador. **Sesión** (refresh) de 30 días en cookie `HttpOnly; Secure; SameSite=Strict`, limitada a `/api/v1/auth`; se rota en cada uso, se guarda solo su hash y **reusar una vieja cierra todas las sesiones** del usuario.
- Mismo mensaje y mismo tiempo de respuesta para usuario inexistente y contraseña mala (no se puede averiguar qué usuarios existen).
- **Bloqueo por usuario**: 5 intentos fallidos → 15 min. **Tope por IP**: 20 intentos fallidos en 10 min desde la misma IP → 429 (frena probar una contraseña contra todos los usuarios).
- **Registro de accesos** (`login_events`): cada intento con usuario, IP, dispositivo y resultado; se ve en *Historial → Accesos*.
- Se cierran todas las sesiones al: desactivar el usuario, resetearle la contraseña, cambiar la propia (queda solo la actual), o con **Cerrar sesiones** (administrador, ej. celular perdido) / `revoke-sessions` por consola.
- El dispositivo **no guarda datos del negocio** ([[ADR-024-Sin-carga-offline]]); al cerrar sesión se borra lo que quedó en memoria.

## Permisos y datos
- Permisos `modulo:accion` verificados **en el servidor en cada endpoint**; el frontend solo oculta.
- Consultas solo vía ORM con parámetros (sin SQL armado a mano con datos del usuario).
- Validación estricta de entrada (Pydantic); archivos subidos hasta 5 MB en la app y 10 MB en Caddy.
- Historial (auditoría) de todo alta, cambio y anulación.
- Errores inesperados: mensaje genérico al usuario, detalle solo en los logs (y en Sentry, sin datos personales).

## Aplicación web (producción, Caddy)
- HTTPS automático (Let's Encrypt) y **HSTS** (1 año).
- **CSP**: solo se ejecuta código del propio sitio (`script-src 'self'`), sin iframes ajenos (`frame-ancestors 'none'`).
- `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`; sin encabezado `Server`.
- Mismo origen para app y API (sin CORS abierto).
- Documentación de la API (Swagger/OpenAPI) desactivada en producción.
- **Tope general por IP**: 600 pedidos/min por proceso de la API (≈1.200 con 2 procesos) → 429.

## Servidor y contenedores
- La API corre **sin root** dentro del contenedor.
- PostgreSQL sin puerto publicado. **Dos usuarios de base**: administrador (solo inicialización y backups/restauración) y **usuario de la aplicación sin superusuario**, dueño solo de su base. La API **no recibe** la clave del administrador.
- La API **no arranca en producción** si `JWT_SECRET` o la contraseña de la base son débiles o de ejemplo.
- `deploy/harden.sh` (una vez, al crear el droplet): SSH solo con clave, `fail2ban`, actualizaciones de seguridad automáticas, `ufw` con 22/80/443. Además, firewall de red de DigitalOcean con 22/80/443.
- `deploy/.env` con permisos 600.
- Backups diarios a Spaces (bucket privado), restauración probada.

## Código y dependencias
- `.env` fuera de git; `.env.example` / `.env.prod.example` sin valores reales.
- **GitHub Actions** en cada push: formato, lint, tipos, tests, build, `pip-audit`, `npm audit` y `gitleaks` (secretos); además los lunes, para vulnerabilidades nuevas.
- **Dependabot**: PRs semanales con actualizaciones (backend, frontend), mensuales para imágenes Docker y acciones.
- `pre-commit` configurado (formato, lint, gitleaks) — instalación local opcional.

## No incluido (a evaluar)
- Doble factor (TOTP) para Dueño y Soporte.
- Backups cifrados antes de subirlos a Spaces.
- Envío de alertas ante muchos accesos fallidos (hoy se ven en *Historial → Accesos*).
