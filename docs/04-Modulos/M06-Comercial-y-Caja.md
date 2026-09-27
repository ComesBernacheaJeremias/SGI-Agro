---
modulo: M06
codigo: commercial
etapa: F4
estado: implementado
depende_de: [M02, M03]
actualizado: 2026-09-27
---

# M06 · Comercial y caja

## Objetivo
Compras, ventas (producción propia, productos terminados, semielaborados y reventa), gastos, cuentas corrientes, cobros, pagos, anticipos y el dinero en cajas y bancos (PDF 2.2 y 2.6). Los comprobantes **se registran** (no se emiten ni se conectan con ARCA). Solo pesos.

## Historias de usuario

### Compras y gastos
**HU-06-01 · Registrar compra**
- Proveedor, fecha, tipo (factura / NC / ND), letra, punto de venta y número, vencimiento, líneas, percepciones/otros impuestos, total.
- Cada línea es:
  - **Producto** → ingresa stock al almacén indicado (costo = precio de compra).
  - **Gasto** → categoría (servicios, combustible, reparaciones, impuestos, fletes…) y **destino opcional**: establecimiento, lote, ciclo o activo. Sin destino = gasto de estructura ([[M08-Costos-y-Rentabilidad]]).
- No se permite duplicar proveedor + tipo + letra + punto de venta + número.
- Gastos con destino en un ciclo finalizado: no se permiten.

### Ventas
**HU-06-02 · Registrar venta**
- Cliente, fecha, tipo, letra, punto de venta y número, líneas (producto, cantidad, precio, IVA), total.
- Descuenta stock. Para producción propia se elige la **partida**; el sistema propone la más antigua ([[ADR-012-Rentabilidad-por-partida]]).
- Muestra el margen estimado (reventa, terminados y semielaborados: precio − costo promedio).

**HU-06-03 · Notas de crédito y débito** — referencian el comprobante original; la NC puede reingresar stock (devolución).

### Cuentas corrientes
**HU-06-04 · Cuenta corriente de un tercero** — comprobantes, cobros/pagos, saldo, saldo vencido, pendientes, anticipos.

**HU-06-05 · Resumen de saldos** — a cobrar y a pagar, con antigüedad (0-30, 31-60, 61-90, +90 días).

**HU-06-06 · Registrar cobro**
- Cliente, fecha, medios (efectivo, transferencia) con la cuenta de dinero donde entra.
- Se imputa a uno o varios comprobantes (total o parcial). Lo no imputado queda como **anticipo**, imputable después.

**HU-06-07 · Registrar pago** — igual, del lado proveedor.

### Caja y bancos
**HU-06-08 · Cuentas de dinero** — cajas y cuentas bancarias, con saldo inicial.

**HU-06-09 · Movimientos de dinero** — ingresos/egresos que no son con un tercero (retiros del dueño, comisiones bancarias, aportes) y transferencias entre cuentas. Los egresos pueden llevar categoría de gasto y destino.

**HU-06-10 · Saldo y movimientos por cuenta** — saldo actual y a una fecha.

### Edición
**HU-06-11 · Editar o anular comprobantes y pagos**
- Con confirmación; queda en el historial.
- Si un comprobante con cobros imputados baja de monto → aviso; el excedente queda como anticipo.
- Si se edita el precio de una compra de producto → se recalcula el costo promedio (ciclos finalizados no cambian).

## Preparado para el futuro
- **Cheques:** el medio de pago es un catálogo; agregar cheques (cartera, estados, vencimientos) no cambia el resto.

## Reglas de negocio
- Saldos de cuenta corriente y de caja siempre calculados, nunca cargados a mano.

## Datos
`commercial_documents`, `commercial_lines`, `expense_categories`, `payments`, `payment_lines`, `allocations`, `cash_accounts`, `cash_movements`.

## Implementación

**F7:** importación de **saldos iniciales** de cuentas corrientes (`commercial/imports.py`, `create_opening`): comprobantes "Saldo inicial …" (`is_opening_balance`) que suman a la cuenta corriente pero se excluyen de ventas, gastos, costos y libro del contador; no se editan (se anulan). Importe negativo = saldo a favor ([[ADR-021-Importacion-desde-Excel]]).

### F4 (2026-09-27) ✅
Decisiones: [[ADR-018-Comprobantes-comerciales]], [[ADR-011-Gestion-sin-contabilidad-formal]], [[ADR-012-Rentabilidad-por-partida]].

Backend `app/modules/commercial/`:

| Archivo | Qué hace |
|---|---|
| `models.py` | Tablas de la sección *Datos*. Enums `commercial_direction` y `commercial_status` compartidos entre tablas. |
| `document_service.py` | Alta/edición/anulación de compras y ventas: validaciones, importes, comprobante de stock de sistema, venta por partida, desimputación. |
| `payment_service.py` | Cobros y pagos con medios e imputaciones; anticipos. |
| `cash_service.py` | Movimientos de caja, saldos y resumen por cuenta. |
| `ledger.py` | Pendiente por comprobante, cuenta corriente y saldos con antigüedad. |
| `destinations.py` | Destino de un gasto: se completa hacia arriba (ciclo → lote → establecimiento); rechaza ciclos finalizados. |
| `router.py` | Endpoints (abajo) + piezas CRUD de categorías de gasto y cuentas de dinero. |

| Endpoint | Uso |
|---|---|
| `/api/v1/commercial-documents` (`direction`, `party_id`, `status`, fechas, `q`, `only_pending`) | Compras y ventas: `POST`, `PUT /{id}`, `POST /{id}/cancel`. Devuelve el comprobante + alertas de stock mínimo. |
| `/api/v1/payments` (`direction`) | Cobros (`sale`) y pagos (`purchase`): `POST`, `PUT /{id}`, `POST /{id}/cancel`. |
| `/api/v1/current-accounts?direction=` · `/{party_id}` | Saldos con antigüedad · cuenta corriente con saldo acumulado. |
| `/api/v1/cash/balances` (`at`) · `/cash/accounts/{id}/statement` · `/cash/movements` | Saldos, resumen de una cuenta, movimientos sin tercero. |
| `/api/v1/expense-categories` · `/api/v1/cash-accounts` | Configuración (CRUD estándar). |
| `/api/v1/commercial-options` | Etiquetas de tipos, estados, medios, movimientos. |

Reglas implementadas:
- **Numeración:** interna siempre (`CPR-`, `VTA-`, cobros `REC-`, pagos `OP-`, caja `MOV-`). Con factura se muestra "Factura A 00003-00000123"; sin factura, el número interno. Los comprobantes de stock que generan pasaron a `RCP-` (recepción) y `DSP-` (despacho).
- **Duplicados:** compra = proveedor + tipo + letra + PV + número; venta = tipo + letra + PV + número (solo vigentes).
- **Importes:** neto = cantidad × precio; IVA = neto × alícuota; total = neto + IVA + percepciones/otros. Vencimiento por defecto = fecha + días de pago del tercero.
- **Stock:** factura de compra → entrada al costo neto por unidad base; NC de compra → salida (devolución); venta → salida a costo promedio; NC de venta → entrada. La ND no admite productos.
- **Producción propia:** la venta sale por partida (la elegida o las más antiguas primero; si falta, el resto sin partida). No lleva ciclo: no suma al costo del ciclo.
- **Gastos:** línea de compra (neto de IVA) o movimiento de caja tipo gasto, con categoría; con destino en un ciclo suma a "Servicios y gastos" del ciclo (`expense_cost` en el resumen de ciclos).
- **Imputación:** cada importe ≤ pendiente del comprobante; la suma ≤ total del cobro/pago; el resto es anticipo (se imputa después editando el cobro/pago). Solo comprobantes del mismo tercero y operación. Las NC no se imputan: restan del saldo.
- **Edición/anulación:** si el total nuevo queda por debajo de lo imputado, se desimputa desde el cobro/pago más reciente (queda anticipo); anular un comprobante libera sus imputaciones; no se cambia el tercero con imputaciones; no se edita con destino en un ciclo finalizado.
- **Caja:** saldo = inicial + cobros − pagos + ingresos − gastos − retiros ± transferencias. No se cargan movimientos anteriores a la fecha del saldo inicial.
- Permisos `commercial:read/write/cancel`, `cash:read/write` (staff los recibe en la migración). Migración `create_commercial_and_cash`: tablas, enums, 11 categorías de gasto iniciales.

Frontend `modules/commercial/`: pantalla **Comercial y caja** con pestañas Ventas, Cobros, Compras y gastos, Pagos, Cuentas corrientes (saldos con antigüedad + resumen por tercero con acceso a cada comprobante y "Nuevo cobro/pago"), Caja y bancos (saldos por cuenta, movimientos, resumen de una cuenta) y Configuración (cajas/bancos y categorías de gasto). El cobro/pago lista los pendientes del tercero con "Imputar a los más viejos". En la venta de producción propia se puede elegir la partida (`GET /api/v1/stock/batches`: partidas con stock a la fecha; vacío = las más antiguas). Caja y bancos muestra saldos a hoy o a una fecha.

**Agregado en F5:**
- **Comprobante asociado** en NC/ND (`related_document_id`): la NC se aplica sola a esa factura (baja su pendiente); no puede superar lo que queda sin otras NC; si la factura ya estaba cobrada/pagada, el excedente del cobro/pago queda como anticipo. Una factura con NC asociadas no se anula (primero las NC). La NC sin comprobante asociado cuenta como saldo a favor ("Anticipos y NC sin aplicar").
- **NC de venta con partida:** la devolución vuelve a la partida elegida (la lista incluye partidas sin stock) y resta ingresos a ese ciclo.

Tests: `tests/integration/test_commercial.py` (27).

Pendiente / diferido:
- Margen estimado al cargar la venta (hoy se ve en el reporte Margen por producto).

