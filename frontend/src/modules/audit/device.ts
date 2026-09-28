/** Resume el "user agent" del navegador para mostrarlo: "Chrome · Android". */

const BROWSERS: [RegExp, string][] = [
  [/Edg\//, 'Edge'],
  [/OPR\//, 'Opera'],
  [/SamsungBrowser\//, 'Samsung Internet'],
  [/Firefox\/|FxiOS\//, 'Firefox'],
  [/Chrome\/|CriOS\//, 'Chrome'],
  [/Safari\//, 'Safari'],
];

const SYSTEMS: [RegExp, string][] = [
  [/Android/, 'Android'],
  [/iPhone|iPad|iPod/, 'iPhone/iPad'],
  [/Windows/, 'Windows'],
  [/Mac OS X|Macintosh/, 'Mac'],
  [/Linux/, 'Linux'],
];

const first = (list: [RegExp, string][], text: string) =>
  list.find(([pattern]) => pattern.test(text))?.[1];

export function describeDevice(userAgent: string | null | undefined): string {
  if (!userAgent) return '—';
  const parts = [first(BROWSERS, userAgent), first(SYSTEMS, userAgent)].filter(Boolean);
  return parts.length ? parts.join(' · ') : 'Otro';
}
