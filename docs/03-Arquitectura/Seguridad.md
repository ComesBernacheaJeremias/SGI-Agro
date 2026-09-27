---
tags: [arquitectura, seguridad]
actualizado: 2026-09-27
---

# Seguridad

## Autenticación y permisos ([[ADR-008-Autenticacion-y-roles]])
- Usuario + contraseña; hash **Argon2id**.
- **Access token** JWT corto (15 min) en memoria del frontend + **refresh token** (30 días, rotativo, guardado con hash en la base) en cookie `HttpOnly; Secure; SameSite=Strict`.
- Sesiones revocables (logout, usuario desactivado).
- Bloqueo temporal tras 5 intentos fallidos.
- Permisos `modulo:accion` verificados en **cada endpoint** del backend; el frontend solo oculta lo que no corresponde.

## Secretos
- `.env` local (en `.gitignore`); el repo tiene `.env.example` sin valores reales.
- En producción: `.env` en el servidor con permisos restringidos.
- Nunca secretos en logs.
- `gitleaks` en pre-commit para detectar secretos antes de commitear.

## Dependencias
- `pip-audit` y `npm audit` (se corren periódicamente y antes de cada deploy).
- Dependabot en GitHub (avisos de versiones vulnerables).

## Aplicación
- HTTPS en producción (Caddy + Let's Encrypt).
- CORS restringido al dominio del frontend.
- Consultas solo vía ORM / parámetros.
- Validación estricta de entrada (Pydantic).

## Servidor (F7)
- Firewall: solo 80/443 públicos; SSH solo con clave.
- PostgreSQL no expuesto a internet.
- Contenedores sin usuario root.
- Backups diarios fuera del servidor.
