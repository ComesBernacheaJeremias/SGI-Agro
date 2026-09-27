---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-002 · Stack: Python + FastAPI + PostgreSQL + React/TypeScript

## Contexto
Un desarrollador, sistema centrado en datos, costos y reportes, < 10 usuarios.

## Alternativas evaluadas
| | Python (FastAPI) | TypeScript (NestJS) | Java (Spring Boot) |
|---|---|---|---|
| Velocidad trabajando solo | Alta | Alta | Media-baja (más código repetitivo) |
| Datos y reportes | **La mejor** | Correcta | Correcta, más verbosa |
| Lenguajes | Python + TS (frontend) | Uno solo | Java + TS |
| Tipado | Bueno con mypy | Bueno | El más fuerte |
| Swagger | Automático | Casi automático | Con librería extra |
| RAM del servidor | Baja | Baja | Alta (JVM) |

## Decisión
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Pydantic.
- **Base:** PostgreSQL 16 (relacional; stock y dinero necesitan transacciones y consistencia).
- **Frontend:** React + TypeScript + Vite + Mantine, como PWA.
Detalle en [[Stack-tecnologico]].

## Por qué
Python es el más fuerte para lo que más valor tiene (costos, rentabilidad, reportes); FastAPI valida datos y genera Swagger solo; Java agrega peso sin beneficio a esta escala. React/TS para las pantallas por ecosistema y soporte offline; el cliente de API se genera desde el backend, así los contratos no se desincronizan.

## Consecuencias
- Dos lenguajes, mitigado por el cliente generado.
- Disciplina de tipos en Python (mypy).
