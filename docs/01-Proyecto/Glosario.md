---
tags: [proyecto, glosario]
actualizado: 2026-09-27
---

# Glosario

Términos del dominio. **Código** = nombre usado en tablas, clases y endpoints ([[ADR-009-Codigo-en-ingles]]).
Si aparece un término nuevo, **agregarlo acá antes de usarlo en código**.

| Término | Código | Definición |
|---|---|---|
| Establecimiento | `farm` | Campo / finca. Contiene lotes. |
| Lote | `plot` | Parcela de un establecimiento con superficie en ha. Tipo: campo abierto, invernadero o forestal. **No confundir con Partida.** |
| Cultivo | `crop` | Especie + variedad (tomate perita, manzana red, pino). Indica qué producto se cosecha. |
| Ciclo productivo | `crop_cycle` | Un cultivo en (parte de) un lote entre fecha de inicio y fin. Estados: en curso → finalizado (reabrir: solo Soporte). Acumula los costos. Ver [[ADR-013-Ciclo-productivo-y-temporada]]. |
| Temporada | `season` | Período 1/7 → 30/6, igual para toda la empresa. Los movimientos caen en una temporada según su fecha. |
| Labor | `field_operation` | Trabajo en un ciclo (preparación de suelo, siembra, trasplante, aplicación, riego, poda, cosecha, tala…), con insumos y maquinaria. |
| Tipo de labor | `operation_type` | Catálogo configurable de labores. |
| Cosecha | `harvest` | Labor que ingresa producto al stock y genera una partida. Puede marcarse como "cosecha final". |
| Partida | `batch` | Conjunto de producto con origen común (ej. cosecha del Lote 3 del 12/01). Vincula ventas con el ciclo de origen ([[ADR-012-Rentabilidad-por-partida]]). |
| Tipo de producto | `product_type` | `input` (insumo), `semi_finished` (semielaborado), `finished` (producto terminado), `own_produce` (producción propia), `resale` (reventa), `service` (servicio, sin stock). |
| Semielaborado | `semi_finished` | Producto elaborado que se usa como componente de otra receta. Debe estar en stock para usarse. |
| Producto terminado | `finished` | Producto elaborado final; se vende o se usa en labores. |
| Receta | `recipe` | Componentes (insumos y/o semielaborados) y cantidades para obtener un semielaborado o terminado. Puede tener varios niveles, sin ciclos. |
| Preparación | `production_order` | Ejecución de una receta (un nivel): consume componentes a costo promedio y produce el semielaborado o terminado. |
| Almacén | `warehouse` | Lugar físico con stock. |
| Movimiento de stock | `stock_move` | Entrada o salida de un producto en un almacén. |
| Documento de stock | `stock_document` | Agrupa movimientos: compra, venta, transferencia, ajuste, consumo, cosecha, elaboración. |
| Tercero | `party` | Cliente y/o proveedor. |
| Comprobante | `commercial_document` | Factura, nota de crédito o débito, de compra o de venta (solo se registra). |
| Gasto | `expense` (línea de compra sin stock) | Servicio o concepto con categoría y destino opcional. |
| Categoría de gasto | `expense_category` | Servicios, combustible, reparaciones, impuestos, etc. |
| Destino | `cost dimensions` | Establecimiento, lote, ciclo o activo al que se asigna un costo. Sin destino = gasto de estructura. |
| Gastos de estructura | `overhead` | Gastos sin destino; se muestran aparte, no se reparten. |
| Cuenta corriente | `party ledger` | Saldo y movimientos de un cliente/proveedor (calculado). |
| Cobro / Pago | `payment` | Entrada o salida de dinero con un tercero. |
| Imputación | `allocation` | Vincula un cobro/pago con los comprobantes que cancela. |
| Anticipo | `advance` | Parte de un cobro/pago no imputada. |
| Cuenta de dinero | `cash_account` | Caja o cuenta bancaria. |
| Movimiento de dinero | `cash_movement` | Ingreso/egreso que no es de un tercero (retiro, comisión, transferencia entre cuentas). |
| Activo | `asset` | Tractor, camioneta, herramienta (futuro: infraestructura). |
| Costo por hora | `hourly_rate` | Tarifa del activo que se imputa a las labores. |
| Anular | `cancel` | Deja un registro sin efecto (sale de listas y cálculos, queda en el historial). |
| Soporte | rol `support` | Rol del desarrollador; único que reabre ciclos finalizados. |
