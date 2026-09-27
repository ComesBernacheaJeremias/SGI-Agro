---
tags: [inicio, moc]
actualizado: 2026-09-27
---

# 🌱 SGI Agro — Inicio

> Punto de entrada del proyecto. Si retomás el proyecto (o sos Claude en una sesión nueva), leé esta nota
> y la última entrada de la [[2026-09-27|Bitácora]].

## Estado actual
- **Etapa:** **F7 terminada** (27/09/2026): el sistema está listo para publicarse. Falta el **deploy real** (necesita las cuentas del usuario) y que el usuario pruebe F4–F7.
- **Hecho:** F0 (entorno, login), F1 (usuarios, roles, historial, maestros), F2 (inventario con costo promedio y alertas de mínimo), F3 (producción: ciclos, labores, cosecha, cuaderno de campo; elaboración multinivel; activos básicos), F4 (compras, ventas, cobros/pagos, cuentas corrientes, caja y bancos), F5 (costos, rentabilidad, resultado de gestión, reportes con Excel/PDF, tablero), F6 (activos: lecturas, planes y avisos, mantenimientos con repuestos, ficha con costo real), F7 (importar desde Excel, carga sin conexión, producción, manual y datos de ejemplo). Tests: backend 175, frontend 15.
- **Pendiente con el cliente:** [[Preguntas-abiertas]] (no bloquean F0).

## Próximos pasos
1. (Pospuesto) `git init` + subir a GitHub + `pre-commit install`; el usuario ejecuta los comandos de git.
2. El usuario prueba F4, F5 y F6 en el navegador (y lo pendiente de F1–F3); corregir lo que surja.
3. **Deploy real** ([[Entorno-local-y-deploy]]): cuando estén cuenta de DigitalOcean, dominio, GitHub (repositorio privado) y, opcional, Sentry.
4. **Arranque con el cliente** ([[Puesta-en-marcha]]): demo con `seed-demo`, entrega del el manual en `/manual` ([[Manual-de-uso]]), carga inicial por Excel. Decisiones de F7 (27/09): orden Excel → sin conexión → servidor → manual; se importan productos, terceros, stock inicial y saldos; PostgreSQL en el mismo droplet (2 GB) con backups a Spaces. Pendiente del usuario/cliente: cuenta DigitalOcean, dominio, GitHub, Sentry.

## Mapa del proyecto

### 1. Proyecto
- [[Vision-y-alcance]] — objetivo, alcance y fuera de alcance
- [[Negocio-del-cliente]] — cómo opera la empresa
- [[Propuesta-original]] — resumen del PDF (pensado en Odoo, descartado)
- [[Roadmap]] — etapas F0…F7
- [[Glosario]] — términos del dominio (ES ↔ código)
- [[Preguntas-abiertas]] — dudas pendientes con el cliente

### 2. Requisitos
- [[Actores-y-roles]]
- [[Requisitos-no-funcionales]]
- Las historias de usuario están **en cada nota de módulo**.

### 3. Arquitectura
- [[Stack-tecnologico]]
- [[Arquitectura-general]]
- [[Modelo-de-datos]]
- [[Estructura-del-repositorio]]
- [[API]]
- [[Offline-y-sincronizacion]]
- [[Seguridad]]
- [[Observabilidad]]

### 4. Módulos (por funcionalidad)
| # | Módulo | Etapa | Estado |
|---|---|---|---|
| M01 | [[M01-Nucleo]] — usuarios, roles, auditoría | F1 | ✅ Implementado |
| M02 | [[M02-Maestros]] — productos, unidades, clientes/proveedores, almacenes | F1 | ✅ Implementado |
| M03 | [[M03-Inventario]] | F2 | ✅ Implementado |
| M04 | [[M04-Produccion]] — establecimientos, lotes, ciclos, temporadas, labores, cosecha | F3 | ✅ Implementado |
| M05 | [[M05-Elaboracion]] — insumos → semielaborados → terminados (recetas multinivel) | F3 | ✅ Implementado |
| M06 | [[M06-Comercial-y-Caja]] — compras, ventas, gastos, cuentas corrientes, cobros, pagos, caja y bancos | F4 | ✅ Implementado |
| M07 | [[M07-Activos]] — tractores, camionetas, mantenimiento | F3 (básico) / F6 | ✅ Implementado |
| M08 | [[M08-Costos-y-Rentabilidad]] | F5 | ✅ Implementado |
| M09 | [[M09-Reportes]] — reportes y tablero | F5 | ✅ Implementado |

Estados: 📝 Definido · 🔨 En desarrollo · ✅ Implementado · 🚀 En producción

### 5. Desarrollo
- [[Convenciones-de-codigo]]
- [[Flujo-Git]]
- [[Estrategia-de-testing]]
- [[Entorno-local-y-deploy]]
- [[Guia-nueva-entidad]] — receta para sumar un maestro/entidad
- [[Definition-of-Done]]
- [[Puesta-en-marcha]] — lista del día de arranque

### 6. Decisiones (ADR)
- [[ADR-001-Desarrollo-desde-cero]]
- [[ADR-002-Stack-Python-FastAPI-React]]
- [[ADR-003-Monolito-modular]]
- [[ADR-004-Edicion-auditoria-y-bloqueo]]
- [[ADR-005-Dimensiones-y-costos-calculados]]
- [[ADR-006-Offline-limitado]]
- [[ADR-007-Local-y-DigitalOcean]]
- [[ADR-008-Autenticacion-y-roles]]
- [[ADR-009-Codigo-en-ingles]]
- [[ADR-010-Costo-promedio-ponderado]]
- [[ADR-011-Gestion-sin-contabilidad-formal]]
- [[ADR-012-Rentabilidad-por-partida]]
- [[ADR-013-Ciclo-productivo-y-temporada]]
- [[ADR-014-Recetas-multinivel]]
- [[ADR-015-Piezas-CRUD-genericas]]
- [[ADR-016-Motor-de-stock]]
- [[ADR-017-Costo-derivado-y-cascada]]
- [[ADR-018-Comprobantes-comerciales]]
- [[ADR-019-Reportes-y-resultado-de-gestion]]
- [[ADR-020-Medidor-y-planes-de-mantenimiento]]
- [[ADR-021-Importacion-desde-Excel]]
- [[ADR-022-Infraestructura-de-produccion]]

### 8. Manual de uso (para el cliente)
- [[Manual-de-uso]] — página `/manual` del sistema (pública, preguntas "¿Cómo hago…?" con pasos cortos)

### 7. Bitácora
- [[2026-09-27]] — Planificación (26 y 27/09) + F0 + F1 + F2 + F3 + F4 + F5 + F6
