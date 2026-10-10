export function readViewState() {
  return new URLSearchParams(location.hash.split('?')[1] || '');
}
export function saveViewState(values: Record<string, string | number | null>) {
  const params = readViewState();
  for (const [key, value] of Object.entries(values)) {
    if (value === null) params.delete(key);
    else params.set(key, String(value));
  }
  history.replaceState(
    null,
    '',
    `${location.hash.split('?')[0]}${params.size ? '?' + params : ''}`,
  );
}
export function initialIndex(key: string, length: number) {
  const n = Number(readViewState().get(key) || 0);
  return Number.isInteger(n) && n >= 0 && n < length ? n : 0;
}
