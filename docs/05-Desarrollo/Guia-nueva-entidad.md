---
tags: [desarrollo, guia]
actualizado: 2026-09-27
---

# Guía: agregar una entidad (maestro) nueva

Receta para sumar una entidad con alta / edición / activación, sin repetir código.
Ejemplo real: [[M02-Maestros]] (`backend/app/modules/masterdata`, `frontend/src/modules/masterdata`).
Decisión: [[ADR-015-Piezas-CRUD-genericas]].

## Backend

1. **Modelo** (`models.py`): heredar de `BaseModel` (id UUIDv7, fechas y autoría automáticas).
   - `__label__ = "Producto"` y `__display__ = "name"` → cómo se muestra en el historial.
   - Cada columna con `info={"label": "..."}`; opciones con `info={"label": ..., "choices": LABELS}`.
   - Columnas técnicas: `info={"audit": False}`. Tabla sin historial propio: `__audited__ = False`.
   - Colecciones hijas que deben verse en el historial: `relationship(..., info={"label": ..., "audit_key": "<atributo>"})`.
   - Registrar el modelo en `app/models.py`.
2. **Permisos** (`permissions.py`): `define_permission("modulo:accion", "Grupo", "Etiqueta")`; importarlo en `app/permissions.py`.
3. **Schemas** (`schemas.py`): `XOut`, `XCreate`, `XUpdate` (en Update todo opcional: es PATCH).
4. **Repository** (`repository.py`): `class XRepository(CrudRepository[X])` con `model`, `search_fields`, `default_sort`; `apply_filters` si hay filtros propios.
5. **Service** (`service.py`): `class XService(CrudService[X, XCreate, XUpdate])` con `repository_class`, `unique_fields`, `not_found_message`. Reglas en `validate()` (llamar a `super().validate(obj)`); transformaciones en `values_for_create()` / `values_for_update()`.
6. **Router**: `crud_router(prefix=..., tag=..., service=XService, out=XOut, create=XCreate, update=XUpdate, permissions=CrudPermissions(...), filters=<dependencia opcional>)`; registrar en `app/main.py`.
7. **Migración**: `docker compose exec api alembic revision --autogenerate -m "..."`; revisar el archivo (enums: agregar el `drop` en `downgrade`; datos iniciales y permisos por defecto del rol `staff` a mano).
8. **Tests** (`tests/integration/test_<modulo>.py`): reglas de negocio, únicos, filtros, permisos.

## Frontend

1. `npm run gen:api` (con la API levantada) → tipos nuevos en `src/api/schema.d.ts`.
2. **Recurso** (`modules/<modulo>/api.ts`): `createCrudResource<XOut, XCreate, XUpdate>({ path, key, label, table })`.
3. **Pestaña** (`XTab.tsx`): `<CrudTab resource columns newLabel canCreate renderDrawer filters? extraParams? />`.
4. **Panel** (`XDrawer` en el mismo archivo): `useDrawerForm` + `<EntityDrawer>` + `<RecordActions>` (historial y desactivar).
5. Inputs: siempre `NumberInput` / `DateInput` de `shared/components` (formatos del sistema). Para elegir productos: `ProductSelect` (busca en el servidor) y `allowedUnits` para sus unidades.
6. Opciones de desplegables: desde el backend (ej. `useMasterdataOptions()`), no hardcodear etiquetas.
7. Agregar la tabla al filtro de `modules/audit/AuditPage.tsx` y la ruta en `app/router.tsx` / `app/navigation.ts` si es una pantalla nueva.

## Checklist
- [ ] Permisos aplicados en la API y botones ocultos sin permiso (`useCan`).
- [ ] Historial se ve bien (etiquetas en español, referencias por nombre).
- [ ] Tests en verde; nota del módulo actualizada.
