---
tags: [adr]
estado: aceptada
fecha: 2026-09-28
---

# ADR-026 · "Cultivo" en lugar de "ciclo" en todo lo que ve el usuario

## Contexto
Al mejorar el manual apareció que el manual decía "cultivo" y el sistema "ciclo" para lo mismo: un cultivo en un lote en una temporada (`crop_cycle`, [[ADR-013-Ciclo-productivo-y-temporada]]). "Cultivo" es la palabra natural para el cliente. Pero el sistema ya usaba "Cultivo" para el catálogo de especies/variedades (`crop`: Tomate perita, Lechuga…), así que había que renombrar las dos cosas.

## Decisión
En **todo lo que ve el usuario** (pantallas, mensajes de error, reportes en pantalla, Excel y PDF, entidades y campos del Historial, permisos, filtros):
- `crop_cycle` (antes "ciclo") → **"Cultivo"**. Ej.: "Empezar cultivo", "Cultivos en curso", "Finalizar cultivo", "costo del cultivo".
- `crop` (antes "cultivo") → **"Tipo de cultivo"**. Ej.: Producción → Configuración → "Tipos de cultivo"; el campo al empezar un cultivo; el filtro de Rentabilidad "Tipo de cultivo"; "Ver por: Tipo de cultivo".
- **No cambia**: nombres en el código y en la base (`crop_cycle`, `crop`, `cycle_id`…), ni los comentarios y la documentación técnica, que siguen diciendo "ciclo". El mapeo está en el [[Glosario]].
- La descripción del rol Soporte (guardada en la base) se actualizó con una migración: "Uso del desarrollador: acceso total, incluido reabrir cultivos. No se asigna a usuarios de la empresa."

## Alternativas descartadas
- **Dejar "ciclo" en el sistema** y explicarlo en el manual: más simple, pero el cliente iba a ver dos palabras para lo mismo.
- **Renombrar también el código y la base**: mucho riesgo para ningún beneficio del usuario.

## Consecuencias
- ➕ Una sola palabra, la del cliente, en pantalla, reportes y manual.
- ➖ En el código "ciclo" = lo que en pantalla es "cultivo": hay que mirar el glosario. Los textos nuevos para el usuario deben decir "cultivo" / "tipo de cultivo".
