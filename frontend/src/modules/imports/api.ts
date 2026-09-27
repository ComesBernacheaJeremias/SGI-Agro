/** Importación desde Excel: catálogo, plantilla, vista previa y confirmación. */
import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';
import { saveFile } from '@/api/download';
import { unwrap } from '@/api/errors';
import type { components } from '@/api/schema';

type S = components['schemas'];

export type ImportInfo = S['ImportInfo'];
export type ImportResult = S['ImportResult'];

export function useImports() {
  return useQuery({
    queryKey: ['imports'],
    queryFn: async () => unwrap(await api.GET('/api/v1/imports')),
    staleTime: Infinity,
  });
}

export async function downloadTemplate(key: string) {
  const result = await api.GET('/api/v1/imports/{key}/template', {
    params: { path: { key } },
    parseAs: 'blob',
  });
  saveFile(result, `plantilla-${key}.xlsx`);
}

/** El archivo va como multipart/form-data (campo `file`). */
const asForm = (body: { file: unknown }) => {
  const form = new FormData();
  form.append('file', body.file as Blob);
  return form;
};

export async function previewImport(key: string, file: File): Promise<ImportResult> {
  return unwrap(
    await api.POST('/api/v1/imports/{key}/preview', {
      params: { path: { key } },
      body: { file: file as unknown as string },
      bodySerializer: asForm,
    }),
  );
}

export async function confirmImport(key: string, file: File): Promise<ImportResult> {
  return unwrap(
    await api.POST('/api/v1/imports/{key}', {
      params: { path: { key } },
      body: { file: file as unknown as string },
      bodySerializer: asForm,
    }),
  );
}
