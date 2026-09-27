/** CUIT: se guarda con 11 dígitos y se muestra 20-12345678-9. */
export function formatCuit(value: string | null | undefined): string {
  const digits = (value ?? '').replace(/\D/g, '');
  return digits.length === 11
    ? `${digits.slice(0, 2)}-${digits.slice(2, 10)}-${digits.slice(10)}`
    : (value ?? '');
}
