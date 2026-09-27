# SGI Agro — Sistema de Gestión Integral

Sistema de gestión a medida para una empresa agrícola: producción (lotes, ciclos, temporadas, labores, cosecha),
elaboración (insumos → semielaborados → terminados), inventario, compras, ventas y gastos, cuentas corrientes,
caja y bancos, activos, y **costos y rentabilidad** por ciclo, lote, cultivo y temporada.

> Estado: **F0 terminada** (entorno, login, base común). Ver `docs/01-Proyecto/Roadmap.md`.

## Documentación
`docs/` es un **vault de Obsidian** (en Obsidian: "Abrir carpeta como vault" → `docs`).
Punto de entrada: [`docs/00-Inicio.md`](docs/00-Inicio.md).

## Stack
Backend: Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 16 · uv
Frontend: React 19 · TypeScript · Vite · Mantine · TanStack Query · React Router
Entorno: Docker Compose

## Requisitos
- Docker Desktop
- Git
- Node 22 y Python 3.11+ en tu PC (solo para pre-commit y para correr herramientas del frontend fuera de Docker)

## Levantar en local
```bash
cp .env.example .env        # primera vez; revisar valores
docker compose up -d        # levanta db, api y web (la API aplica las migraciones sola)
docker compose exec api python -m app.cli create-user   # primera vez: crear tu usuario
```

| Qué | Dónde |
|---|---|
| Sistema | http://localhost:5173 |
| API — documentación interactiva (Swagger) | http://localhost:8000/api/docs |
| PostgreSQL (desde tu PC) | `localhost:5433` (usuario/clave del `.env`) |

Comandos útiles:
```bash
docker compose ps                      # estado de los servicios
docker compose logs -f api             # ver logs de la API
docker compose down                    # apagar (los datos quedan en el volumen)
docker compose up -d --build api       # tras cambiar dependencias del backend
docker compose up -d --build -V web    # tras cambiar dependencias del frontend
```

## Tests y calidad
```bash
# Backend (dentro del contenedor, contra la base sgi_agro_test)
docker compose exec api pytest
docker compose exec api ruff check .
docker compose exec api ruff format .
docker compose exec api mypy app tests

# Frontend (desde frontend/)
npm test
npm run lint
npm run typecheck
npm run format
```

pre-commit (formato, lint y detección de secretos en cada commit), una vez creado el repo git:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # opcional: revisar todo
```

## Base de datos y migraciones
```bash
# Después de crear o cambiar modelos (registrarlos en backend/app/models.py):
docker compose exec api alembic revision --autogenerate -m "descripcion"
docker compose exec api alembic upgrade head      # (también se aplica solo al reiniciar la API)
docker compose exec api alembic downgrade -1      # deshacer la última
```

## Dependencias
```bash
# Backend: editar backend/pyproject.toml y luego
docker compose run --rm --no-deps api uv lock && docker compose up -d --build api

# Frontend: desde frontend/
npm install <paquete> && docker compose up -d --build -V web

# Tipos del cliente de API (con la API levantada), desde frontend/:
npm run gen:api
```

## Variables de entorno (`.env`)
| Variable | Descripción | Ejemplo / defecto |
|---|---|---|
| `ENVIRONMENT` | `development`, `test` o `production` (en producción: logs JSON y cookie `Secure`) | `development` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales y nombre de la base (la de tests es `<POSTGRES_DB>_test`) | `sgi` / … / `sgi_agro` |
| `DB_HOST` / `DB_PORT` | Dónde la API encuentra la base (dentro de Docker: `db:5432`) | `db` / `5432` |
| `DB_HOST_PORT` | Puerto de PostgreSQL expuesto en tu PC | `5433` |
| `JWT_SECRET` | Clave para firmar los tokens. **Larga y aleatoria**; distinta en cada entorno | — |
| `ACCESS_TOKEN_MINUTES` | Duración del token de acceso | `15` |
| `REFRESH_TOKEN_DAYS` | Duración de la sesión (cookie) | `30` |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCK_MINUTES` | Intentos fallidos antes de bloquear y minutos de bloqueo | `5` / `15` |
| `API_HOST_PORT` / `WEB_HOST_PORT` | Puertos de la API y del frontend en tu PC | `8000` / `5173` |

## Estructura
```
backend/   API FastAPI: app/core (base común), app/modules/<módulo> (models, schemas, repository, service, router), alembic/, tests/
frontend/  React: src/app (layout, rutas, sesión), src/modules/<módulo>, src/shared (componentes y formatos comunes), src/api (cliente generado)
docker/    scripts de inicialización de PostgreSQL
deploy/    (F7) configuración de producción
docs/      vault de Obsidian
```
Detalle y reglas: `docs/03-Arquitectura/` y `docs/05-Desarrollo/`.
