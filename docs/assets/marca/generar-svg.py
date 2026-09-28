"""Genera el logo de SGI Agro en SVG (geometría exacta + texto convertido a trazos)."""

import pathlib

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

OUT = pathlib.Path(__file__).resolve().parent  # docs/assets/marca
ROOT = OUT.parents[2]
FONT = ROOT / "frontend/node_modules/@fontsource/ibm-plex-sans/files/ibm-plex-sans-latin-600-normal.woff2"

# --- Paleta (ADR-025) ---
FOREST = "#1F4D3A"  # parcelas sobre fondo claro
GREEN = "#2E6A4F"  # parcelas sobre fondo oscuro
TERRACOTTA = "#C4622D"  # parcela destacada
PANEL = "#16362A"  # fondo oscuro / tinta oscura
LIGHT = "#E9EFEA"  # texto sobre oscuro / tinta clara


def parcels(size: float = 100, gap: float = 6, center: float = 14, radius: float = 3):
    """Molinete: 4 parcelas iguales (w × l) alrededor de un cuadrado central.

    size = 2·w + center + 2·gap  →  w = (size − center − 2·gap) / 2;  l = size − w − gap.
    Devuelve [(x, y, ancho, alto, rol)], rol: 'tl', 'tr', 'br' (destacada), 'bl', 'center'.
    """
    w = (size - center - 2 * gap) / 2
    l = size - w - gap
    c0 = w + gap
    rects = [
        (0, 0, w, l, "tl"),  # vertical arriba a la izquierda
        (c0, 0, l, w, "tr"),  # horizontal arriba a la derecha
        (size - w, c0, w, l, "br"),  # vertical abajo a la derecha (destacada)
        (0, size - w, l, w, "bl"),  # horizontal abajo a la izquierda
    ]
    if center:
        rects.append((c0, c0, center, center, "center"))
    return rects, radius


def symbol(fill: str, accent: str, *, dx=0.0, dy=0.0, scale=1.0, **geometry) -> str:
    rects, radius = parcels(**geometry)
    parts = []
    for x, y, w, h, role in rects:
        color = accent if role == "br" else fill
        r = min(radius, w / 2, h / 2)
        parts.append(
            f'<rect x="{dx + x * scale:g}" y="{dy + y * scale:g}" width="{w * scale:g}" '
            f'height="{h * scale:g}" rx="{r * scale:g}" fill="{color}"/>'
        )
    return "\n  ".join(parts)


def text_path(text: str, x: float, baseline: float, cap_height: float) -> tuple[str, float]:
    """Texto convertido a trazos (IBM Plex Sans SemiBold). Devuelve (path d, ancho)."""
    font = TTFont(FONT)
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    cap = font["OS/2"].sCapHeight
    scale = cap_height / cap
    pen = SVGPathPen(glyphs, lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    cursor = 0.0
    for ch in text:
        name = cmap[ord(ch)]
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x + cursor * scale, baseline)))
        cursor += font["hmtx"][name][0]
    return pen.getCommands(), cursor * scale


def svg(width: float, height: float, body: str, background: str | None = None) -> str:
    bg = f'<rect width="{width:g}" height="{height:g}" fill="{background}"/>\n  ' if background else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
        f'width="{width:g}" height="{height:g}">\n  {bg}{body}\n</svg>\n'
    )


def write(name: str, content: str) -> None:
    (OUT / f"{name}.svg").write_text(content, encoding="utf-8", newline="\n")


# --- Horizontal: símbolo de 100 + separación + texto (altura de mayúsculas 54) ---
CAP, GAP_TEXT, PAD_BOTTOM = 54, 24, 6
baseline = 50 + CAP / 2  # mayúsculas centradas en el símbolo
d, text_width = text_path("SGI Agro", 100 + GAP_TEXT, baseline, CAP)
width, height = 100 + GAP_TEXT + text_width, 100 + PAD_BOTTOM  # lugar para la "g"
for variant, fill, ink in (("claro", FOREST, FOREST), ("oscuro", GREEN, LIGHT)):
    body = symbol(fill, TERRACOTTA) + f'\n  <path d="{d}" fill="{ink}"/>'
    write(f"logo-horizontal-{variant}", svg(width, height, body))

# --- Símbolo solo ---
write("simbolo-claro", svg(100, 100, symbol(FOREST, TERRACOTTA)))
write("simbolo-oscuro", svg(100, 100, symbol(GREEN, TERRACOTTA)))

# --- Una tinta (todo del mismo color) ---
write("una-tinta-claro", svg(100, 100, symbol(PANEL, PANEL)))  # tinta oscura, para fondo claro
write("una-tinta-oscuro", svg(100, 100, symbol(LIGHT, LIGHT)))  # tinta clara, para fondo oscuro
body = symbol(PANEL, PANEL) + f'\n  <path d="{d}" fill="{PANEL}"/>'
write("logo-horizontal-una-tinta", svg(width, height, body))


# --- Íconos de app: fondo oscuro redondeado + símbolo ---
def app_icon(size: int, padding: float, corner: float, **geometry) -> str:
    inner = size - 2 * padding
    bg = f'<rect width="{size}" height="{size}" rx="{corner:g}" fill="{PANEL}"/>'
    return svg(size, size, bg + "\n  " + symbol(GREEN, TERRACOTTA, dx=padding, dy=padding,
                                                 scale=inner / 100, **geometry))


write("icono-192", app_icon(192, 38, 40))
write("icono-512", app_icon(512, 100, 106))
# "maskable": fondo a sangre (Android recorta la forma) y símbolo dentro del círculo seguro
write("icono-maskable-512", app_icon(512, 136, 0))
write("apple-touch-180", app_icon(180, 36, 0))  # iOS redondea solo
# Favicon simplificado: sin cuadrado central y separaciones más anchas (se lee a 32 px)
write("favicon-32", app_icon(32, 5, 7, gap=10, center=0, radius=4))

print("SVG generados en", OUT)
print(f"horizontal: {width:.1f} x {height:.1f}")
