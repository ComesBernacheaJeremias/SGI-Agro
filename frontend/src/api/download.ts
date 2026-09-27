/** Descarga de archivos generados por la API (Excel, PDF) con la sesión del usuario. */
import { toApiError } from './errors';

type BlobResult = { data?: unknown; error?: unknown; response: Response };

/** Guarda el archivo de una respuesta `parseAs: 'blob'` con el nombre que manda el servidor. */
export function saveFile(result: BlobResult, fallbackName: string): void {
  if (result.error !== undefined || !result.data) {
    throw toApiError(result.error, result.response.status);
  }
  const disposition = result.response.headers.get('content-disposition') ?? '';
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? fallbackName;
  const url = URL.createObjectURL(result.data as Blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
