---
tags: [adr]
estado: aceptada
fecha: 2026-09-28
---

# ADR-025 · Diseño visual propio: paleta "Monte"

## Contexto
El sistema usaba Mantine casi sin personalizar (verde estándar, fuente del sistema, íconos en todos lados, "Hola, X") y el usuario sentía que "parecía hecho con IA". El cliente no tiene logo. Se armaron dos propuestas (A · Campo, oliva y ocre; B · Monte, verde bosque y terracota) y el usuario eligió la **B** con ajustes.

## Decisión
- **Paleta** (`frontend/src/app/theme/palette.ts`): principal verde bosque `#1F4D3A`; fondo piedra `#F4F5F2`; texto `#1E2521`; texto secundario verde apagado `#5B6B62` (nunca gris claro); menú y panel `#16362A`. Cada color se define por su tono base y se generan los 10 tonos de Mantine; pisan los colores de Mantine (`red`, `green`, `yellow`…) para que todo el sistema los use.
- **Color solo con significado:** rojo ladrillo `#A8432F` = vencido, negativo, error; ámbar `#B8892F` = faltantes de stock (`STOCK_ALERT_COLOR`). Las tarjetas son todas iguales, sin franjas de color.
- **Fuente:** IBM Plex Sans, instalada en el proyecto (`@fontsource`, la CSP no permite fuentes externas). Números de ancho fijo en todo el sistema.
- **Tema centralizado** (`app/theme/theme.ts`): colores, fuente, fondo, texto secundario y estilos por defecto de los componentes. Las pantallas no definen colores sueltos.
- **Menú lateral oscuro**, columna completa con el nombre arriba (`AppShell layout="alt"`), agrupado en Día a día / Análisis / Administración. Íconos en un solo tono claro apagado; el ítem activo, fondo verde más claro y texto blanco.
- **Íconos** solo en el menú y en acciones chicas sin texto (campanas, borrar, editar); ninguno en botones con texto ni en títulos.
- **Componentes compartidos:** `PageHeader` (título, subtítulo y línea corta verde), `InfoCard` (tarjeta de resumen con título chico en mayúsculas).
- **Tablero:** "Tablero · Temporada …" y fila de números clave (Resultado, A cobrar, Caja y bancos, Valor del stock); la columna "Anterior" se oculta si la temporada anterior no tiene datos.
- **Login:** panel oscuro con nombre y frase + formulario.
- **Montos negativos:** `-$ 57.500,00` (frontend `formatMoney` y backend `format_money`).
- **Faltantes de stock:** solo si hay **menos** que el mínimo (antes también si era igual).

- **Logo** (28/09): cuatro parcelas en molinete con la de abajo a la derecha en terracota, texto en IBM Plex Sans SemiBold. Archivos, geometría y usos en [[Marca]] (`docs/assets/marca/`).

## Alternativas descartadas
- **A · Campo** (oliva y ocre, menú claro): el usuario prefirió la B.
- **Color por módulo** (franjas e íconos de colores distintos): se probó y se sacó; distraía y no significaba nada.

## Consecuencias
- ➕ Identidad propia y consistente, cambiable desde un solo archivo.
- ➕ Cuando haya logo, va en el menú, el login y el ícono de la app, con estos colores.
- ➖ Mantine sigue siendo la base: componentes nuevos deben usar el tema y los componentes compartidos, no colores sueltos.
