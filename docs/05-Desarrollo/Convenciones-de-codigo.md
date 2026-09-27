---
tags: [desarrollo, calidad]
actualizado: 2026-09-27
---

# Convenciones de código

## Objetivo
Código **ordenado, legible y sin repeticiones**, que el desarrollador (o Claude) pueda abrir en cualquier momento y entender dónde está cada cosa. Buenas prácticas con criterio, no dogmas.

## Organización
- Cada módulo de negocio es una carpeta con los mismos archivos: `models`, `schemas`, `repository`, `service`, `router` ([[Arquitectura-general]]). Sabiendo el módulo, se sabe dónde buscar.
- Lo que se usa en más de un módulo va a `core/` (backend) o `shared/` (frontend): auditoría, paginación, errores, permisos, componentes de tabla y formulario, formato de números y fechas.
- Reglas de negocio **solo en los services**: ni en routers, ni en componentes React, ni en la base de datos.

## Principios que se aplican
- **Sin repetición (DRY):** si algo se repite, se extrae a una función o componente común. Ej.: un componente de tabla con filtros/paginación/exportar para todas las listas; una base de repositorio con las operaciones CRUD comunes.
- **Simple (KISS):** la solución más simple que cumpla; nada "por si acaso".
- **Una responsabilidad por archivo/clase** y **dependencias inyectadas** (los services reciben sus repositorios → se testean sin base de datos).
- **Abierto a extensión** donde el negocio crece: tipos de labor, categorías de gasto y medios de pago son datos configurables, no `if` en el código.
- Funciones cortas, nombres claros; comentarios solo para explicar el **por qué**.

## Herramientas (automáticas en cada commit con pre-commit)
| | Backend | Frontend |
|---|---|---|
| Formato | `ruff format` | Prettier |
| Lint | `ruff check` | ESLint |
| Tipos | `mypy` | `tsc` (strict) |
| Tests | pytest | Vitest |
| Secretos | gitleaks | gitleaks |

## Otras reglas
- Dinero y cantidades: siempre `Decimal`, nunca `float`.
- **Formatos visibles** ([[Requisitos-no-funcionales]]): fechas `dd/mm/aaaa` (`mm/aaaa` o `mm/aa` para meses); números `123.456.789,12` formateados al escribir (precios 2 decimales; cantidades 2, hasta 3 si hace falta). Solo a través de `shared/` (`NumberInput`, `DateInput`, `formatNumber`, `formatDate`) y, en backend, de las utilidades de `core/` para Excel/PDF. Prohibido formatear a mano en cada pantalla.
- Fechas con zona horaria; fechas de negocio como `date`.
- Código en inglés, UI en español ([[ADR-009-Codigo-en-ingles]]); términos según [[Glosario]].

## Nombres
| Cosa | Convención | Ejemplo |
|---|---|---|
| Tablas | snake_case plural | `crop_cycles` |
| Clases Python | PascalCase | `CropCycle` |
| Endpoints | kebab-case plural | `/crop-cycles` |
| Componentes React | PascalCase | `FieldOperationForm.tsx` |
| Hooks | `useXxx` | `useStockBalances` |
| Códigos de error | UPPER_SNAKE | `INSUFFICIENT_STOCK` |
| Ramas | `tipo/descripcion` | `feat/harvest-registration` |
| Commits | Conventional Commits | `feat(production): register harvest` |
