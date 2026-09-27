---
modulo: M02
codigo: masterdata
etapa: F1
estado: implementado
depende_de: [M01]
actualizado: 2026-09-27
---

# M02 · Maestros: productos, unidades, clientes/proveedores, almacenes

## Objetivo
Datos base que usan todos los módulos.

## Historias de usuario

**HU-02-01 · Gestionar productos**
- Campos: código (único), nombre, tipo (`insumo`, `semielaborado`, `producto terminado`, `producción propia`, `reventa`, `servicio`), categoría, unidad base, IVA %, stock mínimo, activo.
- Un servicio no maneja stock.
- Un producto con movimientos no se borra: se desactiva.

**HU-02-02 · Unidades y conversiones**
- Unidades: kg, g, tn, L, mL, unidad, cajón, bin, m³, h, km…
- Conversiones por producto (1 cajón de manzana = 18 kg; 1 bidón = 20 L). El stock se guarda siempre en la unidad base; se puede cargar en cualquier unidad convertible.

**HU-02-03 · Categorías de productos** — jerárquicas (Insumos > Agroquímicos > Insecticidas).

**HU-02-04 · Gestionar clientes y proveedores**
- Razón social, nombre de fantasía, CUIT (validado), condición de IVA, domicilio, teléfono, email, es cliente / es proveedor, días de pago, activo.
- Un tercero puede ser cliente y proveedor. CUIT único.

**HU-02-05 · Gestionar almacenes** — nombre, establecimiento (opcional), tipo (depósito, cámara de frío, galpón, depósito de agroquímicos), activo.

**HU-02-06 · Importar desde Excel** — productos y terceros, con vista previa y errores por fila (para la migración). ✅ F7 ([[ADR-021-Importacion-desde-Excel]]): `masterdata/imports.py`; pantalla **Importar datos**.

## Reglas de negocio
- Códigos y CUIT únicos.
- La unidad base no se cambia si el producto ya tiene movimientos.
- Toda edición queda en el historial.

## Datos
`products`, `product_categories`, `units`, `unit_conversions`, `parties`, `warehouses`.

## Pantallas
Listas con búsqueda y filtros + formularios · Importador Excel.

## Implementación

### F1 (2026-09-27) ✅ (salvo HU-02-06 → F7)
Backend `app/modules/masterdata/` sobre las piezas CRUD genéricas ([[ADR-015-Piezas-CRUD-genericas]]):

| Entidad | Endpoint | Reglas |
|---|---|---|
| Unidades | `/api/v1/units` | Código único. Tipo (masa, volumen, cantidad, tiempo, distancia, superficie, envase) + `factor` respecto de la base del tipo (kg, L, un, h, km, ha). El tipo no se cambia después. Envases (cajón, bin, bidón): factor 1, se convierten por producto. |
| Categorías | `/api/v1/product-categories` | Jerárquicas (`parent_id`), `path` "Insumos > Agroquímicos". Nombre único dentro del mismo nivel. Sin ciclos. |
| Productos | `/api/v1/products` (filtros `type`, `category_id`) | Código automático por tipo si se deja vacío: `INS`, `SEM`, `TER`, `PRO`, `REV`, `SER` + `-0001` (manual permitido, en mayúsculas, único). Conversiones propias (`product_unit_conversions`): se cargan como **"1 [unidad del producto] = cantidad [otra unidad]"** (ej. producto en cajones: 1 cajón = 18 kg; se guarda `quantity` tal cual se escribió y el factor se deriva). No a la unidad base, sin repetir unidad; se reemplazan completas al editar y figuran en el historial ("1 cajón = 18 kg"). IVA %, stock mínimo, observaciones. |
| Clientes/proveedores | `/api/v1/parties` (filtro `role` = customer o supplier) | CUIT opcional, se guarda con 11 dígitos, dígito verificador validado (`cuit.py`), único. Debe ser cliente, proveedor o ambos. Condición IVA, contacto, días de pago. |
| Almacenes | `/api/v1/warehouses` | Nombre único (sin distinguir tildes/mayúsculas), tipo. El vínculo con establecimiento se agrega en F3. |

- `GET /api/v1/masterdata/options`: opciones de desplegables con etiquetas en español (tipos de producto, unidad, condición IVA, almacén, alícuotas IVA). Las etiquetas viven **una sola vez** en `models.py` (`*_LABELS`) y también las usa el historial.
- Permisos: `masterdata:read`, `masterdata:write`, `masterdata:deactivate` (el rol `staff` los recibe en la migración).
- Migración `create_masterdata`: tablas, enums, 13 unidades y categorías iniciales (Insumos, Producción propia, Elaborados, Reventa, Servicios + subcategorías).
- Cambio de unidad base bloqueado si el producto tiene movimientos (`BASE_UNIT_LOCKED`, hecho en F3).

Frontend `modules/masterdata/`: pantalla Maestros con pestañas Productos (filtros tipo/categoría, editor de equivalencias), Clientes y proveedores (filtro cliente/proveedor, CUIT formateado), Almacenes, Categorías, Unidades.

Tests: `tests/integration/test_masterdata.py`, `tests/unit/test_cuit.py`.
