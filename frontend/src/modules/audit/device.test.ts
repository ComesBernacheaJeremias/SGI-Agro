import { describe, expect, it } from 'vitest';

import { describeDevice } from './device';

describe('describeDevice', () => {
  it('navegador y sistema', () => {
    const windows =
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';
    const android =
      'Mozilla/5.0 (Linux; Android 14; SM-A146M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36';
    const iphone =
      'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
    expect(describeDevice(windows)).toBe('Chrome · Windows');
    expect(describeDevice(android)).toBe('Chrome · Android');
    expect(describeDevice(iphone)).toBe('Safari · iPhone/iPad');
  });

  it('sin datos o desconocido', () => {
    expect(describeDevice(null)).toBe('—');
    expect(describeDevice('curl/8.0')).toBe('Otro');
  });
});
