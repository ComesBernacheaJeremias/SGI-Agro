---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-003 · Monolito modular

## Contexto
Opciones: microservicios, serverless, monolito. Un desarrollador, un cliente, pocas personas usando el sistema, y operaciones que tocan varios módulos a la vez (una labor descuenta stock y genera costo) y deben ser "todo o nada".

## Decisión
**Una sola aplicación y una sola base**, organizada por módulos de negocio con capas internas (router → service → repository). Ver [[Arquitectura-general]].

## Por qué no microservicios / serverless
Transacciones entre módulos se volverían distribuidas (mucho más complejo), más infraestructura y costo, sin beneficio a esta escala.

## Consecuencias
- ➕ Simple de desarrollar, testear, desplegar y entender.
- ➕ Si algún módulo necesitara separarse, los límites ya existen.
- ➖ Requiere respetar los límites: un módulo usa el service de otro, nunca sus tablas.
