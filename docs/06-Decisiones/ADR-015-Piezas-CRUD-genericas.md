---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-015 · Piezas CRUD genéricas (backend y frontend)

## Contexto
El sistema tiene muchas entidades con el mismo comportamiento (listar con búsqueda y filtros, alta, edición con confirmación, activar/desactivar, historial). El desarrollador pidió explícitamente **no repetir código**.

## Decisión
**Backend** (`app/core/`):
- `CrudRepository`: búsqueda sin tildes ni mayúsculas (`unaccent`), filtro de activos, orden, paginación, `apply_filters`.
- `CrudService`: get / search / create / update / set_active + validación de únicos; extensión vía `validate`, `values_for_create`, `values_for_update`.
- `crud_router(...)`: los 6 endpoints estándar a partir de schemas y `CrudPermissions`.

**Frontend** (`src/shared/crud/`):
- `createCrudResource` (llamadas a la API), `useListState` / `useResourceList` / `useResourceMutations`.
- `CrudTab` (pestaña completa), `DataTable`, `EntityDrawer` (confirmación al editar + errores por campo), `RecordActions` (historial + desactivar), `useDrawerForm`, `HistoryButton`.
- Formularios con **@mantine/form** (en lugar de React Hook Form + Zod del plan original): se integra directo con los inputs de Mantine y requiere menos código; la validación de negocio real está en el backend.

Guía de uso: [[Guia-nueva-entidad]].

## Consecuencias
- ➕ Un maestro nuevo son pocas líneas por capa; comportamiento y UX idénticos en todo el sistema.
- ➕ Corregir o mejorar algo común (ej. exportar a Excel) se hace una vez.
- ➖ `crud_router` recibe los schemas como variables: requiere `type: ignore[valid-type]` para mypy (localizado en un archivo).
- ➖ `createCrudResource` usa el cliente de API sin tipos de ruta (un único cast documentado); los tipos de datos siguen viniendo del OpenAPI.
- Entidades con reglas muy distintas (usuarios, roles) usan las piezas parcialmente y tienen router propio.
