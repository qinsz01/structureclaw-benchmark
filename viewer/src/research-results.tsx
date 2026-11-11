import { useEffect, useMemo, useRef, useState } from 'react';
import type { Locale, Model } from './types';
import type {
  ResearchDerived,
  ResearchQuantity,
  ResearchSelection,
  ResearchDeformationField,
} from './research-types';
import { formatNumber, downloadJson } from './data';
import {
  automaticDeformationScale,
  embedPngMetadata,
  selectDeformationField,
  deformationEvidence,
  discreteDeformation,
  exactJson,
  exactNumber,
  layoutResponseMarkers,
  memberAxisEvidence,
  projectPoint,
  responseColor,
  responseSeries,
  sameSelection,
  selectionKey,
} from './research-response';
import type { ProjectionView } from './research-response';
import { supportKind } from './scene-loads';
import { publicReferenceForDownload } from './public-reference';

const locationLabel = (q: ResearchQuantity) =>
  q.location.kind === 'node'
    ? q.location.id
    : `${q.location.id}@${q.location.positionM} m:${q.location.side}`;
const safeName = (name: string) => name.replace(/[^\p{L}\p{N}_.-]+/gu, '-');
function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob),
    a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function saveFigure(svg: SVGSVGElement, name: string, png: boolean, metadata: unknown) {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  clone.setAttribute('width', '960');
  clone.setAttribute('height', '640');
  const embedded = clone.querySelector('metadata');
  if (embedded) embedded.textContent = exactJson(metadata);
  const payload = new XMLSerializer().serializeToString(clone);
  const blob = new Blob([payload], { type: 'image/svg+xml;charset=utf-8' });
  if (!png) {
    saveBlob(blob, `${name}.svg`);
    return;
  }
  const url = URL.createObjectURL(blob);
  try {
    const image = new Image();
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(Error('Image export failed'));
      image.src = url;
    });
    const canvas = document.createElement('canvas');
    canvas.width = 2880;
    canvas.height = 1920;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw Error('Canvas unavailable');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const pngBlob = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (value) => (value ? resolve(value) : reject(Error('PNG export failed'))),
        'image/png',
      ),
    );
    const exactPng = embedPngMetadata(new Uint8Array(await pngBlob.arrayBuffer()), metadata);
    saveBlob(new Blob([exactPng], { type: 'image/png' }), `${name}.png`);
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function ResearchResults({
  model,
  quantities,
  derived,
  locale,
  caseId,
  state,
  engine,
  turnId,
  sourceHash,
  referenceSource,
  deformationFields,
  modelSha256,
  maintainerMode = false,
}: {
  model: Model;
  quantities: ResearchQuantity[];
  deformationFields: ResearchDeformationField[];
  modelSha256: string;
  derived: ResearchDerived[];
  locale: Locale;
  caseId: string;
  state: number;
  engine: string;
  turnId?: string;
  sourceHash?: string;
  referenceSource?: { source: string; sha256: string; kind: string };
  maintainerMode?: boolean;
}) {
  const zh = locale === 'zh';
  const selections = useMemo(
    () => [...new Map(quantities.map((q) => [selectionKey(q.selection), q.selection])).values()],
    [quantities],
  );
  const [selectionValue, setSelectionValue] = useState(''),
    [componentValue, setComponentValue] = useState('');
  const selection: ResearchSelection | undefined =
    selections.find((s) => selectionKey(s) === selectionValue) || selections[0];
  const components = useMemo(
    () => [
      ...new Set(
        quantities
          .filter((q) => selection && sameSelection(q.selection, selection))
          .map((q) => q.component),
      ),
    ],
    [quantities, selection],
  );
  const component = components.includes(componentValue) ? componentValue : components[0] || '';
  const [view, setView] = useState<ProjectionView>(
    model.coordinate_system.dimension === '3d'
      ? 'iso'
      : (model.coordinate_system.plane as ProjectionView) || 'xz',
  );
  const [labels, setLabels] = useState(false),
    [deformation, setDeformation] = useState(false),
    [manualScale, setManualScale] = useState<number | null>(null);
  const [selected, setSelected] = useState<string | null>(null),
    [error, setError] = useState('');
  const svgRef = useRef<SVGSVGElement>(null),
    tableRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    setSelected(null);
    setError('');
  }, [caseId, state, turnId]);
  const series = useMemo(
    () =>
      selection
        ? responseSeries(model, quantities, selection, component, true)
        : { points: [], unavailable: [], unit: '', maxAbsolute: 0 },
    [model, quantities, selection, component],
  );
  const field = selection
    ? selectDeformationField(deformationFields, {
        caseId,
        state,
        engine,
        sourceHash,
        modelSha256,
        selection,
      })
    : undefined;
  const fieldQuantities = field?.quantities || [];
  const automatic = selection
    ? automaticDeformationScale(model, fieldQuantities, selection, view)
    : { scale: 1, allZero: true, projectionHidden: false };
  const scale = manualScale ?? automatic.scale;
  useEffect(() => {
    setManualScale(null);
  }, [caseId, state, turnId, selection?.kind, selection?.id]);
  const deformed = selection
    ? discreteDeformation(model, fieldQuantities, selection, scale)
    : { nodes: [], elements: [], missingNodeIds: model.nodes.map((n) => n.id) };
  const displayNodes = deformation ? [...model.nodes, ...deformed.nodes] : model.nodes;
  const projected = displayNodes.map((n) => projectPoint([n.x, n.y, n.z], view));
  const xs = projected.map((p) => p[0]),
    ys = projected.map((p) => p[1]);
  const minX = Math.min(...xs),
    maxX = Math.max(...xs),
    minY = Math.min(...ys),
    maxY = Math.max(...ys);
  const fit = Math.min(720 / Math.max(maxX - minX, 0.1), 350 / Math.max(maxY - minY, 0.1));
  const point = (xyz: [number, number, number]) => {
    const [x, y] = projectPoint(xyz, view);
    return [430 + (x - (minX + maxX) / 2) * fit, 252 + (y - (minY + maxY) / 2) * fit];
  };
  const pointsById = new Map(model.nodes.map((n) => [n.id, point([n.x, n.y, n.z])]));
  const deformedById = new Map(deformed.nodes.map((n) => [n.id, point([n.x, n.y, n.z])]));
  const chosen = quantities.find(
    (q) => q.id === selected && (!selection || sameSelection(q.selection, selection)),
  );
  const context = `${caseId} · ${turnId || ''} · ${zh ? '状态' : 'State'} ${state} · ${engine} · ${selection ? selectionKey(selection) : ''}`;
  const markers = layoutResponseMarkers(series.points, point);
  const memberAxes = [
    ...new Set(
      series.points
        .filter((p) => p.quantity.location.kind === 'member')
        .map((p) => p.quantity.location.id),
    ),
  ]
    .map((id) => memberAxisEvidence(model, id))
    .filter((v) => v !== null);
  const activeAxes = memberAxes.find((a) => a.id === chosen?.location.id) || memberAxes[0];
  const axes = {
    coordinateSystem: model.coordinate_system,
    convention:
      'Node components: global XYZ, Z up. Member local 1 follows i to j; 2/3 use the frozen reference vector and section roll. Basis rows map local axes into global XYZ. M2/M3 act about local 2/3; station side preserves signed limiting cuts.',
    members: memberAxes,
  };
  const metadata = {
    schemaVersion: 1,
    kind: 'research300-discrete-reference-visualization',
    caseId,
    turnId,
    state,
    targetEngine: engine,
    selection,
    component,
    unit: series.unit,
    sourceHash,
    referenceSource,
    axes,
    deformation:
      deformation && selection && field
        ? {
            ...deformationEvidence(model, fieldQuantities, selection, scale),
            field,
            magnification: manualScale === null ? 'automatic' : 'manual',
            allZero: automatic.allZero,
            projectionHidden: automatic.projectionHidden,
          }
        : null,
    projection: view,
    quantities: series.points.map((p) => p.quantity),
  };
  const axisLabel = (axis: number) =>
    activeAxes?.basisGlobal?.[axis].map((v) => formatNumber(v)).join(', ') || 'unavailable';
  const filename = safeName(
    `${caseId}-${turnId || 'reference'}-s${state}-${selection ? selectionKey(selection) : 'none'}-${component}`,
  );
  async function exportImage(png: boolean) {
    if (!svgRef.current) return;
    try {
      setError('');
      await saveFigure(
        svgRef.current,
        filename,
        png,
        maintainerMode ? metadata : publicReferenceForDownload(metadata),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }
  const pick = (q: ResearchQuantity) => {
    setSelected(q.id);
    if (tableRef.current) tableRef.current.open = true;
  };
  return (
    <section className="research-results" aria-label={zh ? '参考结果' : 'Reference results'}>
      <div className="section-heading">
        <h3>{zh ? '参考值与结果图' : 'Reference values & response diagram'}</h3>
        <span>
          {quantities.length} {zh ? '项数值' : 'quantities'} · {derived.length}{' '}
          {zh ? '项汇总' : 'derived'}
        </span>
      </div>
      <p className="note">
        {zh
          ? '数值按当前轮要求的单位显示。图中仅标绘已有参考值的位置；构件分量使用题定局部轴和截面侧，节点分量使用全局轴。'
          : 'Values use the units requested on this turn. The diagram marks recorded locations only; member components use the specified local axes and station side, node components use global axes.'}
      </p>
      {selection && (
        <>
          <div className="research-result-controls">
            <label>
              {zh ? '工况 / 组合' : 'Case / combination'}
              <select
                aria-label={zh ? '结果工况或组合' : 'Result case or combination'}
                value={selectionKey(selection)}
                onChange={(e) => {
                  setSelectionValue(e.target.value);
                  setSelected(null);
                }}
              >
                {selections.map((s) => (
                  <option key={selectionKey(s)} value={selectionKey(s)}>
                    {selectionKey(s)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {zh ? '分量' : 'Component'}
              <select
                aria-label={zh ? '结果分量' : 'Result component'}
                value={component}
                onChange={(e) => {
                  setComponentValue(e.target.value);
                  setSelected(null);
                }}
              >
                {components.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              {zh ? '投影' : 'Projection'}
              <select
                aria-label={zh ? '结果投影' : 'Result projection'}
                value={view}
                onChange={(e) => setView(e.target.value as ProjectionView)}
              >
                {['xy', 'xz', 'yz', 'iso'].map((v) => (
                  <option key={v} value={v}>
                    {v.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <input
                type="checkbox"
                checked={labels}
                onChange={(e) => setLabels(e.target.checked)}
              />
              {zh ? '标注数值' : 'Value labels'}
            </label>
            <label>
              <input
                type="checkbox"
                checked={deformation}
                onChange={(e) => setDeformation(e.target.checked)}
                disabled={!deformed.nodes.length}
              />
              {zh ? '离散节点变形' : 'Discrete NODE deformation'}
            </label>
            {deformation && (
              <label>
                {zh ? '倍率' : 'Scale'}
                <input
                  aria-label={zh ? '变形倍率' : 'Deformation scale'}
                  type="number"
                  min="0"
                  step="any"
                  value={scale}
                  onChange={(e) => {
                    const next = e.target.valueAsNumber;
                    if (Number.isFinite(next) && next >= 0) setManualScale(next);
                  }}
                />
              </label>
            )}
            {deformation && (
              <button onClick={() => setManualScale(null)}>{zh ? '自动倍率' : 'Auto scale'}</button>
            )}
          </div>
          {maintainerMode && field && (
            <p className="note research-deformation-coverage">
              {zh ? '原生节点位移覆盖' : 'Native node displacement coverage'}:{' '}
              {field.coverage.completeNodes}/{field.coverage.totalNodes} {zh ? '节点' : 'nodes'} ·{' '}
              {field.coverage.completeElements}/{field.coverage.totalElements}{' '}
              {zh ? '构件' : 'members'} · {field.coverage.nativeComponents}{' '}
              {zh ? '原生分量' : 'native components'} · {field.coverage.constraintComponents}{' '}
              {zh ? '明确约束零值' : 'explicit constraint zeros'}.{' '}
              {zh
                ? '位移场来自当前物理状态和所选工况；评分数值仍按当前轮请求显示。'
                : 'The field uses this physical state and selection; scoring rows follow the current turn request.'}
            </p>
          )}
          {deformation && automatic.allZero && (
            <p className="note">
              {zh
                ? '完整记录的位移为零；变形与原轮廓重合。'
                : 'Recorded translations are all zero; the deformed and original outlines coincide.'}
            </p>
          )}
          {deformation && automatic.projectionHidden && (
            <p className="note">
              {zh
                ? '当前投影中位移不可见；切换投影查看其他方向。'
                : 'Displacement is hidden in this projection; select another projection to see its direction.'}
            </p>
          )}
          <div className="research-response-figure">
            <svg
              ref={svgRef}
              viewBox="0 0 960 640"
              role="img"
              aria-label={
                zh ? `${component} 离散参考结果图` : `${component} discrete reference diagram`
              }
              fontFamily="Arial, Microsoft YaHei, sans-serif"
              fontSize="12"
            >
              <title>{`${context} · ${component} [${series.unit}]`}</title>
              <desc>
                {zh
                  ? '离散冻结参考值；未记录的值不填零；杆件连线仅表示几何。'
                  : 'Discrete frozen reference values; missing values are not zero; member lines indicate geometry only.'}
              </desc>
              <metadata>{exactJson(metadata)}</metadata>
              <rect width="960" height="640" fill="white" />
              <text x="32" y="29" fill="#20304a" fontSize="16" fontWeight="700">
                {context}
              </text>
              <text x="32" y="51" fill="#52647b">
                {component} · {series.unit} · {view.toUpperCase()} ·{' '}
                {zh ? '离散参考值' : 'Discrete reference values'}
              </text>
              <g
                className="research-undeformed-outline"
                stroke="#a7b5c8"
                strokeWidth="2"
                fill="none"
              >
                {model.elements.map((e) => {
                  const a = pointsById.get(e.nodes[0]),
                    b = pointsById.get(e.nodes[1]);
                  return a && b ? (
                    <line key={e.id} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} />
                  ) : null;
                })}
              </g>
              {model.nodes.map((n) => {
                const p = pointsById.get(n.id)!;
                const support = supportKind(model, n);
                return (
                  <g key={n.id}>
                    <circle cx={p[0]} cy={p[1]} r="2.5" fill="#a7b5c8" />
                    {support && (
                      <g
                        className="research-support"
                        data-node-id={n.id}
                        data-support={support}
                        fill="#d7e0ed"
                        stroke="#6d819b"
                      >
                        <title>{`${n.id} · ${support} · ${n.restraints?.join(', ')}`}</title>
                        {support === 'fixed' ? (
                          <path
                            d={`M${p[0]},${p[1]}v6m-7,0h14m-12,0l-3,4m8,-4l-3,4m8,-4l-3,4`}
                            fill="none"
                          />
                        ) : support === 'rotation' || support === 'partial' ? (
                          <circle cx={p[0]} cy={p[1]} r="6" fill="none" />
                        ) : (
                          <>
                            <path
                              d={`M${p[0] - 5},${p[1] + 9}L${p[0]},${p[1] + 2}L${p[0] + 5},${p[1] + 9}Z`}
                            />
                            {support === 'roller' && (
                              <>
                                <circle cx={p[0] - 3} cy={p[1] + 12} r="1.5" />
                                <circle cx={p[0] + 3} cy={p[1] + 12} r="1.5" />
                              </>
                            )}
                          </>
                        )}
                      </g>
                    )}
                  </g>
                );
              })}
              {deformation && (
                <g stroke="#7650b6" strokeWidth="2" strokeDasharray="5 4" fill="none">
                  {deformed.elements.map((e) => {
                    const a = deformedById.get(e.nodes[0])!,
                      b = deformedById.get(e.nodes[1])!;
                    return (
                      <line
                        className="research-deformed-member"
                        key={e.id}
                        x1={a[0]}
                        y1={a[1]}
                        x2={b[0]}
                        y2={b[1]}
                      />
                    );
                  })}
                  {deformed.nodes.map((n) => {
                    const p = deformedById.get(n.id)!;
                    const original = pointsById.get(n.id)!;
                    return (
                      <circle
                        className="research-deformed-node"
                        data-node-id={n.id}
                        data-displaced={Math.hypot(p[0] - original[0], p[1] - original[1]) > 0.1}
                        key={n.id}
                        cx={p[0]}
                        cy={p[1]}
                        r="3.5"
                        fill="#7650b6"
                      >
                        <title>{`${n.id} · NODE · ×${scale}`}</title>
                      </circle>
                    );
                  })}
                </g>
              )}
              {markers.map(({ point: p, anchor, position }, i) => (
                <g
                  className="research-response-marker"
                  data-quantity-id={p.quantity.id}
                  key={`${p.quantity.id}:${i}`}
                  onClick={() => pick(p.quantity)}
                  style={{ cursor: 'pointer' }}
                >
                  {(anchor[0] !== position[0] || anchor[1] !== position[1]) && (
                    <line
                      x1={anchor[0]}
                      y1={anchor[1]}
                      x2={position[0]}
                      y2={position[1]}
                      stroke="#7b8799"
                    />
                  )}
                  <circle
                    cx={position[0]}
                    cy={position[1]}
                    r={selected === p.quantity.id ? 7 : 5.5}
                    stroke={selected === p.quantity.id ? '#0f172a' : '#59677a'}
                    strokeWidth={selected === p.quantity.id ? 2.5 : 1}
                    fill={responseColor(p.value, series.maxAbsolute)}
                  >
                    <title>{`${p.quantity.id}\n${locationLabel(p.quantity)}\n${exactNumber(p.quantity.value)} ${p.quantity.unit}\n${p.quantity.location.kind === 'member' ? exactJson(memberAxes.find((a) => a.id === p.quantity.location.id)) : 'Global XYZ components'}`}</title>
                  </circle>
                  {labels && (
                    <text x={position[0] + 8} y={position[1] - 10} fill="#20304a" fontSize="11">
                      {formatNumber(p.value)}
                    </text>
                  )}
                </g>
              ))}
              {Array.from({ length: 40 }, (_, i) => (
                <rect
                  key={i}
                  x="865"
                  y={110 + i * 6}
                  width="16"
                  height="6.1"
                  fill={responseColor(series.maxAbsolute * (1 - (i / 39) * 2), series.maxAbsolute)}
                />
              ))}
              <text x="890" y="119" fill="#34445a">
                {formatNumber(series.maxAbsolute)}
              </text>
              <text x="890" y="234" fill="#34445a">
                0
              </text>
              <text x="890" y="352" fill="#34445a">
                {formatNumber(-series.maxAbsolute)}
              </text>
              <text
                x="32"
                y="466"
                fill="#52647b"
              >{`${series.points.length} ${zh ? '个参考采样值；灰色几何不表示零响应。' : 'recorded samples; gray geometry does not mean zero response.'}`}</text>
              <text x="32" y="487" fill="#52647b">
                {deformation
                  ? `${zh ? '完整三分量位移节点' : 'Discrete NODE translations'}: ${deformed.nodes.length}/${model.nodes.length} · ×${scale} · ${zh ? '直线仅连接已记录节点' : 'straight segments join recorded nodes only'}`
                  : zh
                    ? '构件站点沿节点1至节点2按米定位；左右侧值分别保留。'
                    : 'Member stations follow node 1 to node 2 in metres; left/right values stay distinct.'}
              </text>
              <text x="32" y="510" fill="#52647b">
                {zh
                  ? '节点：全局XYZ；构件：1轴沿i→j，M2/M3绕局部2/3轴。标记引线仅区分重合采样点。'
                  : 'Nodes: global XYZ. Members: local 1 along i→j; M2/M3 about local 2/3. Leaders separate coincident samples.'}
              </text>
              {activeAxes && (
                <g fill="#52647b" fontSize="11" className="research-visible-axes">
                  <text
                    x="32"
                    y="531"
                  >{`${activeAxes.id} · ${activeAxes.nodeIds.join(' → ')} · roll ${activeAxes.rotationDegrees}° · local axes in global XYZ (rounded display):`}</text>
                  <text
                    x="32"
                    y="551"
                  >{`1 = [${axisLabel(0)}]   2 = [${axisLabel(1)}]   3 = [${axisLabel(2)}]`}</text>
                  <text x="32" y="571">
                    {zh
                      ? '点击采样点查看该构件局部轴；SVG/JSON保留全部构件的精确轴、站点、侧与参考值。'
                      : 'Click a sample for its member axes; SVG/JSON retain every exact basis, station, side and reference value.'}
                  </text>
                </g>
              )}
              {maintainerMode && (
                <text x="32" y="599" fill="#52647b" fontSize="10">
                  {referenceSource
                    ? `${referenceSource.kind} · SHA-256 ${referenceSource.sha256}`
                    : 'research-300 · current-turn frozen scoring quantities'}
                </text>
              )}
              <text x="32" y="623" fill="#52647b" fontSize="10">
                StructureClaw Benchmark · {zh ? '参考结果' : 'Reference results'}
              </text>
            </svg>
          </div>
          {series.unavailable.length > 0 && (
            <p className="note" role="status">
              {zh
                ? '以下数据无法定位或单位不兼容，未绘制：'
                : 'Unavailable locations or incompatible units; not plotted: '}
              {series.unavailable.join(', ')}
            </p>
          )}
          {!deformed.nodes.length && (
            <p className="note">
              {zh
                ? '当前状态和工况没有可核验的完整三分量节点位移。'
                : 'No verified complete node displacement vector is available for this state and selection.'}
            </p>
          )}
          {maintainerMode && field && (
            <details className="research-deformation-source">
              <summary>
                {zh ? '节点位移场来源与覆盖' : 'Node displacement field sources & coverage'}
              </summary>
              <p>
                {engine} · {field.receipt.runId}
              </p>
              {field.sources.map((source) => (
                <p key={source.source}>
                  <code>{source.source}</code>
                  <br />
                  <code>SHA-256 {source.sha256}</code>
                </p>
              ))}
              <p>
                {zh
                  ? '离散节点与直线连接；不提供无证据的梁内光滑插值。'
                  : 'Discrete nodes and straight connecting segments; no smooth beam interpolation is supplied.'}
              </p>
              {!!field.coverage.missingNodeIds.length && (
                <p>
                  {zh ? '缺少完整位移的节点' : 'Nodes missing complete translations'}:{' '}
                  {field.coverage.missingNodeIds.join(', ')}
                </p>
              )}
            </details>
          )}
          <div className="research-export-actions">
            <button onClick={() => exportImage(false)}>
              {zh ? '导出结果 SVG' : 'Export response SVG'}
            </button>
            <button onClick={() => exportImage(true)}>
              {zh ? '导出结果 PNG' : 'Export response PNG'}
            </button>
            <button
              onClick={() =>
                downloadJson(
                  maintainerMode
                    ? {
                        ...metadata,
                        quantities: series.points.map((p) => p.quantity),
                        unavailable: series.unavailable,
                      }
                    : publicReferenceForDownload(metadata),
                  `${filename}.json`,
                )
              }
            >
              {zh ? '导出图中数据 JSON' : 'Export plotted data JSON'}
            </button>
          </div>
          {error && <p role="alert">{error}</p>}
        </>
      )}
      <details ref={tableRef} className="research-quantity-details">
        <summary>
          {zh ? '精确数值' : 'Exact quantities'} · {quantities.length}
        </summary>
        {maintainerMode && (
          <p className="note">
            {zh
              ? '表内显示原始完整数值，容差属于评分规则；工程诊断余量不改变默认通过条件。'
              : 'The table preserves full numeric values. Tolerances are scoring rules; engineering diagnostic allowances do not change the default pass condition.'}
          </p>
        )}
        <div className="research-table-scroll">
          <table className="research-quantity-table">
            <thead>
              <tr>
                {[
                  ...(maintainerMode ? ['ID'] : []),
                  ...(zh
                    ? ['工况 / 组合', '位置', '分量', '参考值', '单位']
                    : ['Case / combination', 'Location', 'Component', 'Reference value', 'Unit']),
                  ...(maintainerMode
                    ? [zh ? '绝对 / 相对容差' : 'Absolute / relative tolerance']
                    : []),
                ].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {quantities.map((q, i) => (
                <tr
                  key={`${selectionKey(q.selection)}:${q.id}:${i}`}
                  data-quantity-id={q.id}
                  className={selected === q.id ? 'selected' : ''}
                  onClick={() => {
                    setSelectionValue(selectionKey(q.selection));
                    setComponentValue(q.component);
                    setSelected(q.id);
                  }}
                >
                  {maintainerMode && (
                    <td>
                      <code>{q.id}</code>
                    </td>
                  )}
                  <td>{selectionKey(q.selection)}</td>
                  <td>{locationLabel(q)}</td>
                  <td>{q.component}</td>
                  <td data-value={exactNumber(q.value)} title={exactNumber(q.value)}>
                    {exactNumber(q.value)}
                  </td>
                  <td data-unit={q.unit}>{q.unit}</td>
                  {maintainerMode && (
                    <td>
                      {q.tolerance.absolute} / {q.tolerance.relative}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button
          onClick={() =>
            downloadJson(
              maintainerMode
                ? { ...metadata, quantities, derived }
                : publicReferenceForDownload({ ...metadata, quantities, derived }),
              `${safeName(`${caseId}-${turnId || ''}-s${state}`)}-reference-values.json`,
            )
          }
        >
          {zh ? '下载本轮完整参考 JSON' : 'Download complete turn reference JSON'}
        </button>
        {maintainerMode && chosen && (
          <details className="research-quantity-provenance">
            <summary>
              {zh ? '所选值的原始记录' : 'Selected quantity provenance'} · {chosen.id}
            </summary>
            <pre>{exactJson(chosen, 2)}</pre>
          </details>
        )}
      </details>
      {derived.length > 0 && (
        <details className="research-derived-details">
          <summary>
            {zh ? '汇总与控制值' : 'Derived and governing values'} · {derived.length}
          </summary>
          <div className="research-table-scroll">
            <table>
              <thead>
                <tr>
                  {[
                    ...(maintainerMode ? ['ID'] : []),
                    ...(zh
                      ? ['运算', '值', '单位', '控制对象', '工况 / 组合']
                      : ['Operation', 'Value', 'Unit', 'Governing operand', 'Case / combination']),
                  ].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {derived.map((d) => (
                  <tr key={d.id} data-derived-id={d.id}>
                    {maintainerMode && (
                      <td>
                        <code>{d.id}</code>
                      </td>
                    )}
                    <td>{d.operation}</td>
                    <td data-value={exactNumber(d.value)}>{exactNumber(d.value)}</td>
                    <td data-unit={d.unit}>{d.unit}</td>
                    <td>{d.governingOperand || '—'}</td>
                    <td>{d.governingSelection ? selectionKey(d.governingSelection) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {maintainerMode && <pre>{exactJson(derived, 2)}</pre>}
        </details>
      )}
      {!quantities.length && !derived.length && (
        <p className="note">
          {zh ? '本轮没有要求数值输出。' : 'No numerical output is requested on this turn.'}
        </p>
      )}
    </section>
  );
}
