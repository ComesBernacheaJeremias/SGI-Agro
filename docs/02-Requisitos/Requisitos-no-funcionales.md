---
tags: [requisitos, rnf]
actualizado: 2026-09-27
---

# Requisitos no funcionales

| Categoría | Requisito |
|---|---|
| **Localización** | UI en español (Argentina). Zona horaria `America/Argentina/Buenos_Aires`. Moneda: **solo ARS**. |
| **Formato de fechas** ⚠️ | **Todas** las fechas en pantalla, inputs, reportes y exportaciones: `dd/mm/aaaa`. Cuando solo importa el mes: `mm/aaaa` (o `mm/aa` si el espacio es chico). Nunca formato ISO ni estadounidense a la vista del usuario (ISO solo internamente en la API). |
| **Formato de números** ⚠️ | **Todos** los inputs numéricos formatean **mientras se escribe**: puntos de miles y coma decimal → `123.456.789,12`. **Precios e importes: siempre 2 decimales.** **Cantidades** (stock, dosis, componentes de recetas): 2 decimales por defecto y **hasta 3 cuando hace falta** (ej. `0,125 L`); si el tercero es cero no se muestra. Mismo formato en pantallas, reportes, PDF y Excel. Internamente la base guarda más precisión (costos unitarios y cantidades) para no acumular errores de redondeo; se muestra redondeado según la regla anterior. Un único componente `NumberInput` compartido en `frontend/src/shared/` lo implementa para todo el sistema. |
| **Precisión** | Nunca `float` para dinero o cantidades. Montos `NUMERIC(18,2)`, cantidades `NUMERIC(18,4)`, costos unitarios `NUMERIC(18,6)`. En Python `Decimal`. |
| **Edición y trazabilidad** | Se puede editar con confirmación; anular en vez de borrar; todo cambio queda en el historial (quién, cuándo, antes → después). Ciclos finalizados bloqueados. Ver [[ADR-004-Edicion-auditoria-y-bloqueo]]. |
| **Offline** | Dueño y secretario pueden cargar labores, cosechas, movimientos de stock y preparaciones sin conexión ([[Offline-y-sincronizacion]]). |
| **Dispositivos** | PC (Chrome/Edge) y celular Android (Chrome). Las pantallas de carga de campo se diseñan primero para celular. |
| **Usabilidad** | Formularios cortos, valores por defecto (fecha de hoy, último almacén/ciclo usado), búsqueda rápida. |
| **Rendimiento** | < 10 usuarios. Pantallas < 1 s; reportes < 5 s con 5 años de datos. |
| **Backups** | (Producción) Base de datos diaria, 30 días de retención, fuera del servidor. Restauración probada. |
| **Seguridad** | HTTPS, contraseñas Argon2, roles y permisos, secretos fuera del repo ([[Seguridad]]). |
| **Mantenibilidad** | Código organizado por módulos, sin duplicación, con linters y tests ([[Convenciones-de-codigo]]). |
| **Propiedad de datos** | Los datos son del cliente: exportación completa disponible cuando la pida. |
