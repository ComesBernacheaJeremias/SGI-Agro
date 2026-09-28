---
tags: [arquitectura, stack]
actualizado: 2026-09-27
---

# Stack tecnológico

Justificación: [[ADR-002-Stack-Python-FastAPI-React]].

> Versiones exactas: `backend/uv.lock` y `frontend/package-lock.json`. Al 27/09/2026: FastAPI 0.141, SQLAlchemy 2.1, Pydantic 2.13, Alembic 1.20, React 19, Mantine 9, Vite 8, Vitest 5, ESLint 10.
>
> **Notas de versiones**
> - **TypeScript 5.9 (no 7):** `typescript-eslint` y `openapi-typescript` todavía no soportan TS 6/7. Revisar al actualizar.
> - **httpx2** (no httpx) para los tests: Starlette deprecó `httpx` en su `TestClient`.
> - Transacción por request con `Depends(get_db, scope="function")`: el commit ocurre **antes** de enviar la respuesta.

## Backend
| Pieza | Elección | Para qué |
|---|---|---|
| Lenguaje | Python 3.12 | |
| Framework | FastAPI | API REST + documentación Swagger automática |
| ORM | SQLAlchemy 2.0 (sync) | Modelos y consultas |
| Migraciones | Alembic | Esquema versionado (fuente de verdad del esquema) |
| Validación / config | Pydantic v2 + pydantic-settings | Entrada/salida y variables de entorno |
| Base de datos | PostgreSQL 16 | |
| Auth | PyJWT + argon2-cffi | [[ADR-008-Autenticacion-y-roles]] |
| Reportes | SQL + openpyxl (Excel) + reportlab (PDF) | reportlab en lugar de WeasyPrint: sin librerías del sistema ([[ADR-019-Reportes-y-resultado-de-gestion]]) |
| Logs | structlog (JSON) | [[Observabilidad]] |
| Dependencias | uv | |
| Calidad | Ruff (lint + formato), mypy, pytest | [[Convenciones-de-codigo]] |

## Frontend
| Pieza | Elección | Para qué |
|---|---|---|
| Lenguaje | TypeScript (strict) | |
| Framework | React + Vite | |
| Componentes UI | Mantine | Formularios, tablas, fechas en español |
| Datos del servidor | TanStack Query | Caché, reintentos, estados de carga |
| Ruteo | React Router | |
| Formularios | @mantine/form | Integrado con los inputs de Mantine ([[ADR-015-Piezas-CRUD-genericas]]) |
| Modales / confirmaciones | @mantine/modals | "¿Estás seguro?" |
| Íconos | @tabler/icons-react | |
| Cliente de API | Generado desde OpenAPI (`openapi-typescript` + `openapi-fetch`) | Tipos del backend sin escribirlos a mano |
| App instalable | vite-plugin-pwa (sin carga sin conexión) | [[ADR-024-Sin-carga-offline]] |
| Calidad | ESLint, Prettier, Vitest | |

## Entorno y deploy
| Pieza | Elección |
|---|---|
| Local | Docker Compose (db + api + web) |
| Producción (F7) | Droplet de DigitalOcean con Docker Compose + Caddy (HTTPS automático) |
| Errores (producción) | Sentry (plan gratuito) |
| Repositorio | GitHub privado (el usuario ejecuta los comandos de git) |
