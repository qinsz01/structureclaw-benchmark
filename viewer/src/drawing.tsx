import { useEffect, useRef, useState } from 'react';
import { fetchData } from './data';
import type { Locale } from './types';

type Entity = {
  type: string;
  layer: string;
  start: number[];
  end: number[];
  radius: number;
  height: number;
  angle: number;
  endAngle: number;
  text: string;
  align: number;
  verticalAlign: number;
};
type Drawing = { entities: Entity[]; layers: string[]; unsupported: string[] };
const pointList = (e: Entity): number[][] => {
  if (e.type === 'LINE') return [e.start, e.end];
  if (e.type === 'TEXT') {
    const p = e.align || e.verticalAlign ? e.end : e.start;
    const width = e.text.length * e.height * 0.7;
    return [
      [p[0] - width, p[1] - e.height],
      [p[0] + width, p[1] + e.height],
    ];
  }
  return [
    [e.start[0] - e.radius, e.start[1] - e.radius],
    [e.start[0] + e.radius, e.start[1] + e.radius],
  ];
};
export default function DrawingPreview({ path, locale }: { path: string; locale: Locale }) {
  const [drawing, setDrawing] = useState<Drawing>();
  const [error, setError] = useState(false),
    [hidden, setHidden] = useState<string[]>([]);
  const [zoom, setZoom] = useState(1),
    [pan, setPan] = useState([0, 0]);
  const [expanded, setExpanded] = useState(false);
  const [layerMenu, setLayerMenu] = useState(false);
  const drag = useRef<{ x: number; y: number; pan: number[] } | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const z = locale === 'zh';
  useEffect(() => {
    let active = true;
    fetchData<Drawing>(`${path}.json`).then(
      (d) => {
        if (active) setDrawing(d);
      },
      () => {
        if (active) setError(true);
      },
    );
    return () => {
      active = false;
    };
  }, [path]);
  useEffect(() => {
    if (!expanded) return;
    const listener = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpanded(false);
    };
    document.addEventListener('keydown', listener);
    const before = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    container.current?.focus();
    return () => {
      document.removeEventListener('keydown', listener);
      document.body.style.overflow = before;
    };
  }, [expanded]);
  if (!drawing)
    return (
      <p role="status" className="note">
        {error
          ? z
            ? '图纸预览加载失败，请下载原文件。'
            : 'Preview unavailable; download the original drawing.'
          : z
            ? '正在读取图纸…'
            : 'Loading drawing…'}
      </p>
    );
  const points = drawing.entities.flatMap(pointList),
    xs = points.map((p) => p[0]),
    ys = points.map((p) => -p[1]);
  const minX = Math.min(...xs),
    minY = Math.min(...ys),
    width = Math.max(Math.max(...xs) - minX, 1),
    height = Math.max(Math.max(...ys) - minY, 1),
    pad = Math.max(width, height) * 0.05;
  const w = width + pad * 2,
    h = height + pad * 2;
  const vx = minX - pad + (w * (1 - 1 / zoom)) / 2 + pan[0],
    vy = minY - pad + (h * (1 - 1 / zoom)) / 2 + pan[1];
  return (
    <div
      className={`drawing-preview ${expanded ? 'expanded-drawing' : ''}`}
      ref={container}
      tabIndex={-1}
      role={expanded ? 'dialog' : undefined}
      aria-modal={expanded || undefined}
      aria-label={z ? 'DXF 图纸预览' : 'DXF drawing preview'}
    >
      <div className="drawing-toolbar">
        <span>DXF · XY</span>
        <button
          onClick={() => setZoom(Math.min(12, zoom * 1.3))}
          aria-label={z ? '放大图纸' : 'Zoom in drawing'}
        >
          ＋
        </button>
        <button
          onClick={() => setZoom(Math.max(0.5, zoom / 1.3))}
          aria-label={z ? '缩小图纸' : 'Zoom out drawing'}
        >
          −
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan([0, 0]);
          }}
        >
          {z ? '适配' : 'Fit'}
        </button>
        <button aria-expanded={layerMenu} onClick={() => setLayerMenu(!layerMenu)}>
          {z ? '图层' : 'Layers'}
        </button>
        <button onClick={() => setExpanded(!expanded)}>
          {expanded ? (z ? '关闭' : 'Close') : z ? '放大查看' : 'Expand'}
        </button>
      </div>
      {layerMenu && (
        <div className="drawing-layers">
          {drawing.layers.map((layer) => (
            <label key={layer}>
              <input
                type="checkbox"
                checked={!hidden.includes(layer)}
                onChange={() =>
                  setHidden(
                    hidden.includes(layer) ? hidden.filter((v) => v !== layer) : [...hidden, layer],
                  )
                }
              />
              {layer}
            </label>
          ))}
        </div>
      )}
      <svg
        className="dxf-svg"
        xmlns="http://www.w3.org/2000/svg"
        viewBox={`${vx} ${vy} ${w / zoom} ${h / zoom}`}
        data-source={path}
        data-fit={`${minX - pad} ${minY - pad} ${w} ${h}`}
        role="img"
        aria-label={z ? '原始 DXF 图纸，XY 投影' : 'Original DXF drawing, XY projection'}
        style={{ background: 'white', touchAction: 'none' }}
        onWheel={(e) =>
          setZoom((v) => Math.min(12, Math.max(0.5, v * (e.deltaY < 0 ? 1.12 : 0.89))))
        }
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          drag.current = { x: e.clientX, y: e.clientY, pan };
        }}
        onPointerMove={(e) => {
          if (!drag.current) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const scale = Math.max(w / zoom / rect.width, h / zoom / rect.height);
          setPan([
            drag.current.pan[0] - (e.clientX - drag.current.x) * scale,
            drag.current.pan[1] - (e.clientY - drag.current.y) * scale,
          ]);
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        {drawing.entities
          .filter((e) => !hidden.includes(e.layer))
          .map((e, i) => {
            const color = /dim|text|anno/i.test(e.layer)
              ? '#738198'
              : /axis|grid/i.test(e.layer)
                ? '#b8c3d3'
                : '#355b89';
            const stroke = {
              stroke: color,
              strokeWidth: 1.3,
              vectorEffect: 'non-scaling-stroke' as const,
              fill: 'none',
            };
            if (e.type === 'LINE')
              return (
                <line
                  key={i}
                  x1={e.start[0]}
                  y1={-e.start[1]}
                  x2={e.end[0]}
                  y2={-e.end[1]}
                  {...stroke}
                />
              );
            if (e.type === 'CIRCLE')
              return <circle key={i} cx={e.start[0]} cy={-e.start[1]} r={e.radius} {...stroke} />;
            if (e.type === 'ARC') {
              const sweep = (e.endAngle - e.angle + 360) % 360;
              const pts = Array.from({ length: Math.max(3, Math.ceil(sweep / 3)) + 1 }, (_, j) => {
                const angle =
                  ((e.angle + (sweep * j) / Math.max(3, Math.ceil(sweep / 3))) * Math.PI) / 180;
                return `${e.start[0] + e.radius * Math.cos(angle)},${-e.start[1] - e.radius * Math.sin(angle)}`;
              });
              return <polyline key={i} points={pts.join(' ')} {...stroke} />;
            }
            const p = e.align || e.verticalAlign ? e.end : e.start;
            return (
              <text
                key={i}
                x={p[0]}
                y={-p[1]}
                fontSize={e.height}
                fontFamily="Arial, Microsoft YaHei, sans-serif"
                fill={color}
                textAnchor={e.align === 1 ? 'middle' : e.align === 2 ? 'end' : 'start'}
                dominantBaseline={
                  e.verticalAlign === 3 ? 'hanging' : e.verticalAlign === 2 ? 'central' : 'auto'
                }
                transform={`rotate(${-e.angle} ${p[0]} ${-p[1]})`}
              >
                {e.text}
              </text>
            );
          })}
      </svg>
      <div className="drawing-note">
        {z
          ? '原始图纸 · 拖动平移，滚轮缩放；不自动匹配参考构件。'
          : 'Original drawing · Drag to pan, scroll to zoom. No automatic member mapping.'}
        {drawing.unsupported.length > 0 && (
          <strong>
            {z ? ' 未显示实体：' : ' Entities not shown: '}
            {drawing.unsupported.join(', ')}
          </strong>
        )}
      </div>
    </div>
  );
}
