---
tags: [arquitectura, repo]
actualizado: 2026-09-27
---

# Estructura del repositorio

Monorepo (un solo repo). Se crea en F0.

```
Proyecto/
├── CLAUDE.md                 # contexto y reglas para Claude
├── README.md                 # qué es, cómo levantarlo, variables de entorno
├── CHANGELOG.md
├── .env.example              # variables necesarias, sin secretos
├── .gitignore
├── docker-compose.yml        # entorno local: db, api, web
├── .pre-commit-config.yaml
│
├── backend/
│   ├── pyproject.toml        # dependencias (uv) + config de ruff, mypy, pytest
│   ├── Dockerfile
│   ├── alembic/              # migraciones
│   ├── app/
│   │   ├── main.py           # crea la app y registra los routers
│   │   ├── core/             # lo común: config, db, seguridad, auditoría, errores, paginación, modelo base
│   │   └── modules/
│   │       ├── identity/     # M01
│   │       ├── masterdata/   # M02
│   │       ├── inventory/    # M03
│   │       ├── production/   # M04
│   │       ├── manufacturing/# M05
│   │       ├── commercial/   # M06
│   │       ├── assets/       # M07
│   │       ├── costs/        # M08
│   │       └── reports/      # M09
│   │           # cada módulo: models.py, schemas.py, repository.py, service.py, router.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── factories.py
│
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   └── src/
│       ├── api/              # cliente generado desde OpenAPI
│       ├── app/              # layout (con aviso "Sin conexión"), rutas, proveedores, sesión
│       ├── modules/<modulo>/ # pantallas por módulo
│       └── shared/           # componentes y utilidades comunes (tablas, formularios, formato de números/fechas)
│
├── docker/postgres/init/     # scripts de inicialización de PostgreSQL (crea la base de tests)
├── deploy/                   # (F7) compose de producción, Caddyfile, scripts de backup
└── docs/                     # vault de Obsidian
```

Regla: si algo se usa en más de un módulo, va a `core/` (backend) o `shared/` (frontend).
