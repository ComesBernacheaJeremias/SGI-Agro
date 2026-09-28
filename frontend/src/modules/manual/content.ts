/**
 * Contenido del manual de uso (página /manual). Única fuente: si cambia una pantalla,
 * se actualiza acá con el nombre exacto del botón. Títulos en infinitivo, pasos cortos en el
 * orden en que se hace la tarea, y palabras del campo para el buscador.
 */
import type { ActionKey } from '@/app/actions';

export type ManualTopic = {
  /** Lo que la persona quiere hacer, en infinitivo ("Cargar una cosecha"). */
  title: string;
  steps: string[];
  /** Pasos que no son una secuencia (explicaciones, opciones): se muestran sin numerar. */
  unordered?: true;
  /** Lista extra debajo de los pasos (ej. los roles). */
  bullets?: string[];
  /** Consejo (se muestra en gris). */
  tip?: string;
  /** Aviso importante (se muestra en ámbar). */
  warning?: string;
  /** Sinónimos y palabras del campo que usa la gente ("fumigación", "remito"…). */
  keywords?: string[];
  /** Botón del final: abre la pantalla o el formulario (ver app/actions.ts). */
  action?: ActionKey;
  /** Muestra la dirección del sistema con botón para copiarla. */
  showAddress?: true;
};

export type ManualSection = {
  id: string;
  title: string;
  /** Pantallas cuyo "?" abre esta sección. */
  paths: string[];
  topics: ManualTopic[];
};

export const MANUAL: ManualSection[] = [
  {
    id: 'empezar',
    title: 'Empezar',
    paths: ['/perfil'],
    topics: [
      {
        title: 'Entrar al sistema',
        steps: [
          'Abrí en el navegador la dirección de abajo, en la PC o en el celular.',
          'Poné tu usuario y tu contraseña.',
        ],
        showAddress: true,
        warning:
          'Si te equivocás 5 veces seguidas, la cuenta se bloquea 15 minutos: esperá o pedile al administrador que te ponga una contraseña nueva (eso la desbloquea). Si sos el administrador, esperá 15 minutos o contactá a soporte.',
        keywords: ['ingresar', 'login', 'iniciar sesión', 'dirección', 'bloqueada'],
      },
      {
        title: 'Cambiar mi contraseña',
        steps: [
          'Tocá tu nombre (arriba a la derecha) → Mi perfil → Cambiar contraseña.',
          'Poné la actual y dos veces la nueva (mínimo 10 caracteres).',
        ],
        tip: 'Al cambiarla se cierran tus sesiones abiertas en otros dispositivos.',
        keywords: ['clave', 'password'],
        action: 'perfil',
      },
      {
        title: 'Recuperar una contraseña olvidada',
        steps: [
          'Pedile al administrador que te ponga una contraseña nueva: Usuarios y roles → tu usuario → Contraseña.',
          'Entrá con esa y cambiala por una tuya en Mi perfil.',
        ],
        tip: 'Si sos el administrador y no podés entrar, contactá a soporte.',
        keywords: ['olvidé', 'recuperar', 'blanquear', 'resetear', 'clave'],
      },
      {
        title: 'Instalar en el celular',
        steps: [
          'Android: abrilo en Chrome → menú ⋮ → Instalar aplicación.',
          'iPhone: abrilo en Safari → Compartir → Agregar a inicio.',
          'Queda un ícono "SGI Agro" como cualquier aplicación.',
        ],
        keywords: ['app', 'aplicación', 'ícono', 'android', 'iphone'],
      },
      {
        title: 'Seguir trabajando si se corta internet',
        steps: [
          'Sin internet no se puede guardar: arriba aparece "Sin conexión".',
          'Usá los datos del celular, o compartilos a la PC (zona Wi-Fi).',
          'Si no hay forma, anotalo y cargalo cuando vuelva la conexión.',
        ],
        tip: 'Si se cortó justo al guardar, tocá Guardar de nuevo: no se duplica.',
        keywords: ['sin señal', 'offline', 'conexión', 'wifi', 'datos móviles'],
      },
    ],
  },
  {
    id: 'datos',
    title: 'Productos, clientes y proveedores',
    paths: ['/maestros'],
    topics: [
      {
        title: 'Crear un producto',
        steps: [
          'Maestros → Productos → Nuevo producto.',
          'Nombre, tipo (insumo, producción propia, reventa…), unidad base e IVA.',
          'Stock mínimo: con menos de esa cantidad, la campana de arriba avisa "Necesitás comprar". Vacío = sin aviso.',
        ],
        tip: 'Si lo comprás o vendés en otra unidad (bidón, cajón), agregá la equivalencia (ej. 1 cajón = 18 kg).',
        keywords: ['insumo', 'artículo', 'mercadería', 'stock mínimo', 'equivalencia', 'alta'],
        action: 'producto',
      },
      {
        title: 'Crear un cliente o proveedor',
        steps: [
          'Maestros → Clientes y proveedores → Nuevo cliente/proveedor.',
          'Marcá si es cliente, proveedor o los dos; razón social, CUIT y condición de IVA.',
          'Días de pago: con cuántos días vence cada factura (0 = contado).',
        ],
        keywords: ['tercero', 'comprador', 'cuit', 'razón social', 'alta'],
        action: 'tercero',
      },
    ],
  },
  {
    id: 'campo',
    title: 'Campo',
    paths: ['/produccion'],
    topics: [
      {
        title: 'Empezar un cultivo',
        steps: [
          'Producción → Empezar cultivo.',
          'Lote, tipo de cultivo (ej. Tomate perita), superficie en hectáreas y fecha de inicio.',
        ],
        tip: 'Los tipos de cultivo se crean en Producción → Configuración → Tipos de cultivo.',
        keywords: ['siembra', 'plantación', 'trasplante', 'temporada', 'lote', 'ciclo'],
        action: 'cultivo',
      },
      {
        title: 'Cargar una labor (aplicación, fertilización, poda…)',
        steps: [
          'Producción → Cargar labor.',
          'Fecha, tipo de labor y el cultivo (o los cultivos).',
          'Si usaste productos: cuáles y cuánto (o la dosis por hectárea).',
          'Si usaste el tractor o la camioneta: las horas o los km.',
        ],
        tip: 'Cargala el mismo día, desde el celular.',
        keywords: [
          'fumigación',
          'fumigar',
          'pulverización',
          'aplicación',
          'fertilización',
          'riego',
          'poda',
          'carpida',
          'trabajo',
          'tractor',
        ],
        action: 'labor',
      },
      {
        title: 'Cargar una cosecha',
        steps: [
          'Producción → Cargar cosecha.',
          'Cultivo, cantidad (cajones, kg…) y en qué almacén se guarda.',
          'Si es la última, marcá "¿Es la cosecha final?": el sistema ofrece finalizar el cultivo.',
        ],
        tip: 'Cada cosecha queda como una partida: al vender se elige de qué partida sale, y así se sabe cuánto ganó cada cultivo.',
        keywords: ['recolección', 'cajones', 'kilos', 'partida', 'rinde'],
        action: 'cosecha',
      },
      {
        title: 'Ver todo lo que se hizo en un cultivo',
        steps: ['Producción → tocá el cultivo → Cuaderno.'],
        keywords: ['cuaderno de campo', 'historial', 'aplicaciones', 'trazabilidad'],
      },
    ],
  },
  {
    id: 'stock',
    title: 'Stock y mezclas',
    paths: ['/inventario', '/elaboracion'],
    topics: [
      {
        title: 'Ver cuánto hay de cada cosa',
        steps: [
          'Inventario → Stock.',
          'La campana de arriba avisa lo que está por debajo del mínimo.',
        ],
        tip: 'La producción propia figura valorizada "según costo del cultivo": ver "Entender el valor de la producción propia".',
        keywords: ['existencias', 'inventario', 'faltantes', 'comprar'],
        action: 'stock',
      },
      {
        title: 'Cargar algo que entró o salió sin compra ni venta',
        steps: [
          'Inventario → Nuevo → Ingreso (o Egreso).',
          'Almacén, productos y cantidades (en un ingreso, también el costo).',
        ],
        tip: 'Las compras, ventas, labores y cosechas mueven el stock solas. Para pasar de un almacén a otro: Nuevo → Transferencia; si contaste y no coincide: Nuevo → Ajuste por conteo.',
        keywords: ['entrada', 'salida', 'rotura', 'pérdida', 'merma', 'regalo', 'conteo'],
        action: 'ingreso',
      },
      {
        title: 'Crear una receta',
        steps: [
          'Elaboración → Recetas → Nueva receta.',
          'Producto elaborado, cuánto rinde y los componentes con sus cantidades.',
        ],
        tip: 'Se hace una vez por mezcla; después cada preparación usa la receta.',
        keywords: ['fórmula', 'mezcla', 'caldo', 'componentes'],
        action: 'receta',
      },
      {
        title: 'Preparar una mezcla',
        steps: [
          'Elaboración → Nueva preparación.',
          'Elegí la receta y cuánto vas a preparar.',
          'Si falta algo, el sistema te avisa.',
        ],
        keywords: ['caldo', 'fórmula', 'elaborar', 'preparación'],
        action: 'preparacion',
      },
    ],
  },
  {
    id: 'plata',
    title: 'Compras, ventas y plata',
    paths: ['/comercial'],
    topics: [
      {
        title: 'Cargar una compra',
        steps: [
          'Comercial y caja → Compras y gastos → Nueva compra.',
          'Proveedor y datos de la factura (o "sin factura").',
          'Productos, cantidades y precios sin IVA. Si la factura no discrimina el IVA, poné el total con 0 %.',
          'Al guardar, el stock se suma solo.',
        ],
        keywords: ['factura', 'remito', 'proveedor', 'insumos', 'mercadería'],
        action: 'compra',
      },
      {
        title: 'Cargar un gasto (gasoil, reparación, servicio…)',
        steps: [
          'Con factura: Compras y gastos → Nueva compra → Agregar gasto o servicio.',
          'En efectivo sin factura: Caja y bancos → Nuevo movimiento → Tipo: Gasto.',
          'Elegí a qué corresponde: un cultivo, un lote o una máquina.',
        ],
        unordered: true,
        tip: 'Si no es de nada en particular (luz, seguros, oficina), dejalo sin destino: va a gastos de estructura.',
        keywords: ['gasoil', 'combustible', 'nafta', 'luz', 'flete', 'taller', 'servicio', 'gasto'],
        action: 'compra',
      },
      {
        title: 'Cargar una venta',
        steps: [
          'Comercial y caja → Ventas → Nueva venta.',
          'Cliente, productos, cantidades y precios.',
          'Si es producción propia, elegí la partida (el sistema propone la más vieja).',
          'Al guardar, el stock se descuenta solo.',
        ],
        keywords: ['factura', 'remito', 'cliente', 'vender'],
        action: 'venta',
      },
      {
        title: 'Cargar una nota de crédito o una devolución',
        steps: [
          'Nueva compra (o Nueva venta) → elegí Nota de crédito arriba.',
          'Comprobante asociado: la factura a la que corresponde (baja lo que queda por pagar o cobrar).',
          'Si hubo devolución de mercadería, cargá los productos: el stock se ajusta solo.',
        ],
        tip: 'Si la factura ya estaba pagada, lo de la nota de crédito queda a favor.',
        keywords: ['devolución', 'descuento', 'bonificación', 'NC', 'anular factura'],
        action: 'venta',
      },
      {
        title: 'Registrar un cobro o un pago',
        steps: [
          'Comercial y caja → Cobros → Nuevo cobro (o Pagos → Nuevo pago).',
          'Cliente o proveedor, cuánto y en qué caja o banco.',
          'Tocá "Imputar a los más viejos" para aplicarlo a las facturas pendientes.',
        ],
        tip: 'Si sobra, queda como anticipo a favor.',
        keywords: ['me pagaron', 'pagué', 'cobré', 'transferencia', 'cheque', 'efectivo'],
        action: 'cobro',
      },
      {
        title: 'Ver quién me debe y a quién le debo',
        steps: ['Comercial y caja → Cuentas corrientes.', 'Tocá un nombre para ver su detalle.'],
        keywords: ['deuda', 'saldo', 'vencido', 'cuenta corriente'],
        action: 'cuentas-corrientes',
      },
      {
        title: 'Ver cuánta plata hay en caja y en el banco',
        steps: ['Comercial y caja → Caja y bancos.'],
        keywords: ['saldo', 'efectivo', 'banco', 'caja chica'],
        action: 'caja',
      },
      {
        title: 'Pasar plata entre cajas o depositar en el banco',
        steps: [
          'Comercial y caja → Caja y bancos → Nuevo movimiento.',
          'Tipo: Transferencia entre cuentas; la cuenta de origen, la de destino y el importe.',
        ],
        tip: 'Si la plata la retira el dueño, es Tipo: Retiro.',
        keywords: ['depósito', 'depositar', 'extracción', 'transferencia', 'retiro'],
        action: 'movimiento',
      },
    ],
  },
  {
    id: 'maquinas',
    title: 'Máquinas',
    paths: ['/activos'],
    topics: [
      {
        title: 'Dar de alta una máquina',
        steps: [
          'Activos → Nuevo activo.',
          'Nombre, tipo, en qué se mide (horas o km) y la tarifa por hora o por km.',
        ],
        warning:
          'Sin tarifa, el uso de la máquina en las labores no suma costo a los cultivos (la maquinaria da $ 0).',
        tip: 'La tarifa es lo que cuesta usarla (gasoil, desgaste…); en su ficha se compara con el costo real.',
        keywords: ['tractor', 'camioneta', 'pulverizadora', 'vehículo', 'tarifa', 'alta'],
        action: 'activo',
      },
      {
        title: 'Registrar un service o una reparación',
        steps: [
          'Activos → tocá la máquina → Registrar mantenimiento.',
          'Fecha, qué se hizo y los repuestos que se usaron.',
          'Si hubo factura del taller, cargala antes como compra y elegila acá.',
        ],
        keywords: ['mantenimiento', 'service', 'taller', 'repuestos', 'arreglo'],
        action: 'activos',
      },
      {
        title: 'Anotar las horas o los km',
        steps: ['Activos → tocá la máquina → Lecturas → Cargar lectura.'],
        tip: 'La llave de arriba avisa cuando se acerca un service.',
        keywords: ['horómetro', 'odómetro', 'kilometraje', 'lectura'],
        action: 'activos',
      },
    ],
  },
  {
    id: 'numeros',
    title: 'Números',
    paths: ['/', '/costos', '/reportes'],
    topics: [
      {
        title: 'Ver cuánto gané o perdí con un cultivo',
        steps: [
          'Costos y rentabilidad → Rentabilidad.',
          'Tocá un cultivo para ver en qué se fue la plata.',
        ],
        keywords: ['ganancia', 'margen', 'rentabilidad', 'costo'],
        action: 'rentabilidad',
      },
      {
        title: 'Ver cómo viene el negocio en general',
        steps: ['Costos y rentabilidad → Resultado de gestión.', 'También en el Tablero.'],
        keywords: ['resultado', 'ganancia', 'balance', 'temporada'],
        action: 'resultado',
      },
      {
        title: 'Entender el valor de la producción propia',
        steps: [
          'La cosecha entra al stock sin costo: lo que costó producirla ya está en el cultivo.',
          'Para que no figure en $ 0, Inventario y el Tablero la muestran "según costo del cultivo": lo que costó el cultivo ÷ lo cosechado.',
          'Es solo un dato: no cambia la ganancia ni el costo de lo vendido.',
        ],
        unordered: true,
        tip: 'Si el cultivo sigue en curso dice "provisorio": el valor cambia con cada labor.',
        keywords: ['valor del stock', 'costo del cultivo', 'provisorio', 'cosecha'],
      },
      {
        title: 'Sacar un listado en Excel o PDF',
        steps: [
          'Reportes → elegí el reporte.',
          'Elegí las fechas o la temporada.',
          'Tocá Excel o PDF.',
        ],
        tip: 'Para el contador: "Libro de compras / ventas (contador)".',
        keywords: ['exportar', 'imprimir', 'contador', 'planilla', 'reporte'],
        action: 'reportes',
      },
    ],
  },
  {
    id: 'administrar',
    title: 'Administrar',
    paths: ['/usuarios', '/historial', '/importar'],
    topics: [
      {
        title: 'Crear un usuario',
        steps: ['Usuarios y roles → Nuevo usuario.', 'Nombre, usuario, contraseña y rol:'],
        bullets: [
          'Dueño: puede hacer todo.',
          'Administrativo: la carga del día a día; sus permisos se ajustan en Usuarios y roles → Roles.',
          'Solo lectura: ve todo, no puede modificar.',
          'Soporte: uso del desarrollador; no se asigna a usuarios de la empresa.',
        ],
        tip: 'Un usuario por persona: así se sabe quién cargó cada cosa.',
        keywords: ['alta', 'empleado', 'rol', 'permisos', 'acceso'],
        action: 'usuario',
      },
      {
        title: 'Cerrar la sesión en todos lados (celular perdido)',
        steps: [
          'Usuarios y roles → tocá el usuario → Cerrar sesiones.',
          'Se cierra en todos los dispositivos; hay que volver a entrar.',
          'Si alguien más puede saber la contraseña, cambiala.',
        ],
        tip: 'En Historial → Accesos se ve quién entró, desde dónde y los intentos fallidos.',
        keywords: ['perdí el celular', 'robo', 'sesión', 'seguridad'],
        action: 'usuarios',
      },
      {
        title: 'Ver quién cambió algo',
        steps: ['Botón Historial en cualquier registro, o el menú Historial.'],
        keywords: ['auditoría', 'quién', 'cambios', 'accesos'],
        action: 'historial',
      },
      {
        title: 'Cargar muchos datos desde Excel',
        steps: [
          'Importar datos → elegí qué importar → Descargar plantilla.',
          'Completala y subila → Revisar.',
          'Si no hay errores → Importar.',
        ],
        warning:
          'Importá en este orden: productos, clientes y proveedores, stock inicial y saldos (cada uno usa lo anterior).',
        keywords: ['excel', 'planilla', 'carga inicial', 'importar'],
        action: 'importar',
      },
      {
        title: 'Corregir o anular algo que ya guardé',
        steps: [
          'Abrilo y corregilo: el sistema pide confirmación.',
          'Si no tenía que existir: Anular (no se borra, queda anulado).',
          'Al anular, el stock, la cuenta corriente y la caja se recalculan solos.',
        ],
        warning:
          'Una factura con notas de crédito no se anula: primero anulá las notas. Un cultivo finalizado no se puede cambiar: si hay que corregirlo, pedíselo a soporte.',
        keywords: ['error', 'equivocación', 'borrar', 'eliminar', 'editar', 'anular'],
      },
    ],
  },
];

const normalize = (text: string) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/**
 * Secciones con los temas que contienen todas las palabras buscadas (en el título, los pasos,
 * los consejos o las palabras clave), sin tildes y por comienzo de palabra ("venta" encuentra
 * "ventas", no "inventario"; "fumigación" encuentra "Cargar una labor").
 */
export function searchManual(query: string, sections: ManualSection[] = MANUAL): ManualSection[] {
  const words = normalize(query).split(/\s+/).filter(Boolean);
  if (words.length === 0) return sections;
  return sections
    .map((section) => ({
      ...section,
      topics: section.topics.filter((topic) => {
        const text = normalize(
          [
            section.title,
            topic.title,
            ...topic.steps,
            ...(topic.bullets ?? []),
            topic.tip ?? '',
            topic.warning ?? '',
            ...(topic.keywords ?? []),
          ].join(' '),
        ).split(/[^a-z0-9]+/);
        return words.every((w) => text.some((t) => t.startsWith(w)));
      }),
    }))
    .filter((section) => section.topics.length > 0);
}

/** Sección del manual de una pantalla (para el "?" de la barra); `null` = todo el manual. */
export function sectionForPath(pathname: string): string | null {
  const matches = (path: string) =>
    path === '/' ? pathname === '/' : pathname === path || pathname.startsWith(`${path}/`);
  return MANUAL.find((s) => s.paths.some(matches))?.id ?? null;
}
