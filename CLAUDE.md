# CLAUDE.md — SGI Agro (Sistema de Gestión Integral)

## Al iniciar cada sesión (obligatorio)
1. Leer `docs/00-Inicio.md` (estado actual, etapa en curso, próximos pasos).
2. Leer la última nota de `docs/07-Bitacora/`.
3. Antes de tocar un módulo, leer su nota en `docs/04-Modulos/` y las ADR que enlaza.

## Qué es
Sistema de gestión a medida, **desarrollado desde cero (no Odoo)**, para una empresa agrícola argentina:
frutas, hortalizas, madera, reventa de mercadería y elaboración de mezclas de agroquímicos; con tractores y camionetas.
Objetivo del cliente: **conocer la rentabilidad y analizar los costos de su negocio**. Un solo cliente.
Sin contabilidad formal (partida doble) y sin conexión con ARCA — no volver a proponerlo salvo que el usuario lo pida.

## Stack
Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16 · React + TypeScript + Vite (PWA) · Docker Compose.
Todo se desarrolla **en local**; al final se despliega en DigitalOcean. Ver `docs/03-Arquitectura/Stack-tecnologico.md`.

## Forma de trabajo con el usuario
- **Planificar antes de escribir**: no crear ni modificar archivos/documentación mientras se está planificando, salvo que el usuario lo pida.
- **Git lo ejecuta el usuario**: Claude propone los comandos (`git add`, `git commit`, `git push`…) y el usuario los corre. Claude no hace commits ni push.
- Respuestas concretas, sin vueltas: proponer, recomendar y pedir el okey.
- El usuario quiere **buenas prácticas y código bien organizado, sin repeticiones**, legible para él y para Claude; no le interesa aplicar principios a rajatabla.

## Reglas del proyecto
- **Documentación viva**: todo cambio funcional actualiza la nota del módulo en `docs/04-Modulos/`; toda decisión relevante genera una ADR en `docs/06-Decisiones/` (plantilla en `docs/_templates/`).
- **Bitácora**: al cerrar una sesión, crear/actualizar `docs/07-Bitacora/AAAA-MM-DD.md` y actualizar "Estado actual" y "Próximos pasos" en `docs/00-Inicio.md`.
- **Idioma**: UI, mensajes y documentación en español (Argentina); código en inglés con el mapeo en `docs/01-Proyecto/Glosario.md`.
- **Formatos (obligatorio en toda la UI, reportes y exportaciones)**: fechas `dd/mm/aaaa` (o `mm/aaaa` / `mm/aa` si solo importa el mes); números con puntos de miles y coma decimal (`123.456.789,12`), formateados mientras se escribe en los inputs (al escribir, punto o coma = coma decimal y no se agrega `,00` solo); precios/importes se muestran siempre con 2 decimales, cantidades 2 y hasta 3 si hace falta (`0,125`). Usar siempre los componentes/funciones compartidos de `frontend/src/shared/`, nunca formatear a mano.
- **Commits**: Conventional Commits (`feat(inventory): ...`).
- **Edición de datos**: se permite editar con confirmación; todo cambio queda en auditoría; anular en vez de borrar; un **ciclo finalizado queda bloqueado** y solo el rol `soporte` lo reabre (ver ADR-004).
- Nunca commitear secretos: `.env` ignorado, `.env.example` versionado.
- Definition of Done: `docs/05-Desarrollo/Definition-of-Done.md`.
