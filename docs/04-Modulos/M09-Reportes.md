---
modulo: M09
codigo: reports
etapa: F5 (los reportes de cada módulo se hacen en su etapa)
estado: implementado
depende_de: [M03, M04, M06, M08]
actualizado: 2026-09-27
---

# M09 · Reportes y tablero

## Objetivo
Información para decidir. Todo reporte se filtra, se ve en pantalla y se exporta a **Excel** y **PDF**.

## Tablero (dueño)
- Resultado de gestión de la temporada actual vs. anterior.
- Ciclos activos: costo acumulado, cosecha y rinde.
- Stock valorizado y alertas de stock mínimo.
- Saldos a cobrar / a pagar (y vencidos).
- Saldo de cajas y bancos.
- Mantenimientos próximos.

## Catálogo
| Reporte | Módulo | Etapa |
|---|---|---|
| Stock actual valorizado / a fecha | M03 | F2 |
| Kardex por producto | M03 | F2 |
| Cuaderno de campo por ciclo | M04 | F3 |
| Consumo de insumos por lote/ciclo/período | M04 | F3 |
| Cosecha y rinde por ciclo/cultivo/temporada | M04 | F3 |
| Preparaciones y costo resultante | M05 | F3 |
| Cuenta corriente y saldos con antigüedad | M06 | F4 |
| Ventas por cliente/producto/período | M06 | F4 |
| Compras y gastos por proveedor/categoría/destino/período | M06 | F4 |
| Caja y bancos: movimientos y saldos | M06 | F4 |
| Costo por ciclo / lote (desglosado, con filtro por categoría) | M08 | F5 |
| Rentabilidad por ciclo / cultivo / temporada | M08 | F5 |
| Gastos de estructura por categoría | M08 | F5 |
| Resultado de gestión | M08 | F5 |
| Ficha y costo por activo | M07 | F6 |
| Exportación de compras y ventas para el contador | M06 | F4 |

## Técnica
- Consultas SQL agregadas (con índices por fecha y dimensiones).
- Lógica de exportación común (no repetida por módulo): Excel con openpyxl, PDF con reportlab ([[ADR-019-Reportes-y-resultado-de-gestion]]).

## Implementación

### F5 (2026-09-27) ✅
- `app/core/reports.py`: `TableReport` (columnas tipadas, filas con estilo/sangría/vínculo, totales, notas), filtros declarativos (`period`, `season`, `farm`, `plot`, `crop`, `expense_category`, `party`, `product`, `product_type`, `cash_account`, `asset`, `warehouse`, `choice`), registro `@define_report`.
- `app/core/export.py`: Excel y PDF con formato argentino.
- Cada módulo declara sus reportes en su `reports.py`; `app/reports.py` los registra al iniciar.
- `app/modules/reports/`: `GET /api/v1/reports` (catálogo según permisos), `GET /api/v1/reports/{key}` (datos), `GET /api/v1/reports/{key}/export?format=xlsx|pdf`; `GET /api/v1/dashboard`.
- Reportes disponibles: los de costos ([[M08-Costos-y-Rentabilidad]]); Ventas (por comprobante, cliente, producto o mes); Compras y gastos (por comprobante, proveedor, categoría o mes); Libro de compras/ventas para el contador (neto e IVA por alícuota, CUIT, condición IVA); Saldos de cuentas corrientes; Movimientos de una caja o banco; Stock valorizado.
- **Tablero** (`/`): resultado de la temporada vs. la anterior a la misma fecha, ciclos en curso, cuentas corrientes, cajas y bancos, stock y alertas. Cada tarjeta aparece solo con el permiso del módulo.
- Frontend `modules/reports/`: `ReportView` (filtros + tabla + Excel/PDF, una sola implementación), pantalla **Reportes** (catálogo agrupado), `LinkedRecord` (tocar una fila abre el ciclo, comprobante, cobro/pago o movimiento).

F6: reporte **Costo por activo** y tarjeta **Mantenimientos** (próximos y vencidos) en el tablero.
