---
modulo: M01
codigo: identity (+ core/audit)
etapa: F1
estado: implementado
depende_de: []
actualizado: 2026-09-27
---

# M01 · Núcleo: usuarios, roles, historial

## Objetivo
Controlar quién entra, qué puede hacer y registrar todo lo que se hace (PDF 2.7).

## Historias de usuario

**HU-01-01 · Iniciar sesión**
- Dado un usuario activo con credenciales correctas, cuando ingresa, entonces entra al tablero y la sesión se mantiene hasta 30 días.
- Con credenciales incorrectas ve "Usuario o contraseña incorrectos" (sin indicar cuál falló).
- Tras 5 intentos fallidos la cuenta se bloquea 15 minutos.

**HU-01-02 · Cerrar sesión** — revoca la sesión actual; opción "cerrar todas las sesiones".

**HU-01-03 · Gestionar usuarios** (`owner`, `support`)
- Crear, editar, desactivar (no borrar) y asignar roles.
- Un usuario desactivado no puede entrar y sus sesiones se revocan.

**HU-01-04 · Gestionar roles** — crear/editar roles eligiendo permisos agrupados por módulo. Los roles `support` y `owner` no se eliminan.

**HU-01-05 · Cambiar mi contraseña** — requiere la actual; mínimo 10 caracteres.

**HU-01-06 · Ver historial de un registro**
- En cada registro (labor, compra, producto…) una pestaña "Historial": fecha, usuario, acción (creó / editó / anuló / reabrió) y qué cambió (antes → después).

**HU-01-07 · Consultar historial general** (`owner`, `support`) — filtrable por usuario, módulo, fecha y acción.

## Reglas de negocio
- El historial se graba **automáticamente** en `core/audit` (listener de SQLAlchemy) en la misma transacción; ningún módulo tiene que acordarse de hacerlo.
- El historial no se edita ni se borra.
- Permisos `modulo:accion`: `read`, `create`, `update`, `cancel`, `admin`. Especial: `production:reopen_cycle` (solo `support`).

## Datos
`users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `refresh_tokens`, `audit_log`.

## Pantallas
Login · Mi perfil · Usuarios · Roles · Historial general · Componente "Historial" reutilizable.

## Endpoints (tentativo)
`POST /auth/login` · `/auth/refresh` · `/auth/logout` · `GET /auth/me` · `/users` · `/roles` · `/permissions` · `GET /audit`

## Decisiones
[[ADR-008-Autenticacion-y-roles]] · [[ADR-004-Edicion-auditoria-y-bloqueo]]

## Implementación

### F0 (2026-09-27) — login mínimo ✅
| Historia | Estado |
|---|---|
| HU-01-01 Iniciar sesión (incl. bloqueo tras 5 intentos) | ✅ |
| HU-01-02 Cerrar sesión / cerrar todas | ✅ |
| HU-01-03 a 07 (usuarios, roles, permisos, historial) | ✅ F1 |

**Backend** (`backend/app/modules/identity/`)
- `models.py`: `User` (usuario único sin distinguir mayúsculas vía índice `lower(username)`, intentos fallidos, bloqueo) y `SessionToken` (refresh de 30 días; se guarda solo el hash SHA-256).
- `service.py` → `AuthService`: `create_user`, `login`, `refresh` (rota el token), `logout`, `logout_all`.
  - Usuario inexistente: se verifica contra un hash ficticio para que el tiempo de respuesta no revele qué usuarios existen.
  - **Reutilización de un token ya rotado** (posible robo) → se revocan todas las sesiones del usuario.
  - Excepción documentada a "el service no hace commit": los intentos fallidos y las revocaciones se confirman aunque la operación termine en error.
- `dependencies.py` → `CurrentUser`: exige `Authorization: Bearer <token>` y setea el usuario en el contexto (autoría automática `created_by`/`updated_by` y logs).
- `router.py`: `POST /api/v1/auth/login|refresh|logout|logout-all`, `GET /api/v1/auth/me`. Cookie `sgi_session` (`HttpOnly`, `SameSite=Strict`, `Secure` en producción, `path=/api/v1/auth`).
- `app/cli.py`: `docker compose exec api python -m app.cli create-user`.
- Migración: `20260927_0058_create_users_and_session_tokens`.
- Tests: `tests/integration/test_auth.py` (10), `tests/unit/test_security.py` (4).

**Frontend**
- `src/app/auth/session.ts`: estado de sesión (token solo en memoria).
- `src/api/client.ts`: agrega el token a cada request; ante 401 renueva la sesión **una sola vez** (compartida entre llamadas simultáneas) y reintenta.
- `src/app/auth/RequireAuth.tsx`, `src/modules/auth/LoginPage.tsx`; al abrir la app se restaura la sesión con la cookie.

### F1 (2026-09-27) — usuarios, roles, permisos, historial ✅

**Roles y permisos** ([[ADR-008-Autenticacion-y-roles]])
- **Un rol por usuario** (`users.role_id`).
- Permisos definidos en código: cada módulo los declara en su `permissions.py` con `define_permission(...)` y se registran en `app/permissions.py`. Se usan como constantes: `Annotated[User, require(USERS_MANAGE)]`.
- Roles fijos con permisos **calculados** (`authorization.py` → `COMPUTED_ROLES`): `support` (todo), `owner` (todo menos `support_only`), `read_only` (todo `:read`). Se actualizan solos al agregar módulos.
- Roles editables (`staff` y los que se creen): permisos guardados en `role_permissions`. Cada migración de un módulo nuevo agrega a mano los permisos por defecto de `staff`.
- Reglas (`user_service.py`): solo `support` asigna el rol Soporte o modifica usuarios de Soporte; nadie se desactiva a sí mismo; desactivar o resetear contraseña cierra sus sesiones. Roles fijos no se editan (salvo permisos de `staff`); un rol con usuarios no se elimina; los permisos `support_only` no se asignan a roles.
- Permisos actuales: `users:read`, `users:manage`, `audit:read` (+ los de cada módulo).

**Historial** (`app/core/audit.py` + módulo `audit`)
- Listener `after_flush`: por cada alta/edición/baja de un `BaseModel` inserta en `audit_log` los campos cambiados (antes → después), usuario y request id, en la misma transacción. Acciones: create, update, deactivate, activate, cancel, delete.
- Metadatos para mostrarlo: `__label__`, `__display__`, `info={"label", "choices", "audit"}`, `relationship(info={"audit_key"})` (ver [[Guia-nueva-entidad]]).
- API: `GET /api/v1/audit/records/{tabla}/{id}` (cualquier usuario logueado) y `GET /api/v1/audit` con filtros (permiso `audit:read`). Traduce campos, opciones y referencias (FK → nombre actual).

**Contexto del request** (`app/core/context.py`): FastAPI ejecuta dependencias y endpoints sync en hilos distintos; el middleware crea un `RequestContext` compartido donde la autenticación deja el usuario (autoría, historial y logs).

**Estructura del módulo** (dividido por tema): `auth_service/auth_router` (sesión, cambio de contraseña), `user_service/user_router`, `role_service/role_router` (+ `/api/v1/permissions`), `authorization.py`, `dependencies.py`.

**Frontend**: `modules/users` (pestañas Usuarios y Roles, panel de usuario con resetear contraseña, panel de rol con permisos por grupo), `modules/profile` (Mi perfil: cambiar contraseña, cerrar todas las sesiones), `modules/audit` (historial general con filtros). Menú filtrado por permisos (`useCan`).

**Tests**: `test_permissions.py`, `test_audit.py`, `test_users.py`, `test_roles.py`.
