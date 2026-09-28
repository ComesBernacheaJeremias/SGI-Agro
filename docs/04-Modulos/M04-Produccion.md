---
modulo: M04
codigo: production
etapa: F3
estado: implementado
depende_de: [M02, M03, M07]
actualizado: 2026-09-27
---

# M04 · Producción

## Objetivo
Registrar dónde y qué se produce, qué trabajos se hacen, qué se consume y qué se cosecha (PDF 2.3). **Módulo central del sistema.**

## Modelo: establecimiento → lote → ciclo → labores
Ver [[ADR-013-Ciclo-productivo-y-temporada]].

```
Establecimiento "La Esperanza"
 └─ Lote 3 (2 ha, invernadero)
     ├─ Ciclo: Tomate perita · 1,2 ha · sep-2026 → feb-2027
     │    └─ Labores: preparación, trasplante, aplicaciones, riego, cosechas…
     └─ Ciclo: Pimiento · 0,8 ha · sep-2026 → mar-2027
 └─ Lote 7 (10 ha)
     └─ Ciclo: Manzana Red · 10 ha · 2019 → vigente   (se analiza por temporada)
 └─ Lote F1 (40 ha, forestal)
     └─ Ciclo: Pino · 40 ha · 2015 → vigente
```

### Temporada
- Período **1/7 → 30/6**, única para toda la empresa (ej. "2026/27").
- La crea el dueño (el sistema sugiere la siguiente automáticamente). Termina sola al pasar la fecha.
- Cada registro cae en una temporada según su fecha. No se bloquea por temporada.

### Ciclo productivo
```
PLANIFICADO ──► EN CURSO ──► FINALIZADO
                                 │
                                 └─► reabrir (solo rol soporte)
```
- **Comienza** cuando empieza el primer trabajo (incluida la preparación del suelo), para que esos costos sumen al cultivo.
- **Termina** cuando el usuario lo finaliza. Hortalizas: con la última cosecha (al cargar una cosecha el sistema pregunta "¿Es la cosecha final?" y ofrece finalizar). Frutales: cuando se arranca el monte. Forestal: con la tala final.
- **Finalizado = bloqueado:** no se cargan, editan ni anulan labores, consumos ni gastos de ese ciclo; su costo queda congelado. Las **ventas** de sus partidas sí siguen sumando ingresos. Solo `support` lo reabre (queda en el historial).
- Libera sus hectáreas para un nuevo ciclo en el lote.

| Cultivo | Comienza | Termina | Análisis |
|---|---|---|---|
| Tomate / lechuga | Preparación / trasplante | Última cosecha | Por ciclo |
| Manzano | Plantación | Arranque del monte (décadas) | Por temporada |
| Pino | Plantación | Tala final | Por temporada y acumulado |

## Historias de usuario

**HU-04-01 · Establecimientos y lotes** — establecimiento: nombre, ubicación, superficie. Lote: código, establecimiento, superficie (ha), tipo (campo abierto, invernadero, forestal).

**HU-04-02 · Cultivos y tipos de labor**
- Cultivo: especie, variedad, tipo (fruta, hortaliza, forestal), producto que se cosecha.
- Tipos de labor configurables (preparación de suelo, siembra, trasplante, plantación, aplicación, fertilización, riego, poda, raleo, desmalezado, cosecha, tala…), indicando si lleva insumos, maquinaria o es cosecha.

**HU-04-03 · Temporadas** — crear temporada (nombre, desde, hasta); validación: no se superponen.

**HU-04-04 · Abrir un ciclo**
- Lote, cultivo, superficie (ha), fecha de inicio, fecha estimada de fin, estado inicial (planificado o en curso).
- La suma de hectáreas de ciclos activos no puede superar la del lote.

**HU-04-05 · Registrar una labor** ⭐ carga frecuente
- Fecha, ciclo, tipo de labor, insumos (producto, cantidad o dosis/ha, almacén), maquinaria (activo, horas), observaciones.
- Al guardar: descuenta stock (consumo a costo promedio con las dimensiones del ciclo) y registra las horas de maquinaria con la tarifa del activo en ese momento.
- Sin stock suficiente → error con el producto y lo disponible.
- Ciclo finalizado → no se permite.
- Pantalla pensada para celular: último ciclo y almacén usados por defecto; dosis/ha calcula la cantidad total.

**HU-04-06 · Labor en varios ciclos** — una aplicación que cubre varios ciclos reparte el consumo y las horas por superficie (o manual).

**HU-04-07 · Registrar cosecha** ⭐
- Fecha, ciclo, producto (por defecto el del cultivo), cantidad y unidad, almacén destino, maquinaria, "¿es la cosecha final?".
- Ingresa el producto al stock con una **partida** creada automáticamente (ej. `L3-TOM-20270112`) que guarda el ciclo de origen ([[ADR-012-Rentabilidad-por-partida]]).
- Si es la final, ofrece finalizar el ciclo.

**HU-04-08 · Editar o anular una labor/cosecha** — con confirmación; revierte y rehace los movimientos de stock asociados; no permitido en ciclos finalizados.

**HU-04-09 · Finalizar y reabrir ciclo** — finalizar: fecha de fin, confirmación. Reabrir: solo `support`, con motivo.

**HU-04-10 · Cuaderno de campo del ciclo** — todas sus labores en orden, insumos con dosis/ha, cosechas acumuladas, rinde (kg/ha) y costo acumulado.

## Valuación de la cosecha
El producto cosechado ingresa al stock con **costo cero**: su costo real está en el ciclo, y la rentabilidad se calcula por ciclo (ingresos de sus partidas − costos del ciclo). Evita recalcular stock cada vez que cambia un costo del ciclo. Ver [[M08-Costos-y-Rentabilidad]].

**Valor informativo (28/09):** Inventario y el tablero muestran la producción propia valorizada con el costo por unidad de su ciclo (`production/valuation.py`), "provisorio" si el ciclo sigue en curso. Solo para mostrar: no entra en costo de lo vendido, kardex ni resultado. Detalle y por qué: [[ADR-012-Rentabilidad-por-partida]].

## Datos
`farms`, `plots`, `crops`, `seasons`, `operation_types`, `crop_cycles`, `field_operations`, `field_operation_inputs`, `field_operation_assets`, `batches`.

## Pantallas
Establecimientos y lotes · Temporadas · Ciclos (tablero de activos) · Cargar labor (celular) · Cargar cosecha (celular) · Cuaderno de campo.

## Implementación

**F7:** alta con id generado en el dispositivo (reintentar no duplica). La carga sin conexión se quitó: [[ADR-024-Sin-carga-offline]].

### F3 (2026-09-27) ✅
Decisiones: [[ADR-013-Ciclo-productivo-y-temporada]], [[ADR-017-Costo-derivado-y-cascada]].

| Historia | Estado |
|---|---|
| HU-04-01/02 Establecimientos, lotes, cultivos, tipos de labor (12 sembrados) | ✅ |
| HU-04-03 Temporadas (se crean solas 1/7 → 30/6) | ✅ |
| HU-04-04 Abrir ciclo (control de hectáreas del lote) | ✅ |
| HU-04-05/06 Labor con insumos (total o dosis/ha), maquinaria y varios ciclos (reparto por superficie) | ✅ |
| HU-04-07 Cosecha con partida, ingreso a costo 0 y "¿es la cosecha final?" | ✅ |
| HU-04-08 Editar / anular labor (bloqueado si un ciclo está finalizado) | ✅ |
| HU-04-09 Finalizar (congela costos) / reabrir (solo Soporte, con motivo) | ✅ |
| HU-04-10 Cuaderno de campo | ✅ |

**Backend** `app/modules/production/`
- `models.py`: Farm, Plot (único por establecimiento), Crop (nombre = especie + variedad; producto cosechado de tipo Producción propia), OperationType (lleva insumos / maquinaria / es cosecha), Season, CropCycle (nombre "Tomate perita · Lote 3 · 2026/27", estados `active`/`finished`, `reopen_reason`), FieldOperation (+ FieldOperationCycle con superficie, FieldOperationInput con dosis/ha y almacén, FieldOperationAsset con uso y tarifa copiada; datos de cosecha), Batch.
- `catalog.py`: servicios CRUD de catálogos; `season_for(fecha)` crea la temporada si falta; `active_cycles_area`.
- `service.py`: `CycleService` (create/update/finish/reopen) y `FieldOperationService` (create/update/cancel). Genera comprobantes de stock de sistema: **Consumo** (un movimiento por ciclo, dimensiones farm/plot/cycle/operation) o **Cosecha** (partida `LOTE3-TOMATE-AAAAMMDD` + entrada costo 0). Numeración `LAB-000001`.
- `queries.py`: resumen por ciclo (insumos, maquinaria, total, cosechado, rinde/ha, costo/ha, costo/unidad), detalle de labor y cuaderno de campo.
- Endpoints: `/api/v1/farms`, `/plots` (filtro `farm_id`), `/crops`, `/operation-types` (CRUD), `/production/options`, `/production/seasons`, `/crop-cycles` (+ `/finish`, `/reopen`, `/field-book`), `/field-operations` (+ `/cancel`).
- Permisos: `production:read`, `production:write`, `production:config`, `production:reopen_cycle` (solo Soporte). Staff: read/write/config.
- Validaciones clave: fecha no futura y no anterior al inicio del ciclo; tipo de labor coherente (insumos/maquinaria/cosecha); cosecha sobre un solo ciclo; activos operativos; superficie trabajada ≤ la del ciclo; no finalizar antes de la última labor.

**Frontend** `modules/production/`: pantalla Producción con botones **Cargar labor / Cargar cosecha / Abrir ciclo**; pestañas **Ciclos** (tarjetas con costo, cosechado y rinde; filtro estado/temporada), **Labores** (lista con filtros), **Configuración** (lotes, establecimientos, cultivos, tipos de labor). `OperationDrawer` (se adapta al tipo de labor; varios ciclos con superficie editable; insumos total o por ha; maquinaria con costo a la vista; cosecha con producto del cultivo propuesto y oferta de finalizar el ciclo si es la final), `CycleDrawer` (resumen, finalizar, reabrir), `FieldBookModal`.

**Tests**: `tests/integration/test_production.py` (15).

**Ajustes tras la prueba en Chrome (27/09):**
- Insumos de una labor: el buscador muestra solo insumos, semielaborados y terminados (no la cosecha ni la reventa); el almacén muestra el stock del producto en cada uno y, al elegir el producto, se propone el que tiene stock si el elegido no tiene (`suggestWarehouse`, stock por producto con `GET /api/v1/stock?product_id=…&by_warehouse=true`).
- Tarjeta del ciclo: rinde con unidad ("0,50 cajón/ha") y 2 columnas recién desde pantallas medianas.
- El aviso de validación de la labor se actualiza mientras se corrige (desaparece al elegir el ciclo).
- Maquinaria: "($ 5.000,00 por hora)" / "por km".
