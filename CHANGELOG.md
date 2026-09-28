# Changelog

Cambios relevantes del proyecto. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado [SemVer](https://semver.org/lang/es/).
Se actualiza al cerrar cada etapa a partir de los commits (Conventional Commits).

## [Unreleased]

### Security
- Registro de accesos (Historial → Accesos), tope de intentos por IP y tope general de pedidos.
- Cerrar sesiones de un usuario; cambiar la contraseña cierra las demás sesiones; al salir se borran los datos del dispositivo.
- Producción: CSP, HSTS, tope de 10 MB, API sin root, usuario de base sin superusuario, arranque bloqueado con secretos débiles, `harden.sh` para el servidor.
- GitHub: CI (tests, tipos, lint, build, auditoría de dependencias, gitleaks) y Dependabot.
- Comandos de consola para administrar usuarios.

### Changed (diseño)
- Diseño visual propio (paleta "Monte"): menú oscuro agrupado, tablero con números clave, login nuevo, fuente IBM Plex Sans, color solo con significado, sin íconos en botones con texto.
- Logo propio (parcelas en molinete) en el menú, el login, los íconos de la app y el favicon.
- Montos negativos como `-$ 57.500,00`; faltantes de stock solo por debajo del mínimo (no igual).
- Producción propia en stock valorizada por el costo de su cultivo (solo informativo, "provisorio" si el cultivo sigue en curso) en Inventario y el tablero.
- En pantalla se dice **"cultivo"** (antes "ciclo") y **"tipo de cultivo"** (antes "cultivo"), también en reportes, Excel, PDF e Historial.
- Manual renovado: temas nuevos, buscador con palabras del campo, botones que abren el formulario y "?" en cada pantalla.
- Ventas/compras: filtro "Vencidas" y columna Estado. Activos: estado, mantenimiento y aviso "Sin tarifa". Inventario: valor total real (todas las páginas). Historial con "antes → después". Botón principal siempre en el mismo lugar; scroll horizontal solo en tablas.

### Removed
- Carga sin conexión (cola de pendientes, datos guardados en el dispositivo, ingreso sin señal): el sistema se usa con internet o datos del celular. Quedan la app instalable, el aviso "Sin conexión" y el id del dispositivo que evita duplicados al reintentar (ADR-024).

### Fixed
- "$ -0,00" en el tablero (y en cualquier número redondeado a cero).
- "por hora" / "por km" en maquinaria y activos; rinde del ciclo con unidad.

### Changed
- Insumos de una labor: solo insumos, semielaborados y terminados; se propone el almacén con stock y se ve el stock de cada almacén.
- Orden del catálogo de reportes y de las importaciones; destino de gastos sin repetir el lote; búsqueda del manual por comienzo de palabra; dispositivo resumido en Accesos; tarjetas de ciclo más anchas; aviso de la labor que se actualiza al corregir.
- IVA del producto en compras y ventas; números sin ",00" al escribir (punto o coma = coma decimal); "horas"/"km" y planes por km en rodados.

## [0.8.0] - 2026-09-27 — F7 Puesta en marcha (sin el deploy real)

### Added
- F7 (parte 4) — Manual de uso como página pública del sistema (`/manual`: preguntas con pasos cortos y buscador), lista del día de arranque y datos de ejemplo (`python -m app.cli seed-demo`).
- F7 (parte 3) — Producción: Caddy con HTTPS, API sin recarga, PostgreSQL, backups diarios a Spaces con restauración probada, scripts de deploy y restauración, Sentry opcional, Swagger oculto en producción.
- F7 (parte 2) — Carga sin conexión: app instalable, datos guardados en el dispositivo, labores/cosechas, movimientos de stock y preparaciones en cola que se envían al volver la señal (sin duplicar), indicador de pendientes.
- F7 (parte 1) — Importar datos desde Excel: productos, clientes y proveedores, stock inicial y saldos iniciales de cuentas corrientes; plantillas descargables, vista previa con errores por fila y "todo o nada".

## [0.7.0] - 2026-09-27 — F6 Activos completo

### Added
- Lecturas de horómetro/odómetro y lectura actual estimada (última lectura + labores posteriores).
- Planes de mantenimiento por activo (cada horas/km y/o meses) con estados al día / próximo / vencido; campana de mantenimientos y tarjeta en el tablero.
- Mantenimientos preventivos y correctivos: repuestos que salen del stock y compra del servicio vinculada.
- Ficha del activo: uso, gasto real, costo real por hora/km comparado con la tarifa, planes, mantenimientos, gastos y lecturas.
- Reporte "Costo por activo" (Excel/PDF).

### Changed
- Resultado de gestión: los repuestos de mantenimientos suman a los costos de producción.

## [0.6.0] - 2026-09-27 — F5 Costos, rentabilidad y reportes

### Added
- Costos y rentabilidad: rentabilidad por ciclo, cultivo y temporada, cultivo, temporada, lote o establecimiento; detalle de costos de un ciclo (insumos, maquinaria, gastos, por labor, por mes, ventas por partida).
- Resultado de gestión por período (ventas − costo de lo vendido − costos de producción − mermas − estructura).
- Costos por lote, gastos (con los de estructura) y margen por producto.
- Reportes con filtros y exportación a Excel y PDF: ventas, compras y gastos, libro para el contador, saldos, movimientos de caja, stock valorizado.
- Tablero: resultado de la temporada vs. la anterior, ciclos en curso, cuentas corrientes, cajas y stock.
- Nota de crédito/débito con comprobante asociado (la NC se aplica sola a la factura) y devolución a una partida.
- Permiso "Costos y rentabilidad" (el secretario no lo tiene por defecto).

## [0.5.0] - 2026-09-27 — F4 Comercial y caja

### Added
- Compras y ventas (factura, nota de crédito, nota de débito), con o sin factura: número interno CPR-/VTA- y letra/PV/número si la hubo; control de duplicados.
- Líneas de producto (mueven stock: compra al costo neto, venta a costo promedio, devoluciones con NC) y de gasto/concepto con categoría y destino (ciclo, lote, establecimiento, activo).
- Venta de producción propia por partida, las más antiguas primero.
- Cobros y pagos con medios (efectivo, transferencia) por caja o banco, imputación parcial o total y anticipos.
- Cuentas corrientes: resumen por tercero con saldo acumulado y saldos a cobrar/pagar con antigüedad (1-30, 31-60, 61-90, +90).
- Caja y bancos: saldos, movimientos sin tercero (ingreso, gasto, retiro, transferencia) y resumen por cuenta.
- Costo del ciclo: nuevo rubro "Servicios y gastos" (compras y caja con destino en el ciclo).

### Changed
- Equivalencias de producto: se cargan como "1 [unidad del producto] = cantidad [otra unidad]".
- Comprobantes de stock generados por compras y ventas: numeración RCP-/DSP-.

## [0.4.0] - 2026-09-27 — F3 Producción, elaboración y activos

### Added
- Producción: establecimientos, lotes, cultivos, tipos de labor, temporadas automáticas (1/7 → 30/6) y ciclos productivos con control de superficie.
- Labores con insumos (cantidad total o dosis por hectárea), maquinaria (tarifa por hora o km del momento) y reparto por superficie entre varios ciclos; consumo de stock marcado con lote y ciclo.
- Cosecha con partida, ingreso al stock y rinde; oferta de finalizar el ciclo en la cosecha final.
- Finalizar ciclo congela sus costos; reabrir solo Soporte (con motivo).
- Tablero de ciclos (costo, cosechado, rinde, costo/ha, costo/kg) y cuaderno de campo.
- Elaboración: recetas de varios niveles, preparaciones con costo = lo consumido, verificación de faltantes y "Preparar lo que falta".
- Activos (alta básica): tractores, camionetas, herramientas con tarifa y estado.

### Changed
- Motor de stock: costo derivado para elaboración con recálculo en cascada; movimientos congelados.
- No se puede cambiar la unidad base de un producto con movimientos.

## [0.3.0] - 2026-09-27 — F2 Inventario

### Added
- Comprobantes de stock: ingreso (con costo; sirve para stock inicial), egreso, transferencia entre almacenes y ajuste por conteo (permiso aparte). Numeración ING/EGR/TRF/AJU.
- Motor de stock: costo promedio ponderado con recálculo al editar o cargar con fecha pasada; nunca stock negativo en ningún momento; cargas simultáneas serializadas.
- Carga en cualquier unidad del producto (cajón, bidón, g, tn…) con conversión a la unidad base.
- Consultas: stock por producto o almacén, a una fecha, valorizado; kardex con saldo; edición y anulación con historial.
- Aviso "Necesitás comprar" cuando un producto llega a su stock mínimo (campana en la barra superior, aviso al guardar, filtro "Bajo mínimo").
- Buscador de productos en servidor reutilizable (`ProductSelect`).

## [0.2.0] - 2026-09-27 — F1 Núcleo y maestros

### Added
- Roles y permisos: un rol por usuario; roles fijos Soporte, Dueño y Solo lectura con permisos calculados; rol Administrativo y roles propios editables.
- Gestión de usuarios (alta, edición, desactivar, resetear contraseña) y de roles con permisos por módulo; Mi perfil (cambiar contraseña, cerrar todas las sesiones).
- Historial automático de cambios (quién, cuándo, antes → después) con botón "Historial" en cada registro y pantalla de historial general con filtros.
- Maestros: unidades (con conversiones por tipo), categorías jerárquicas, productos (código automático por tipo, equivalencias propias como 1 cajón = 18 kg), clientes/proveedores (validación de CUIT), almacenes.
- Búsqueda sin distinguir tildes ni mayúsculas; confirmación "¿Estás seguro?" al editar, desactivar o eliminar.
- Piezas genéricas para entidades (backend: CrudRepository, CrudService, crud_router; frontend: CrudTab, DataTable, EntityDrawer, RecordActions) y guía para sumar entidades nuevas.

### Fixed
- El autor de los cambios se perdía entre hilos de FastAPI: ahora se comparte un contexto por request.

## [0.1.0] - 2026-09-27 — F0 Preparación

### Added
- Documentación de planificación (vault de Obsidian en `docs/`): alcance, módulos con historias de usuario, arquitectura, modelo de datos, prácticas de desarrollo y ADRs.
- Entorno local con Docker Compose: PostgreSQL 16, API FastAPI y frontend Vite, con recarga automática y migraciones al iniciar.
- Base común del backend: configuración, sesión por request, modelo base (UUIDv7, fechas y autoría automáticas), formato único de errores en español, logs estructurados con request id, paginación, health checks, Alembic.
- Login: usuarios, sesión de 30 días con token rotativo en cookie segura, bloqueo tras 5 intentos, detección de reutilización de tokens, comando `create-user`.
- Frontend: login, pantalla principal con menú de módulos, renovación automática de la sesión, cliente de API tipado generado desde OpenAPI.
- Componentes compartidos de formato: `NumberInput` (123.456.789,12; precios 2 decimales, cantidades hasta 3), `DateInput` (dd/mm/aaaa), `formatNumber`, `formatMoney`, `formatDate`.
- Calidad: Ruff, mypy, pytest; ESLint, Prettier, Vitest; pre-commit con gitleaks.
