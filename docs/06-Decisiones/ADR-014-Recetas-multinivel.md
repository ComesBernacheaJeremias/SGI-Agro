---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-014 · Recetas de varios niveles con semielaborados en stock

## Contexto
El cliente quiere, como en Odoo, insumos, semielaborados y productos terminados; un terminado puede llevar insumos o semielaborados.

## Decisión
- Tipos de producto: `input` (insumo), `semi_finished` (semielaborado), `finished` (terminado), `own_produce` (producción propia), `resale` (reventa), `service` (servicio).
- Recetas de varios niveles; sin ciclos.
- **Cada preparación es de un solo nivel**: los semielaborados deben estar en stock. Si faltan, el botón **"Preparar lo que falta"** genera primero sus preparaciones y después la del terminado.
- Costo del elaborado = suma de los componentes consumidos a costo promedio.

## Alternativa descartada
Preparar los semielaborados automáticamente dentro de la preparación del terminado (tipo "kit"): oculta pasos y dificulta ver el costo y el stock de cada semielaborado.

## Consecuencias
- ➕ Cada paso queda registrado con su costo; stock de semielaborados visible.
- ➕ Mismo mecanismo para cualquier profundidad de receta.
- ➖ Un clic más cuando falta un semielaborado (mitigado por el botón).
