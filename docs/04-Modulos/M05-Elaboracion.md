---
modulo: M05
codigo: manufacturing
etapa: F3
estado: implementado
depende_de: [M02, M03]
actualizado: 2026-09-27
---

# M05 · Elaboración (recetas de varios niveles)

## Objetivo
El cliente combina insumos para crear **semielaborados** y **productos terminados** (ej. venenos → mezcla base → insecticida para tomates). Descontar componentes, ingresar lo elaborado y calcular su costo. Decisión: [[ADR-014-Recetas-multinivel]].

## Modelo
```
Insecticida tomate (terminado) — rinde 1 L
 ├─ 1,00 L Veneno A          (insumo)
 └─ 0,50 L Mezcla base       (semielaborado)
             └─ receta propia — rinde 1 L
                 ├─ 0,70 L Veneno B  (insumo)
                 └─ 0,30 L Agua      (insumo)
```
- Receta de **terminado**: componentes insumos y/o semielaborados.
- Receta de **semielaborado**: insumos y/o otros semielaborados.
- Prohibidas las recetas circulares (A usa B y B usa A, directa o indirectamente).

## Historias de usuario

**HU-05-01 · Gestionar recetas**
- Producto resultante (semielaborado o terminado), cantidad que rinde, componentes (producto + cantidad, hasta 3 decimales), instrucciones, activa.
- Validación de ciclos al guardar.
- Vista en árbol de la receta completa (con sus semielaborados desplegados) y costo estimado actual.
- Cambiar una receta no altera las preparaciones hechas (cada preparación guarda lo realmente usado).

**HU-05-02 · Registrar una preparación** — apta offline
- Fecha, receta, cantidad a producir (escala la receta), almacén de componentes, almacén destino.
- Se pueden ajustar las cantidades reales de los componentes.
- Al guardar: salida de cada componente a su **costo promedio** y entrada del producto con **costo = suma de lo consumido** ÷ cantidad producida.
  - Ej.: 1 L Veneno A ($ 1.000,00) + 0,5 L Mezcla base ($ 800,00) → Insecticida $ 1.800,00 el litro.
- **Los semielaborados deben estar en stock**: no se preparan implícitamente.

**HU-05-03 · Faltantes y "Preparar lo que falta"**
- Antes de guardar, el sistema verifica el stock de todos los componentes y lista los faltantes: *"Falta 1,00 L de Veneno A (hay 10,00 L)"*.
- Si falta un **insumo** → no se puede preparar (hay que comprar o ajustar).
- Si falta un **semielaborado** → botón **"Preparar lo que falta"**: arma primero la preparación del semielaborado por la cantidad faltante (verificando a su vez sus componentes) y luego la del terminado. Cada preparación queda registrada por separado con su costo.

**HU-05-04 · Editar o anular una preparación** — con confirmación; solo si el stock del producto elaborado lo permite (no se puede anular si ya se consumió/vendió).

**HU-05-05 · Consultar preparaciones** — por receta, producto y período, con costo unitario resultante.

## Ejemplo de stock
Stock: 10 L de Veneno A; la receta usa 1 L por litro.
- Preparar 10 L → consume 10 L → stock de Veneno A = 0.
- Preparar 11 L → rechazado: "Falta 1,00 L de Veneno A (hay 10,00 L)".

## Reglas de negocio
- Semielaborados y terminados se usan en labores ([[M04-Produccion]]) o se venden ([[M06-Comercial-y-Caja]]).
- Costo por cantidad con costo promedio ponderado ([[ADR-010-Costo-promedio-ponderado]]): 10 L comprados a $ 10.000,00 → $ 1.000,00/L; usar 3 L = $ 3.000,00.

## Datos
`recipes`, `recipe_components`, `production_orders`, `production_order_lines`.

## Implementación

**F7:** alta apta para la carga sin conexión (id generado en el dispositivo, cola y reenvío sin duplicar) → [[Offline-y-sincronizacion]].

### F3 (2026-09-27) ✅
Decisiones: [[ADR-014-Recetas-multinivel]], [[ADR-017-Costo-derivado-y-cascada]].

- **Backend** `app/modules/manufacturing/`: `Recipe` (una por producto elaborado; rinde y unidad; componentes insumos/semielaborados; validación de recetas circulares recorriendo las sub-recetas), `ProductionOrder` (número `ELA-000001`, cantidades reales usadas en `ProductionOrderLine`, `parent_id` si se creó con "Preparar lo que falta").
- Preparación → comprobante de stock **Elaboración**: salidas de componentes (costo promedio) + entrada del producto con costo **derivado**. Cambios posteriores en el costo de un componente se propagan en cascada.
- `POST /production-orders/check`: necesario, disponible y faltante por componente (`can_prepare` si es un semielaborado con receta).
- `prepare_missing: true`: crea antes, en la misma transacción y en forma recursiva, las preparaciones de los semielaborados faltantes (cantidad faltante redondeada hacia arriba), con destino el almacén de componentes.
- Costo estimado de la receta con los promedios actuales (si un semielaborado no tiene stock, se estima con su propia receta).
- Endpoints: `/api/v1/recipes` (CRUD + activar/desactivar), `/api/v1/production-orders` (lista, detalle, check, alta, edición, anulación). Permisos `manufacturing:read/write` (staff ambos).
- **Frontend** `modules/manufacturing/`: pantalla Elaboración con pestañas Preparaciones y Recetas; `OrderDrawer` con tabla de faltantes y "Preparar lo que falta"; `RecipesTab` con editor de componentes y costo estimado.
- Pendiente (UI): editar las cantidades reales de cada componente en la preparación (el backend ya lo admite con `lines`).

**Tests**: `tests/integration/test_manufacturing.py` (9: ejemplo del cliente, costo sumado, check, preparar lo que falta, cascada de costos, recetas circulares, validaciones, anulación, costo estimado).
