---
tags: [requisitos, roles]
actualizado: 2026-09-27
---

# Actores y roles

## Actores
| Actor | Usa el sistema | Descripción |
|---|---|---|
| Dueño | Sí | Decide; ve todo, especialmente costos y rentabilidad. |
| Secretario | Sí | Carga diaria: compras, ventas, labores, stock, cobros y pagos. |
| Desarrollador | Sí (soporte) | Administración técnica; reabre ciclos finalizados a pedido del cliente. |
| Empleados | No (futuro) | Podrían cargar labores desde el celular más adelante. |

## Roles ([[ADR-008-Autenticacion-y-roles]])
Permisos con formato `modulo:accion` (ej. `inventory:create`). Los roles son conjuntos de permisos editables.

| Rol | Quién | Permisos |
|---|---|---|
| `support` | Desarrollador | Todo, incluido **reabrir ciclos finalizados** y ver la auditoría técnica. |
| `owner` | Dueño | Todo lo operativo + usuarios y roles. **No** reabre ciclos. |
| `staff` | Secretario | Crear, editar y anular en módulos operativos. Costos/rentabilidad: solo si el dueño le asigna `costs:read`. |
| `read_only` | Reservado | Solo lectura (ej. contador). |

Implementación (F1): **un rol por usuario**. `support`, `owner` y `read_only` calculan sus permisos solos; `staff` y los roles nuevos se editan desde *Usuarios y roles → Roles*. Detalle en [[M01-Nucleo]].

### Permisos actuales
| Permiso | Grupo | Staff por defecto |
|---|---|---|
| `users:read` | Usuarios y roles → Ver | No |
| `users:manage` | Usuarios y roles → Crear y editar | No |
| `audit:read` | Historial → Ver historial general | No |
| `masterdata:read` / `write` / `deactivate` | Maestros | Sí |
| `inventory:read` / `write` / `cancel` | Inventario | Sí |
| `inventory:adjust` | Inventario → Hacer ajustes | **No** (solo Dueño salvo que se asigne) |
| `production:read` / `write` / `config` | Producción | Sí |
| `production:reopen_cycle` | Producción → Reabrir ciclos | Solo Soporte |
| `manufacturing:read` / `write` | Elaboración | Sí |
| `assets:read` / `write` | Activos | Sí |
| `commercial:read` / `write` / `cancel` | Comercial (compras, ventas, cobros, pagos, cuentas corrientes) | Sí |
| `cash:read` / `write` | Caja y bancos | Sí |
| `costs:read` | Costos y rentabilidad (incluye resultado de gestión y tablero de resultado) | **No** (el dueño decide) |
| `assets:deactivate` | Activos → Desactivar | No |
