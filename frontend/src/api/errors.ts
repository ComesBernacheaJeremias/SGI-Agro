/** Errores de la API con el formato único del backend: { error: { code, message, details } }. */

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type ErrorBody = { error?: { code?: string; message?: string; details?: Record<string, unknown> } };

const FALLBACK_MESSAGE = 'No se pudo completar la operación. Intentá de nuevo.';

export function toApiError(body: unknown, status: number): ApiError {
  const error = (body as ErrorBody | undefined)?.error;
  return new ApiError(
    error?.message ?? FALLBACK_MESSAGE,
    error?.code ?? 'UNKNOWN',
    status,
    error?.details,
  );
}

/** Devuelve `data` de una respuesta de openapi-fetch, o lanza ApiError. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || result.data === undefined) {
    throw toApiError(result.error, result.response.status);
  }
  return result.data;
}

/** Error de validación del formulario (se muestra tal cual al usuario). */
export class FormError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'FormError';
  }
}

/** Mensaje para mostrar al usuario a partir de cualquier error. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof FormError) return error.message;
  if (error instanceof TypeError) return 'No hay conexión con el servidor.';
  return FALLBACK_MESSAGE;
}
