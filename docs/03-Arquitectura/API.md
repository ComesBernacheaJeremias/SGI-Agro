---
tags: [arquitectura, api]
actualizado: 2026-09-27
---

# API

## Documentación interactiva
FastAPI genera la especificación **OpenAPI** sola:
- Swagger: `http://localhost:8000/api/docs` · ReDoc: `/api/redoc` · JSON: `/api/openapi.json`
- En producción, detrás de login.
- El frontend genera su cliente tipado desde `openapi.json` (`npm run gen:api`): si cambia un contrato del backend, el frontend no compila hasta adaptarse.

## Convenciones
| Tema | Regla |
|---|---|
| Prefijo | `/api/v1/...` |
| Recursos | Inglés, plural, kebab-case: `/api/v1/crop-cycles` |
| Verbos | `GET` lista/detalle · `POST` crear · `PATCH` editar · `POST /{id}/cancel` anular (no hay `DELETE` en registros operativos) |
| Acciones | `POST /crop-cycles/{id}/finish`, `POST /crop-cycles/{id}/reopen` (solo `support`) |
| Paginación | `?page=1&page_size=50` → `{ items, total, page, page_size }` |
| Filtros | Query params: `?plot_id=...&date_from=2026-07-01&date_to=...` |
| Orden | `?sort=-date` |
| Fechas | ISO 8601 |
| Decimales | Como **string** en JSON (`"1234.56"`) para no perder precisión |
| IDs | UUID; al crear, el cliente **puede** enviar el `id` (si se reintenta el guardado no duplica, [[ADR-024-Sin-carga-offline]]) |
| Errores | `{ "error": { "code": "INSUFFICIENT_STOCK", "message": "No alcanza el stock de Glifosato en Depósito Central (hay 3 L)", "details": {} } }` |
| Status | 200/201 ok · 401 no autenticado · 403 sin permiso · 404 · 409 regla de negocio (ciclo cerrado, stock insuficiente) · 422 datos inválidos |

La confirmación "¿Estás seguro?" al editar es del frontend; el backend valida las reglas y registra la auditoría.
