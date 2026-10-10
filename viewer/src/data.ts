const base = new URL('./data/', document.baseURI).href;
export const dataUrl = (path: string) => base + path;
const cache = new Map<string, Promise<unknown>>();
export function fetchData<T>(path: string): Promise<T> {
  if (!cache.has(path))
    cache.set(
      path,
      fetch(dataUrl(path))
        .then((r) => {
          if (!r.ok) throw new Error(String(r.status));
          return r.json();
        })
        .catch((e) => {
          cache.delete(path);
          throw e;
        }),
    );
  return cache.get(path) as Promise<T>;
}
export function downloadJson(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const formatNumber = (n: number) =>
  n === 0
    ? '0'
    : Math.abs(n) < 0.0001 || Math.abs(n) >= 1e6
      ? n.toExponential(4)
      : Number(n.toPrecision(6)).toString();
