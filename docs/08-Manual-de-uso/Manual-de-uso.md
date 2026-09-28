---
tags: [manual]
actualizado: 2026-09-27
---

# Manual de uso

El manual para el cliente es **una página del propio sistema**: `/manual` (ej. `https://gestion.empresa.com.ar/manual`; en desarrollo `http://localhost:5173/manual`).

- Es **pública**: se abre sin iniciar sesión (sirve, por ejemplo, para instalar la app). Enlaces: "¿Cómo se usa? Ver el manual" en el login y "Manual de uso" al pie del menú.
- Formato: preguntas "¿Cómo hago…?" por tema (Empezar, Campo, Stock y mezclas, Compras/ventas y plata, Máquinas, Números, Administrar), cada una con 1 a 5 pasos cortos y a veces un consejo; buscador sin tildes.
- Necesita conexión, como todo el sistema.
- **Única fuente del texto:** `frontend/src/modules/manual/content.ts`. Si cambia una pantalla (un botón, un menú), actualizar ahí; los pasos usan los nombres exactos de los botones.
