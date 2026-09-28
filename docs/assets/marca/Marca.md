---
tags: [marca, diseño]
actualizado: 2026-09-28
---

# Marca: logo de SGI Agro

Símbolo: **cuatro parcelas en molinete** alrededor de un cuadrado central; la de abajo a la derecha, destacada en terracota. Texto "SGI Agro" en IBM Plex Sans SemiBold, convertido a trazos (no depende de la fuente instalada). Colores de [[ADR-025-Diseno-visual]].

![[simbolo-claro.png|120]]

## Geometría (grilla de 100 × 100)
- Separación entre piezas: **6**; cuadrado central: **14**; parcelas: **37 × 57**; radio de esquina: **3** en todas.
- Fórmula: `100 = 2·ancho + central + 2·separación`, `largo = 100 − ancho − separación`.
- Favicon (32 px) simplificado: sin cuadrado central y separaciones de 10, para que se lea chico.

## Colores
| Uso | Color |
|---|---|
| Parcelas sobre fondo claro | `#1F4D3A` |
| Parcelas sobre fondo oscuro | `#2E6A4F` |
| Parcela destacada | `#C4622D` |
| Fondo de los íconos / tinta oscura | `#16362A` |
| Texto sobre oscuro / tinta clara | `#E9EFEA` |

## Archivos (SVG y PNG transparente)
| Archivo | Para qué |
|---|---|
| `logo-horizontal-claro` | Símbolo + texto, sobre fondo claro (documentos, PDF) |
| `logo-horizontal-oscuro` | Símbolo + texto, sobre fondo oscuro (menú, login) |
| `logo-horizontal-una-tinta` | Una sola tinta oscura (sellos, impresión a un color) |
| `simbolo-claro` / `simbolo-oscuro` | Solo el símbolo |
| `una-tinta-claro` / `una-tinta-oscuro` | Símbolo a una tinta (oscura para fondo claro, clara para fondo oscuro) |
| `icono-192`, `icono-512` | Ícono de la app instalable |
| `icono-maskable-512` | Ícono de Android (fondo a sangre; el sistema recorta la forma) |
| `apple-touch-180` | Ícono de iPhone/iPad |
| `favicon-32` | Pestaña del navegador (simplificado) |
| `referencia.png` | Imagen de referencia original |

## Dónde se usa en el sistema
- **Menú lateral** (PC) y **login**: `logo-horizontal-oscuro`; **barra del celular**: `logo-horizontal-claro`. Copias en `frontend/src/assets/`, usadas por el componente `shared/ui/Logo.tsx`.
- **Íconos de la app y favicon** en `frontend/public/`: `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `apple-touch-icon.png` (180), `favicon.svg` y `favicon-32.png`. Color de la app instalable (`theme_color`): `#16362A`.
- Si se regenera el logo, volver a copiar esos archivos.

## Regenerar
`generar-svg.py` (Python + `fontTools`; lee la fuente de `frontend/node_modules/@fontsource/ibm-plex-sans`) y `generar-png.cjs` (ver su encabezado). Los cambios de geometría o colores se hacen en el script, no a mano en los SVG.
