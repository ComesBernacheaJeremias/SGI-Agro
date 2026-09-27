---
tags: [arquitectura, datos]
actualizado: 2026-09-27
estado: preliminar
---

# Modelo de datos

> Vista conceptual. Cuando exista código, la **fuente de verdad del esquema son los modelos SQLAlchemy + migraciones Alembic**; esta nota se actualiza con los cambios relevantes.

## Convenciones
- PK `id UUID` (UUIDv7, generable en el cliente → carga offline).
- Tablas en inglés, plural, snake_case ([[ADR-009-Codigo-en-ingles]]).
- Toda tabla: `created_at`, `created_by`, `updated_at`, `updated_by`.
- Registros operativos: `status` con `cancelled` para anular (no se borran) ([[ADR-004-Edicion-auditoria-y-bloqueo]]).
- Montos `NUMERIC(18,2)`, cantidades `NUMERIC(18,4)`, costos unitarios `NUMERIC(18,6)`. Solo ARS.
- **Dimensiones** (columnas nullable) en todo lo que genera costo: `farm_id`, `plot_id`, `crop_cycle_id`, `field_operation_id`, `asset_id` ([[ADR-005-Dimensiones-y-costos-calculados]]).
- La **temporada no se guarda** en los movimientos: se deduce de la fecha (`seasons.start_date ≤ fecha ≤ end_date`).

## Núcleo y maestros

```mermaid
erDiagram
    users }o--|| roles : "role_id (un rol por usuario)"
    roles ||--o{ role_permissions : "solo roles editables"
    audit_log }o--|| users : autor
    products }o--|| units : "unidad base"
    products }o--o| product_categories : ""
    product_categories }o--o| product_categories : "parent_id"
    product_unit_conversions }o--|| products : ""
    product_unit_conversions }o--|| units : ""
    parties
    warehouses

    products {
        uuid id
        string code
        string name
        enum type "input|semi_finished|finished|own_produce|resale|service"
        decimal min_stock
        decimal vat_rate
        bool is_active
    }
    parties {
        uuid id
        string name
        string cuit
        enum vat_condition
        bool is_customer
        bool is_supplier
    }
    audit_log {
        uuid id
        string table_name
        uuid record_id
        enum action "create|update|cancel|reopen"
        jsonb before
        jsonb after
        timestamptz at
    }
```

## Producción, elaboración y activos

```mermaid
erDiagram
    farms ||--|{ plots : ""
    plots ||--o{ crop_cycles : ""
    crops ||--o{ crop_cycles : ""
    crop_cycles ||--o{ field_operations : ""
    operation_types ||--o{ field_operations : ""
    field_operations ||--o{ field_operation_inputs : "insumos"
    field_operations ||--o{ field_operation_assets : "maquinaria"
    field_operation_assets }o--|| assets : ""
    field_operations ||--o| batches : "cosecha genera"
    recipes ||--|{ recipe_components : ""
    recipes ||--o{ production_orders : ""
    assets ||--o{ maintenance_plans : ""
    assets ||--o{ maintenance_records : ""
    seasons

    plots {
        uuid id
        string name
        decimal area_ha
        enum kind "open_field|greenhouse|forest"
    }
    crops {
        uuid id
        string species
        string variety
        enum kind "fruit|vegetable|forest"
        uuid harvest_product_id
    }
    crop_cycles {
        uuid id
        decimal area_ha
        date start_date
        date end_date
        enum status "planned|active|finished"
    }
    field_operations {
        uuid id
        date date
        bool is_harvest
        bool is_final_harvest
        text notes
    }
    field_operation_assets {
        decimal hours
        decimal hourly_rate "copiada al cargar"
    }
    assets {
        uuid id
        enum kind "machinery|vehicle|tool"
        enum status "active|in_repair|inactive|sold"
        enum meter "hours|km"
        decimal hourly_rate
    }
    seasons {
        string name "2026/27"
        date start_date "01/07"
        date end_date "30/06"
    }
```

## Inventario

```mermaid
erDiagram
    stock_documents ||--|{ stock_document_lines : "lo cargado"
    stock_documents ||--|{ stock_moves : "calculados"
    stock_moves }o--|| products : ""
    stock_moves }o--|| warehouses : ""
    stock_moves }o--o| batches : partida
    batches }o--o| crop_cycles : origen

    stock_documents {
        uuid id
        enum type "purchase|sale|transfer|adjustment|consumption|harvest|production|manual_in|manual_out"
        string number
        date date
        enum status "active|cancelled"
    }
    stock_moves {
        uuid id
        decimal quantity "+ entrada / - salida (unidad base)"
        enum cost_mode "own|average"
        decimal unit_cost
        decimal total_cost
        decimal avg_cost_after
        decimal balance_after
        bool cancelled
        bool frozen
        uuid crop_cycle_id "dimensiones..."
    }
```
- El stock se obtiene sumando movimientos no anulados (**sin tabla de saldos**, [[ADR-016-Motor-de-stock]]).
- **Recálculo por edición:** si se edita una compra, se recalcula el costo promedio del producto desde esa fecha y se actualiza el `unit_cost` de las salidas posteriores, **salvo las que pertenecen a ciclos finalizados** (quedan congeladas).

## Comercial y dinero

```mermaid
erDiagram
    commercial_documents ||--|{ commercial_lines : ""
    commercial_documents }o--|| parties : ""
    commercial_documents ||--o| stock_documents : "mueve stock"
    commercial_lines }o--o| expense_categories : "si es gasto"
    payments }o--|| parties : ""
    payments ||--|{ payment_lines : "medios"
    payment_lines }o--|| cash_accounts : ""
    allocations }o--|| payments : ""
    allocations }o--|| commercial_documents : ""
    cash_movements }o--|| cash_accounts : ""

    commercial_documents {
        uuid id
        enum direction "purchase|sale"
        enum kind "invoice|credit_note|debit_note"
        string letter "A|B|C|X"
        string pos_number
        string number
        date date
        date due_date
        decimal total
    }
    commercial_lines {
        uuid product_id "o gasto"
        decimal quantity
        decimal unit_price
        decimal vat_rate
        uuid batch_id "venta de producción propia"
        uuid crop_cycle_id "destino opcional del gasto"
    }
    payment_lines {
        enum method "cash|transfer|cheque(futuro)"
        decimal amount
    }
    cash_accounts {
        string name
        enum kind "cash|bank"
    }
```
- Saldo de cuenta corriente = Σ comprobantes − Σ pagos imputados y no imputados (calculado).
- Anticipo = parte de un pago sin imputar.

## Costos
Sin tablas propias: se calculan con consultas sobre `stock_moves` (insumos consumidos), `field_operation_assets` (horas × tarifa), `commercial_lines` de gastos con destino y ventas por partida. Ver [[M08-Costos-y-Rentabilidad]].
