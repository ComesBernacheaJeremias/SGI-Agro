---
tags: [desarrollo, git]
actualizado: 2026-09-27
---

# Flujo Git

- **El desarrollador ejecuta los comandos de git.** Claude propone los comandos exactos (`git add`, `git commit`, `git push`) al terminar cada tarea; no hace commits ni push por su cuenta.
- Repositorio privado en GitHub (respaldo y historial): https://github.com/ComesBernacheaJeremias/SGI-Agro.git — rama `main`. Primer commit y push: 27/09/2026 (`feat: SGI Agro F0-F7`).
- Los scripts de `deploy/` se versionan como ejecutables (`git update-index --chmod=+x`), y `.gitattributes` fuerza fin de línea LF en scripts y configuración que corren en Linux.

## Ramas
- `main`: siempre funcionando.
- Para trabajos de más de un día o riesgosos: rama `feat/<descripcion>` o `fix/<descripcion>`, y se integra a `main` al terminar.
- Cambios chicos: directo en `main` está bien (un solo desarrollador).

## Commits (Conventional Commits)
`tipo(modulo): descripción en imperativo`
- Tipos: `feat` (funcionalidad), `fix` (corrección), `docs`, `refactor`, `test`, `chore` (mantenimiento).
- Módulo en inglés: `inventory`, `production`, `commercial`…
- Ejemplos: `feat(production): register harvest with batch` · `fix(inventory): block negative stock on edit` · `docs: update M04 note`

## Versiones y CHANGELOG
- Versiones `v0.x` durante el desarrollo; `v1.0.0` al entrar en producción.
- `CHANGELOG.md` actualizado al cerrar cada etapa (F0, F1…), a partir de los commits.

## Antes de cada commit
pre-commit corre formato, lint y detección de secretos automáticamente (una vez instalado: `pip install pre-commit` + `pre-commit install`; **todavía no instalado**). Si falla, se corrige y se vuelve a commitear.
