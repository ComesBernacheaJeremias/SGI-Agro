---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-009 · Código en inglés, UI y documentación en español

## Contexto
Mezclar idiomas en el código genera nombres inconsistentes. Las librerías y frameworks están en inglés.

## Decisión
- **Código** (tablas, clases, funciones, endpoints, commits): inglés.
- **UI, mensajes al usuario y documentación:** español (Argentina).
- El mapeo de términos está en el [[Glosario]]; se consulta/actualiza antes de nombrar algo nuevo.

## Consecuencias
- ➕ Nombres predecibles y consistentes.
- ➖ Hay que traducir términos del dominio (el glosario evita que "lote" sea `lot`, `plot` y `field` en distintos lugares).
