---
tags: [desarrollo, testing]
actualizado: 2026-09-27
---

# Estrategia de testing

## Qué se testea
| Tipo | Qué cubre | Herramienta |
|---|---|---|
| **Unitarios** | Reglas de negocio en los services: stock negativo, costo promedio y recálculo, ciclo finalizado bloqueado, hectáreas del lote, imputaciones de pagos, costo de mezclas | pytest |
| **Integración** | Endpoints contra PostgreSQL real (en Docker): permisos, errores, flujos entre módulos (labor → stock → costo), historial | pytest + TestClient |
| **Frontend** | Componentes con lógica (formularios, cálculo dosis/ha, cola offline) | Vitest + Testing Library |
| **Flujos completos (E2E)** | Más adelante (F5/F7) para los flujos críticos: compra → labor → cosecha → venta → cobro | Playwright |

## Reglas
- Nunca SQLite para tests: siempre PostgreSQL (mismo comportamiento que producción).
- Cada test de integración corre en una transacción que se revierte → rápidos y aislados.
- Todo bug corregido lleva un test que lo reproduce.
- Cada historia de usuario tiene tests de sus criterios de aceptación.
- Meta orientativa: ≥ 80 % de cobertura en los services.

## Cómo se corren
```bash
docker compose run --rm api pytest          # backend
docker compose run --rm web npm test        # frontend
```
(comandos definitivos en el README al terminar F0)
