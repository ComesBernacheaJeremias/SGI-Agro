---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-021 · Importación desde Excel con vista previa y "todo o nada"

## Contexto
Para arrancar hay que cargar productos, clientes/proveedores, el stock y los saldos de cuentas corrientes que el cliente ya tiene (F7). A mano es lento y propenso a errores.

## Decisión
1. **Una definición por tipo de importación** (`@define_import` en el `imports.py` de cada módulo): columnas (etiqueta, obligatoria, ayuda, ejemplo) y una función por fila que **usa los servicios reales** (mismas validaciones que las pantallas). De la definición salen la plantilla, la vista previa y la confirmación.
2. **Vista previa = la importación completa en un savepoint que se deshace**: cada fila en su propio savepoint, los errores se informan con el número de fila del Excel. La confirmación corre lo mismo y **solo guarda si no hubo ningún error** (todo o nada).
3. Plantilla `.xlsx` con hoja "Datos" (encabezados, `*` = obligatorio) e "Instrucciones". Se aceptan números con formato argentino y fechas dd/mm/aaaa; las opciones por etiqueta ("Reventa") o valor.
4. Importaciones: **productos**, **clientes y proveedores**, **stock inicial** (un ingreso "Stock inicial" por almacén y fecha) y **saldos iniciales de cuentas corrientes** (comprobantes marcados `is_opening_balance`: suman a la cuenta corriente pero **no son ventas ni gastos**; no se editan, se anulan y se vuelven a cargar; importe negativo = saldo a favor).
5. Cada importación exige el permiso de escritura de su módulo.

## Consecuencias
- ➕ Sin reglas duplicadas: lo que no se puede cargar a mano tampoco se importa.
- ➕ El usuario corrige en el Excel y vuelve a revisar; nunca queda una importación a medias.
- ➖ Archivos grandes se validan dos veces (vista previa y confirmación); con el volumen del cliente no importa (tope 5.000 filas / 5 MB).
