/**
 * Contenido del manual de uso (página /manual). Única fuente: si cambia una pantalla,
 * se actualiza acá. Lenguaje simple, pasos cortos, en el orden en que se hace la tarea.
 */

export type ManualTopic = {
  /** Lo que la persona quiere hacer, como lo diría ella. */
  question: string;
  steps: string[];
  tip?: string;
};

export type ManualSection = { id: string; title: string; topics: ManualTopic[] };

export const MANUAL: ManualSection[] = [
  {
    id: 'empezar',
    title: 'Empezar',
    topics: [
      {
        question: '¿Cómo entro?',
        steps: [
          'Abrí la dirección del sistema en el navegador.',
          'Poné tu usuario y contraseña.',
          'Para cambiar la contraseña: tu nombre (arriba a la derecha) → Mi perfil.',
        ],
        tip: 'Si te equivocás 5 veces, la cuenta se bloquea 15 minutos.',
      },
      {
        question: '¿Cómo lo instalo en el celular?',
        steps: [
          'Android: abrilo en Chrome → menú ⋮ → Instalar aplicación.',
          'iPhone: abrilo en Safari → Compartir → Agregar a inicio.',
          'Queda un ícono "SGI Agro" como cualquier aplicación.',
        ],
      },
      {
        question: '¿Puedo cargar sin señal?',
        steps: [
          'Sí: labores, cosechas, movimientos de stock y mezclas.',
          'Arriba aparece "Sin conexión". Cargá normal; queda "pendiente".',
          'Cuando vuelve la señal se envía solo.',
        ],
        tip: 'Tenés que haber entrado al menos una vez con señal en ese celular.',
      },
    ],
  },
  {
    id: 'campo',
    title: 'Campo',
    topics: [
      {
        question: 'Empezar un cultivo en un lote',
        steps: [
          'Producción → Abrir ciclo.',
          'Elegí el lote, el cultivo, las hectáreas y la fecha de inicio.',
        ],
      },
      {
        question: 'Cargar un trabajo (aplicación, fertilización, poda…)',
        steps: [
          'Producción → Cargar labor.',
          'Fecha, tipo de trabajo y el lote (o los lotes).',
          'Si usaste productos: cuáles y cuánto (o la dosis por hectárea).',
          'Si usaste el tractor o la camioneta: las horas o los km.',
          'Guardar.',
        ],
        tip: 'Cargalo el mismo día, desde el celular.',
      },
      {
        question: 'Cargar una cosecha',
        steps: [
          'Producción → Cargar cosecha.',
          'Lote, cantidad (cajones, kg…) y dónde se guarda.',
          'Si es la última, marcá "¿Es la cosecha final?" y el sistema ofrece cerrar el cultivo.',
        ],
      },
      {
        question: 'Ver todo lo que se hizo en un lote',
        steps: ['Producción → tocá el cultivo → Cuaderno.'],
      },
    ],
  },
  {
    id: 'stock',
    title: 'Stock y mezclas',
    topics: [
      {
        question: '¿Cuánto tengo de cada cosa?',
        steps: ['Inventario → Stock.', 'La campana de arriba avisa lo que hay que comprar.'],
      },
      {
        question: 'Cargar algo que entró o salió sin compra ni venta',
        steps: ['Inventario → Nuevo → Ingreso (o Egreso).', 'Almacén, productos y cantidades.'],
        tip: 'Las compras, ventas, labores y cosechas mueven el stock solas.',
      },
      {
        question: 'Preparar una mezcla',
        steps: [
          'Elaboración → Nueva preparación.',
          'Elegí la receta y cuánto vas a preparar.',
          'Si falta algo, el sistema te lo dice.',
        ],
      },
    ],
  },
  {
    id: 'plata',
    title: 'Compras, ventas y plata',
    topics: [
      {
        question: 'Cargar una compra',
        steps: [
          'Comercial y caja → Compras y gastos → Nueva compra.',
          'Proveedor y datos de la factura (o "sin factura").',
          'Productos, cantidades y precios sin IVA.',
          'Guardar: el stock se suma solo.',
        ],
      },
      {
        question: 'Cargar un gasto (gasoil, reparación, servicio…)',
        steps: [
          'Si hay factura: Compras y gastos → Nueva compra → Agregar gasto o servicio.',
          'Si se pagó en efectivo sin factura: Caja y bancos → Nuevo movimiento → Gasto.',
          'Elegí a qué corresponde: un lote, un cultivo o una máquina.',
        ],
        tip: 'Si no es de nada en particular (luz, seguros), dejalo sin destino.',
      },
      {
        question: 'Cargar una venta',
        steps: [
          'Comercial y caja → Ventas → Nueva venta.',
          'Cliente, productos, cantidades y precios.',
          'Guardar: el stock se descuenta solo.',
        ],
      },
      {
        question: 'Registrar que me pagaron (o que pagué)',
        steps: [
          'Comercial y caja → Cobros (o Pagos) → Nuevo.',
          'Cliente o proveedor, cuánto y en qué caja o banco.',
          'Tocá "Imputar a los más viejos" y guardá.',
        ],
      },
      {
        question: '¿Quién me debe? ¿A quién le debo?',
        steps: ['Comercial y caja → Cuentas corrientes.', 'Tocá un nombre para ver su detalle.'],
      },
      {
        question: '¿Cuánta plata hay en caja y en el banco?',
        steps: ['Comercial y caja → Caja y bancos.'],
      },
    ],
  },
  {
    id: 'maquinas',
    title: 'Máquinas',
    topics: [
      {
        question: 'Registrar un service o una reparación',
        steps: [
          'Activos → tocá la máquina → Registrar mantenimiento.',
          'Fecha, qué se hizo y los repuestos que se usaron.',
          'Si hubo factura del taller, cargala antes como compra y elegila acá.',
        ],
      },
      {
        question: 'Anotar las horas o los km',
        steps: ['Activos → tocá la máquina → Lecturas → Cargar lectura.'],
        tip: 'La llave de arriba avisa cuando se acerca un service.',
      },
    ],
  },
  {
    id: 'numeros',
    title: 'Números',
    topics: [
      {
        question: '¿Cuánto gané o perdí con un cultivo?',
        steps: [
          'Costos y rentabilidad → Rentabilidad.',
          'Tocá un cultivo para ver en qué se fue la plata.',
        ],
      },
      {
        question: '¿Cómo viene el negocio en general?',
        steps: [
          'Costos y rentabilidad → Resultado de gestión.',
          'También en la pantalla de inicio.',
        ],
      },
      {
        question: 'Sacar un listado en Excel o PDF',
        steps: [
          'Reportes → elegí el reporte.',
          'Elegí las fechas o la temporada.',
          'Tocá Excel o PDF.',
        ],
        tip: 'Para el contador: "Libro de compras / ventas".',
      },
    ],
  },
  {
    id: 'administrar',
    title: 'Administrar',
    topics: [
      {
        question: 'Crear un usuario',
        steps: ['Usuarios y roles → Nuevo usuario.', 'Nombre, usuario, contraseña y rol.'],
        tip: 'Un usuario por persona: así se sabe quién cargó cada cosa.',
      },
      {
        question: '¿Quién cambió esto?',
        steps: ['Botón Historial en cualquier registro, o el menú Historial.'],
      },
      {
        question: 'Cargar muchos datos desde Excel',
        steps: [
          'Importar datos → elegí qué importar → Descargar plantilla.',
          'Completala y subila → Revisar.',
          'Si no hay errores → Importar.',
        ],
      },
      {
        question: 'Me equivoqué en algo que ya guardé',
        steps: [
          'Abrilo y corregilo: el sistema pide confirmación.',
          'Si no tenía que existir: Anular (no se borra, queda anulado).',
        ],
      },
    ],
  },
];

const normalize = (text: string) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Secciones con las preguntas que contienen todas las palabras buscadas (sin tildes). */
export function searchManual(query: string): ManualSection[] {
  const words = normalize(query).split(/\s+/).filter(Boolean);
  if (words.length === 0) return MANUAL;
  return MANUAL.map((section) => ({
    ...section,
    topics: section.topics.filter((topic) => {
      const text = normalize(
        [section.title, topic.question, ...topic.steps, topic.tip ?? ''].join(' '),
      );
      return words.every((w) => text.includes(w));
    }),
  })).filter((section) => section.topics.length > 0);
}
