// Convierte los SVG del logo a PNG con fondo transparente (los íconos llevan su propio fondo).
// Uso (en una carpeta temporal, no es dependencia del proyecto):
//   npm install @resvg/resvg-js@2  &&  node generar-png.cjs
const fs = require('node:fs');
const path = require('node:path');
const { Resvg } = require('@resvg/resvg-js');

const dir = __dirname; // docs/assets/marca
// Ancho en px de cada PNG (los íconos, a su tamaño exacto)
const WIDTHS = {
  'logo-horizontal-claro': 1200,
  'logo-horizontal-oscuro': 1200,
  'logo-horizontal-una-tinta': 1200,
  'simbolo-claro': 512,
  'simbolo-oscuro': 512,
  'una-tinta-claro': 512,
  'una-tinta-oscuro': 512,
  'icono-192': 192,
  'icono-512': 512,
  'icono-maskable-512': 512,
  'apple-touch-180': 180,
  'favicon-32': 32,
};

for (const [name, width] of Object.entries(WIDTHS)) {
  const svg = fs.readFileSync(path.join(dir, `${name}.svg`), 'utf8');
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: width } }).render().asPng();
  fs.writeFileSync(path.join(dir, `${name}.png`), png);
  console.log(`${name}.png`, width);
}
