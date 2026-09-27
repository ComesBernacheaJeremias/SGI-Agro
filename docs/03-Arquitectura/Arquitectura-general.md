---
tags: [arquitectura]
actualizado: 2026-09-27
---

# Arquitectura general

**Monolito modular**: una sola aplicación y una sola base de datos, organizada por módulos de negocio con límites claros ([[ADR-003-Monolito-modular]]).

## Componentes

```mermaid
flowchart LR
    subgraph Navegador["Navegador (PC / celular)"]
        SPA["React (PWA)"]
        IDB[("IndexedDB\ncola offline + caché")]
        SPA <--> IDB
    end
    subgraph Servidor["Docker Compose (local o DigitalOcean)"]
        WEB["Caddy / Vite dev\narchivos del frontend"]
        API["API FastAPI\n(monolito modular)"]
        DB[("PostgreSQL 16")]
        API --> DB
    end
    SPA -->|HTTP/HTTPS| WEB
    SPA -->|/api| API
```

## Capas dentro de cada módulo

```mermaid
flowchart TD
    R["router.py\nrutas HTTP y permisos"] --> S["service.py\nreglas de negocio"]
    S --> RP["repository.py\nconsultas a la base"]
    RP --> M["models.py\ntablas"]
    R -.-> SC["schemas.py\ndatos de entrada/salida"]
    S -.-> SC
```

| Capa | Responsabilidad | No hace |
|---|---|---|
| `router` | Recibe la petición, verifica permisos, llama al service, devuelve la respuesta | Lógica de negocio |
| `service` | Reglas de negocio (stock suficiente, ciclo abierto, recálculo de costos) | SQL, HTTP |
| `repository` | Consultas y guardado | Decisiones de negocio |
| `models` / `schemas` | Tablas / formatos de entrada y salida | — |

Reglas:
1. Un módulo usa el **service** de otro módulo, nunca su repository ni sus tablas.
2. Una operación = una transacción (abierta por request). Ej.: registrar una labor descuenta stock y guarda la labor, todo o nada.
3. Lo común (auditoría, paginación, errores, permisos, base de modelos) vive en `core/` y se reutiliza — no se repite en cada módulo.

## Dependencias entre módulos

```mermaid
flowchart BT
    M02[M02 Maestros] --> M01[M01 Núcleo]
    M03[M03 Inventario] --> M02
    M07[M07 Activos] --> M02
    M04[M04 Producción] --> M03
    M04 --> M07
    M05[M05 Elaboración] --> M03
    M06[M06 Comercial y caja] --> M03
    M08[M08 Costos] --> M03
    M08 --> M04
    M08 --> M06
    M08 --> M07
    M09[M09 Reportes] --> M08
```

## Ejemplo: registrar una aplicación de insecticida
1. El secretario carga la labor "Aplicación" en el ciclo *Tomate – Lote 3*: 2 L de insecticida del Depósito y el Tractor 2 durante 1,5 h.
2. `production.service` verifica que el ciclo esté abierto, guarda la labor y pide a `inventory.service` el **consumo** → salida de stock valuada a costo promedio, con lote, ciclo, labor y temporada.
3. El uso del tractor queda registrado (1,5 h × costo por hora del activo).
4. El historial registra quién lo cargó y cuándo.
5. El costo del ciclo se calcula a partir de estos datos ([[ADR-005-Dimensiones-y-costos-calculados]]).
