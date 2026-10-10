import type { Geometry } from './types';
export function Thumbnail({
  model,
  decorative = true,
}: {
  model?: Geometry;
  decorative?: boolean;
}) {
  if (!model)
    return (
      <svg viewBox="0 0 360 180" aria-hidden="true">
        <g fill="none" stroke="currentColor" strokeWidth="1.6" opacity=".55">
          <rect x="129" y="42" width="102" height="85" rx="10" />
          <path d="M150 64h59M150 80h44M150 96h30M155 127l-7 17 30-17" />
          <circle cx="240" cy="49" r="16" fill="#f4f7fc" />
          <path d="M235 49h10m-5-5v10" />
        </g>
      </svg>
    );
  const spatial = model.coordinate_system.dimension === '3d';
  const plane = model.coordinate_system.plane || 'xz';
  const projected = model.nodes.map((n) => ({
    id: n.id,
    restraints: n.restraints,
    x: spatial ? n.x * 0.83 - n.y * 0.62 : plane === 'yz' ? n.y : n.x,
    y: spatial ? -n.z + n.x * 0.28 + n.y * 0.38 : -(plane === 'xy' ? n.y : n.z),
  }));
  const minX = Math.min(...projected.map((n) => n.x)),
    maxX = Math.max(...projected.map((n) => n.x));
  const minY = Math.min(...projected.map((n) => n.y)),
    maxY = Math.max(...projected.map((n) => n.y));
  const scale = Math.min(252 / Math.max(maxX - minX, 1), 110 / Math.max(maxY - minY, 1));
  const points = Object.fromEntries(
    projected.map((n) => [
      n.id,
      {
        ...n,
        px: 180 + (n.x - (minX + maxX) / 2) * scale,
        py: 86 + (n.y - (minY + maxY) / 2) * scale,
      },
    ]),
  );
  return (
    <svg
      viewBox="0 0 360 180"
      role={decorative ? undefined : 'img'}
      aria-label={decorative ? undefined : 'Reference geometry'}
      aria-hidden={decorative || undefined}
    >
      <g stroke="#e0e8f3" strokeWidth="1">
        <path d="M35 147h290M70 32v125M125 32v125M180 32v125M235 32v125M290 32v125" opacity=".65" />
      </g>
      {model.elements.map((e) => {
        const a = points[e.nodes[0]],
          b = points[e.nodes[1]];
        return (
          a &&
          b && (
            <line
              key={e.id}
              x1={a.px}
              y1={a.py}
              x2={b.px}
              y2={b.py}
              stroke="#3661ad"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          )
        );
      })}
      {Object.values(points).map((n) => (
        <g key={n.id}>
          {n.restraints?.some(Boolean) &&
            (n.restraints.every(Boolean) ? (
              <g stroke="#7186a7" strokeWidth="1">
                <path d={`M${n.px - 7} ${n.py + 5}h14m-12 0l-3 4m8-4l-3 4m8-4l-3 4`} />
                <path d={`M${n.px} ${n.py}v5`} />
              </g>
            ) : (
              <g>
                <path
                  d={`M${n.px} ${n.py + 3}l-5 8h10z`}
                  fill="#bdcce2"
                  stroke="#7186a7"
                  strokeWidth="1"
                />
                {n.restraints.slice(0, 3).some((r) => !r) && (
                  <g fill="#7186a7">
                    <circle cx={n.px - 3} cy={n.py + 13} r="1.3" />
                    <circle cx={n.px + 3} cy={n.py + 13} r="1.3" />
                  </g>
                )}
              </g>
            ))}
          <circle cx={n.px} cy={n.py} r="2.7" fill="white" stroke="#2358df" strokeWidth="1.4" />
        </g>
      ))}
    </svg>
  );
}
