---
tags: [proyecto, alcance]
actualizado: 2026-09-27
---

# Visión y alcance

## Objetivo
Sistema de gestión **a medida**, desarrollado desde cero ([[ADR-001-Desarrollo-desde-cero]]), que centraliza la operación de una empresa agrícola: producción, elaboración, inventario, compras y ventas, dinero, activos, costos y rentabilidad.

## Pregunta central
> **¿Cuánto me cuesta producir cada cosa, en cada lote y en cada temporada, y cuánto gano con ella?**

El cliente quiere **conocer la rentabilidad y analizar los costos** de su negocio. No busca contabilidad formal ([[ADR-011-Gestion-sin-contabilidad-formal]]).

## Usuarios
Dueño y secretario, desde la PC o el celular (sin carga sin conexión, [[ADR-024-Sin-carga-offline]]). El desarrollador tiene el rol `soporte`. Los empleados no usan el sistema por ahora. Ver [[Actores-y-roles]].

## Alcance
| Área | Módulo |
|---|---|
| Usuarios, roles, historial de cambios | [[M01-Nucleo]] |
| Productos, unidades, clientes/proveedores, almacenes | [[M02-Maestros]] |
| Ingresos/egresos con comprobante, múltiples almacenes, transferencias, stock al momento, ajustes | [[M03-Inventario]] |
| Establecimientos, lotes, ciclos productivos, temporadas, labores, consumo de insumos, cosecha | [[M04-Produccion]] |
| Mezclas: insumos que se combinan para crear productos | [[M05-Elaboracion]] |
| Compras, ventas, reventa, gastos, cuentas corrientes, anticipos, cobros, pagos, caja y bancos | [[M06-Comercial-y-Caja]] |
| Tractores y camionetas: estado, uso, mantenimiento, gastos, costo por hora | [[M07-Activos]] |
| Costo y rentabilidad por ciclo, lote, cultivo y temporada; gastos de estructura | [[M08-Costos-y-Rentabilidad]] |
| Reportes exportables y tablero | [[M09-Reportes]] |

## Fuera de alcance (por ahora)
- Conexión con ARCA / facturación electrónica (el sistema registra comprobantes, no los emite).
- Contabilidad formal (partida doble, asientos, balance).
- Mano de obra de empleados en los costos.
- Infraestructura (a definir con el cliente; se agregaría como tipo de activo).
- Cheques (el diseño de medios de pago lo deja preparado).
- Ganadería, transporte, sueldos.
- Otros clientes (irían en otra instancia/servidor).

Todo esto puede agregarse después gracias al diseño por módulos ([[ADR-003-Monolito-modular]]). Cambios fuera de alcance se presupuestan aparte.
