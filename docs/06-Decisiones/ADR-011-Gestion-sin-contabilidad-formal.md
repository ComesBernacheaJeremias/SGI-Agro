---
tags: [adr]
estado: aceptada
fecha: 2026-09-27
---

# ADR-011 · Gestión sin contabilidad formal

## Contexto
El PDF menciona "integración con contabilidad" y "obligaciones fiscales (estructura base)". El cliente quiere **conocer la rentabilidad y analizar costos**; no necesita conexión con ARCA ni partida doble. El contador lleva la contabilidad por fuera.

## Decisión
- **Sin** plan de cuentas, asientos, balance ni conexión con ARCA.
- **Sí:** comprobantes de compra y venta registrados (con condición de IVA y alícuotas), cuentas corrientes, **caja y bancos**, gastos por categoría y destino, y **resultado de gestión** (ingresos − costos directos − gastos de estructura).
- **Gastos de estructura** (sin destino) se muestran aparte, **no se reparten** entre ciclos.
- Exportación de compras y ventas en Excel para el contador.

## Consecuencias
- ➕ Mucho menos alcance y riesgo; foco en lo que el cliente valora.
- ➕ Si en el futuro se necesita contabilidad formal, los comprobantes y movimientos ya tienen la información para generarla.
