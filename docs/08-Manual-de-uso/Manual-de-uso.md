---
tags: [manual]
actualizado: 2026-09-28
---

# Manual de uso

El manual para el cliente es **una página del propio sistema**: `/manual` (ej. `https://gestion.empresa.com.ar/manual`; en desarrollo `http://localhost:5173/manual`).

- Es **pública**: se abre sin iniciar sesión. Enlaces: "¿Cómo se usa? Ver el manual" en el login, "Manual de uso" al pie del menú y el **"?" de la barra de arriba**, que abre la sección de la pantalla actual (`/manual?seccion=campo`).
- **Formato** (28/09): temas por sección (Empezar; Productos, clientes y proveedores; Campo; Stock y mezclas; Compras, ventas y plata; Máquinas; Números; Administrar).
  - Títulos en infinitivo ("Cargar una cosecha"); pasos cortos numerados (sin numerar si es uno solo o no es una secuencia).
  - Consejos en gris y **avisos importantes en ámbar**.
  - Cada tema puede terminar con un **botón que abre la pantalla o el formulario** ("Cargar una cosecha" abre Producción con el formulario de cosecha).
- **Buscador**: sin tildes, por comienzo de palabra, y con **palabras clave del campo** por tema ("fumigación", "pulverización" → cargar labor; "remito" → compra o venta; "gasoil" → gasto).
- Identidad visual del sistema: fondo piedra, logo, títulos de sección y pregunta abierta en el verde principal.
- Muestra la **dirección real del sistema** (la desde donde se abrió) con botón para copiarla.
- Necesita conexión, como todo el sistema.
- **Única fuente del texto:** `frontend/src/modules/manual/content.ts`. Si cambia una pantalla (un botón, un menú), actualizar ahí con el nombre exacto; se usa "cultivo" y "tipo de cultivo" ([[ADR-026-Cultivo-en-lugar-de-ciclo]]).

## Botones que abren formularios (reutilizable)
`frontend/src/app/actions.ts`: registro único de acciones (`ACTIONS`: clave → pantalla + texto del botón). Enlace: `actionUrl('cosecha')` → `/produccion?abrir=cosecha`.
- La pantalla de destino la atiende con `useOpenAction({ cosecha: () => … })`: abre el formulario o la pestaña y saca `?abrir=` de la dirección (al recargar no se vuelve a abrir).
- En pantallas con pestañas, `useActionTab({ receta: 'recipes' }, setTab)` elige la pestaña y la acción la atiende la pestaña (en `CrudTab`, prop `openAction`).
- Sin sesión, el login vuelve a la misma dirección (con `?abrir=`) después de entrar.
- Pensado para reutilizar desde el tablero y los avisos.
