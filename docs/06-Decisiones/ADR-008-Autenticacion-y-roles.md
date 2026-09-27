---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-008 · Autenticación JWT y roles con permisos

## Contexto
SPA/PWA con pocos usuarios, sin login con proveedores externos. Se necesitan sesiones revocables y un rol del desarrollador por encima del dueño (para reabrir ciclos).

## Decisión
- Usuario + contraseña (Argon2id).
- Access token JWT de 15 min en memoria + refresh token de 30 días (rotativo, con hash en la base) en cookie `HttpOnly`.
- Roles con permisos `modulo:accion`: `support` (desarrollador, todo + reabrir ciclos), `owner` (dueño), `staff` (secretario), `read_only`.
- **Un rol por usuario** (actualización F1, 27/09): con 3 usuarios alcanza y la UI es más simple.
- **Roles fijos calculados** (`support`, `owner`, `read_only`): sus permisos se derivan del catálogo en código, así que los módulos nuevos no requieren tocar esos roles. `staff` y los roles creados por el usuario guardan sus permisos.
- **Un rol por usuario** (actualización F1, 27/09): con 3 usuarios alcanza y la UI es más simple.
- **Roles fijos calculados** (`support`, `owner`, `read_only`): sus permisos se derivan del catálogo en código, así que los módulos nuevos no requieren tocar esos roles. `staff` y los roles creados por el usuario guardan sus permisos.
- **Un rol por usuario** (actualización F1, 27/09): con 3 usuarios alcanza y la UI es más simple.
- **Roles fijos calculados** (`support`, `owner`, `read_only`): sus permisos se derivan del catálogo en código, así que los módulos nuevos no requieren tocar esos roles. `staff` y los roles creados por el usuario guardan sus permisos.
- Verificación de permisos en cada endpoint.
Detalle: [[Seguridad]], [[Actores-y-roles]].

## Consecuencias
- ➕ Sesiones revocables, token de refresco inaccesible desde JavaScript, permisos editables.
- ➖ Rotación y revocación requieren tests dedicados.
