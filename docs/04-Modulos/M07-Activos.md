---
modulo: M07
codigo: assets
etapa: F3 (alta básica) / F6 (completo)
estado: implementado
depende_de: [M02]
actualizado: 2026-09-27
---

# M07 · Activos (tractores, camionetas)

## Objetivo
Registrar los bienes, su estado, uso, mantenimiento y gastos, y llevar su costo a las labores (PDF 2.5).

## Historias de usuario

**HU-07-01 · Gestionar activos** (F3)
- Código, nombre, tipo (`maquinaria`, `vehículo`, `herramienta`), marca/modelo, año, patente/serie, fecha y valor de compra, medidor (horas o km), **costo por hora**, estado (activo, en reparación, inactivo, vendido).

**HU-07-02 · Uso del activo** — horas desde las labores (automático) y lecturas manuales de horómetro/odómetro.

**HU-07-03 · Mantenimientos** (F6)
- Fecha, activo, tipo (preventivo/correctivo), descripción, repuestos (salida de stock), servicio externo (desde una compra), costo, lectura del medidor.
- Planes: "cada 250 h / 10.000 km / 6 meses" → aviso cuando se acerca.

**HU-07-04 · Gastos del activo** (F6) — combustible, reparaciones, seguros, patentes: son gastos de compra o de caja con destino = activo ([[M06-Comercial-y-Caja]]).

**HU-07-05 · Ficha del activo** (F6) — uso, mantenimientos, gastos, costo total y **costo por hora real** (gastos / horas) para comparar con la tarifa configurada y ajustarla.

## Costo por hora
- Tarifa fija configurada por activo. Al cargar una labor se copia la tarifa vigente (cambiarla después no altera labores pasadas).
- La ficha muestra el costo real para que el dueño ajuste la tarifa.

## Futuro
- **Infraestructura** (a definir con el cliente): nuevo tipo de activo.
- Amortización: si se necesita, cuota mensual como gasto del activo.

## Datos
`assets`, `asset_meter_readings`, `maintenance_plans`, `maintenance_records`.

## Implementación

### F3 (2026-09-27) — alta básica ✅
- **Backend** `app/modules/assets/` (entidad simple sobre las piezas CRUD): nombre único, tipo (maquinaria, vehículo, herramienta), marca, modelo, año, patente/serie, **medidor horas o km** y **tarifa** por hora o por km (camionetas por km, tractores por hora — decisión 27/09), estado (operativo / en reparación), observaciones. Un activo en reparación no se puede usar en labores.
- Endpoints `/api/v1/assets` (CRUD, filtros `kind`, `status`) y `/api/v1/assets-options`. Permisos `assets:read/write/deactivate` (staff: read/write).
- En las labores se copia la tarifa del momento ([[ADR-017-Costo-derivado-y-cascada]]).
- **Frontend** `modules/assets/AssetsPage.tsx`.
- Pendiente F6: mantenimientos, planes y avisos, gastos del activo, costo por hora real.

### F6 (2026-09-27) ✅
Decisión: [[ADR-020-Medidor-y-planes-de-mantenimiento]].

Backend `app/modules/assets/`:
- `models.py`: `MeterReading` (lecturas), `MaintenancePlan` (cada X h/km y/o N meses, punto de partida), `Maintenance` (MNT-000001; tipo, plan, lectura, compra vinculada, estado, comprobante de stock) y `MaintenancePart` (repuestos).
- `maintenance.py`: medidor estimado, estado de planes (al día / próximo / vencido), servicio de mantenimientos (repuestos → consumo de stock con dimensión activo; editar/anular recalcula), costos del activo por período (`asset_costs`) y consultas compartidas `usage_rows()` / `parts_rows()`.
- `maintenance_router.py`: `/api/v1/meter-readings` y `/api/v1/maintenance-plans` (CRUD estándar, filtro `asset_id`), `/api/v1/maintenances` (alta, edición, anulación), `/api/v1/maintenance-alerts` (próximos y vencidos) y `/plans` (todos los estados), `/api/v1/asset-sheets/{id}` (ficha).
- `reports.py`: reporte **Costo por activo** (uso, cargado a ciclos por tarifa, gastos, repuestos, costo real por h/km vs. tarifa).
- Migración `add_asset_maintenance`. Permisos: los de activos (`assets:write` para cargar mantenimientos).

Frontend `modules/assets/`: tocar un activo abre su **ficha** (medidor estimado, uso, gasto real, costo real por h/km vs. tarifa, período; pestañas Planes, Mantenimientos, Gastos, Lecturas; "Registrar mantenimiento", "Nuevo plan", "Cargar lectura", "Editar datos"). Columna "Mantenimiento" en la lista, **campana de mantenimientos** en la barra superior y tarjeta en el tablero.

Tests: `tests/integration/test_maintenance.py`.
