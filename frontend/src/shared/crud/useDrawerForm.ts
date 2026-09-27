import { useForm, type UseFormInput } from '@mantine/form';
import { useEffect } from 'react';

/**
 * Formulario de un panel de alta/edición: al abrirse carga los datos del registro
 * (o los valores vacíos si es un alta).
 */
export function useDrawerForm<T, V extends Record<string, unknown>>({
  opened,
  record,
  empty,
  toValues,
  validate,
}: {
  opened: boolean;
  record: T | null;
  empty: V;
  toValues: (record: T) => V;
  validate?: UseFormInput<V>['validate'];
}) {
  const form = useForm<V>({ initialValues: empty, validate });

  useEffect(() => {
    if (!opened) return;
    form.setValues(record ? toValues(record) : empty);
    form.resetDirty();
    form.clearErrors();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al abrir o cambiar de registro
  }, [opened, record]);

  return form;
}

/** Validación de campo obligatorio. */
export const required = (value: unknown) =>
  value === null || value === undefined || String(value).trim() === '' ? 'Obligatorio' : null;
