import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/api/errors';

import { submitOrQueue } from './submit';

const add = vi.fn();
vi.mock('./outbox', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./outbox')>()),
  outbox: { add: (...args: unknown[]) => add(...args) },
}));
vi.mock('@mantine/notifications', () => ({ notifications: { show: vi.fn() } }));

const base = { kind: 'field_operation' as const, path: '/api/v1/field-operations', label: 'Labor' };

function setOnline(value: boolean) {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true });
}

describe('submitOrQueue', () => {
  beforeEach(() => {
    add.mockReset();
    setOnline(true);
  });

  it('con conexión envía con un id generado en el dispositivo', async () => {
    const send = vi.fn().mockResolvedValue({ ok: true });
    const result = await submitOrQueue({ ...base, body: { date: '2026-09-27' }, send });
    expect(result).toEqual({ queued: false, data: { ok: true } });
    expect(send.mock.calls[0]?.[0]).toMatchObject({ date: '2026-09-27', id: expect.any(String) });
    expect(add).not.toHaveBeenCalled();
  });

  it('sin conexión guarda en la cola', async () => {
    setOnline(false);
    const send = vi.fn();
    const result = await submitOrQueue({ ...base, body: { id: 'abc' }, send });
    expect(result).toEqual({ queued: true });
    expect(send).not.toHaveBeenCalled();
    expect(add).toHaveBeenCalledWith(expect.objectContaining({ id: 'abc', path: base.path }));
  });

  it('si la red falla al enviar, también queda en la cola', async () => {
    const send = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    expect(await submitOrQueue({ ...base, body: {}, send })).toEqual({ queued: true });
    expect(add).toHaveBeenCalledOnce();
  });

  it('un error de la API (regla de negocio) no se encola', async () => {
    const send = vi.fn().mockRejectedValue(new ApiError('Stock insuficiente', 'STOCK', 409));
    await expect(submitOrQueue({ ...base, body: {}, send })).rejects.toThrow('Stock insuficiente');
    expect(add).not.toHaveBeenCalled();
  });
});
