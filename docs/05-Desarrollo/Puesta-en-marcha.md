---
tags: [desarrollo, puesta-en-marcha]
actualizado: 2026-09-27
---

# Puesta en marcha (día de arranque)

Lista para el día en que el cliente empieza a usar el sistema. Servidor: [[Entorno-local-y-deploy]]. Manual para los usuarios: la página `/manual` del sistema ([[Manual-de-uso]]).

## Antes (semana previa)
- [ ] Servidor publicado con dominio y HTTPS; **backup a Spaces funcionando y una restauración de prueba hecha**.
- [ ] Alertas de DigitalOcean (CPU, memoria, disco) y, si se usa, Sentry.
- [ ] Usuarios: Soporte (desarrollador), Dueño, Administrativo (secretario). Revisar los permisos del rol Administrativo (costos, ajustes).
- [ ] Juntar del cliente, en Excel: productos (con unidades y equivalencias), clientes/proveedores (con CUIT), stock al día de arranque (con costo), saldos pendientes de clientes y proveedores, saldo de cada caja y banco.
- [ ] Demostración con datos de ejemplo (en local: `python -m app.cli seed-demo` en una base vacía) y mostrarles la página `/manual`.

## Día de arranque (en este orden)
1. **Configuración** (a mano): establecimientos y lotes, cultivos, almacenes, activos (con tarifas), cajas y bancos **con saldo inicial a la fecha de arranque**, categorías de gasto si faltan.
2. **Importar** (*Importar datos*): productos → clientes y proveedores → **stock inicial** (fecha de arranque) → **saldos iniciales** de cuentas corrientes.
3. **Ciclos en curso**: crear los ciclos activos con su fecha real de inicio. (Las labores anteriores al arranque no se cargan salvo que el cliente quiera su costo histórico.)
4. **Planes de mantenimiento** y una lectura de horómetro/odómetro por activo.
5. **Verificar contra las planillas del cliente**:
   - [ ] *Reportes → Stock valorizado*: cantidades y valor total.
   - [ ] *Reportes → Saldos de cuentas corrientes*: clientes y proveedores, uno por uno los más grandes.
   - [ ] *Caja y bancos*: saldo de cada cuenta.
6. **Instalar la app** en el celular del dueño y del secretario y hacer una carga de prueba sin señal (modo avión) → ver que se sincroniza.

## Primeras semanas
- Semana 1: revisar juntos las labores y compras cargadas; corregir hábitos (destinos de gastos, partidas en ventas).
- Fin del primer mes: repasar *Rentabilidad* y *Resultado de gestión* con el dueño.
- Verificar que los backups diarios siguen llegando a Spaces.
