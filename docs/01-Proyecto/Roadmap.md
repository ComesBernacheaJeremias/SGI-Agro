---
tags: [proyecto, roadmap]
actualizado: 2026-09-27
---

# Roadmap

Todo se desarrolla **en local**; el deploy a DigitalOcean es la última etapa ([[ADR-007-Local-y-DigitalOcean]]).
Al final de cada etapa hay algo funcionando que se le puede mostrar al cliente.

| Etapa | Contenido | Qué se puede probar al terminar | Estado |
|---|---|---|---|
| **F0 – Preparación** | Repo git, Docker Compose (db, api, web), esqueleto FastAPI y React, linters, pre-commit, tests, login básico | El sistema levanta en local con login | ✅ 27/09/2026 |
| **F1 – Núcleo y maestros** | [[M01-Nucleo]], [[M02-Maestros]] | Usuarios, roles, productos, clientes/proveedores, almacenes; historial de cambios | ✅ 27/09/2026 (importar Excel → F7) |
| **F2 – Inventario** | [[M03-Inventario]] | Stock al momento; ingresos, egresos, transferencias, ajustes | ✅ 27/09/2026 |
| **F3 – Producción** | [[M04-Produccion]], [[M05-Elaboracion]], alta básica de [[M07-Activos]] | Ciclos y temporadas, labores con consumo y maquinaria, cosecha con partida, mezclas | ✅ 27/09/2026 |
| **F4 – Comercial y caja** | [[M06-Comercial-y-Caja]] | Compras, ventas, gastos, cuentas corrientes, cobros, pagos, anticipos, caja y bancos | ✅ 27/09/2026 |
| **F5 – Costos y reportes** | [[M08-Costos-y-Rentabilidad]], [[M09-Reportes]] | Costo y rentabilidad por ciclo/lote/cultivo/temporada; tablero | ✅ 27/09/2026 |
| **F6 – Activos completo** | [[M07-Activos]] | Mantenimientos con avisos, gastos y costo real por activo | ✅ 27/09/2026 |
| **F7 – Puesta en marcha** | Carga sin conexión, migración de datos (incluye importar productos y terceros desde Excel), deploy a DigitalOcean, capacitación | Cliente usando el sistema | ✅ 27/09/2026 (listo para publicar; deploy real pendiente de cuentas) |

## Notas
- Desde F2 cada movimiento guarda sus **dimensiones** (lote, ciclo, labor, activo) → en F5 los costos salen solos ([[ADR-005-Dimensiones-y-costos-calculados]]).
- IDs generables en el cliente desde F1 para que el offline de F7 no requiera cambios de fondo.
- Estimación de tiempos: pendiente.
