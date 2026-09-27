---
tags: [proyecto, propuesta]
actualizado: 2026-09-27
---

# Propuesta original (PDF)

Archivo: `C:\Users\Corcho\Documents\Mauro\PROPUESTA DE IMPLEMENTACIÓN DE SISTEMA DE GESTIÓN INTEGRAL.pdf`

> La propuesta estaba pensada sobre **Odoo**. Se decidió desarrollar **desde cero** con las mismas funcionalidades → [[ADR-001-Desarrollo-desde-cero]].
> Algunas partes se ajustaron en la planificación: sin contabilidad formal ([[ADR-011-Gestion-sin-contabilidad-formal]]) y "obligaciones fiscales" se limita a registrar condición de IVA y alícuotas.

## Alcance funcional del PDF
- **2.1 Inventario:** ingresos/egresos con comprobantes, múltiples almacenes, transferencias, stock en tiempo real, ajustes. → [[M03-Inventario]]
- **2.2 Comercial:** compras de insumos y mercadería, ventas, cuentas corrientes, anticipos, cobranzas y pagos. → [[M06-Comercial-y-Caja]]
- **2.3 Producción agrícola:** establecimientos y lotes (ha), división de lotes por cultivo, actividades (siembra, aplicación, cosecha), cosecha (lote origen, producto, kg), consumo de insumos por lote. → [[M04-Produccion]]
- **2.4 Costos:** centros de costo (lote, producto, actividad), imputación automática, costo de producción, costos de infraestructura, rentabilidad. → [[M08-Costos-y-Rentabilidad]]
- **2.5 Activos y flota:** maquinaria, vehículos, infraestructura; estado; gastos y mantenimiento; asociación a costos. → [[M07-Activos]]
- **2.6 Administrativa y contable:** movimientos administrativos, integración contable, estructura fiscal base, reportes. → [[M06-Comercial-y-Caja]], [[M09-Reportes]]
- **2.7 Usabilidad:** carga simple, registro detallado, trazabilidad, usuarios y roles. → [[M01-Nucleo]]

## Condiciones comerciales
- **Opción A – SaaS:** implementación AR$ 3.800.000 + AR$ 350.000/mes (hosting, soporte, correcciones, mejoras menores, backups, monitoreo). Primer mes sin costo; pago del 1 al 10; ajuste trimestral por IPC.
- **Opción B – Tradicional:** AR$ 6.500.000; incluye código fuente; sin soporte ni mejoras.
- Pago: 50 % al inicio, 50 % al entregar funcionando.
- Datos propiedad del cliente; base técnica del desarrollador salvo exclusividad; cambios fuera de alcance se presupuestan aparte.
