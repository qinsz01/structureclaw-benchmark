import { useMemo, useState } from 'react';
import { line } from 'd3-shape';
import type { Locale, Reference, Result } from './types';
import { memberResponses } from './member-response';
import type { Vec, Sample } from './member-response';
import { PaperFigure, SvgText } from './paper-figures';
import { formatNumber as f, downloadJson } from './data';

export function MemberView({
  reference,
  result,
  engine,
  caseName,
  locale,
}: {
  reference: Reference;
  result: Result;
  engine: string;
  caseName?: string;
  locale: Locale;
}) {
  const zh = locale === 'zh',
    rows = useMemo(() => memberResponses(reference, result, engine), [reference, result, engine]);
  const [id, setId] = useState(rows[0]?.id || ''),
    [scale, setScale] = useState(20),
    [metric, setMetric] = useState('uz');
  const selected = rows.find((r) => r.id === id) || rows[0],
    spatial = reference.model.coordinate_system.dimension === '3d';
  const names = {
    recovered: zh ? '荷载修正恢复' : 'Load-corrected recovery',
    interpolated: zh ? '端部运动插值' : 'End-kinematic interpolation',
    truss: zh ? '桁架轴力／直杆变形' : 'Truss axial force / straight-member deformation',
    unavailable: zh ? '数据不足' : 'Unavailable',
  };
  const reasons: Record<string, string> = {
    checked: zh
      ? '端部内力平衡、位移及转角一致性检查通过。'
      : 'End-force equilibrium and displacement/rotation consistency checks passed.',
    floor: zh
      ? '楼板传递荷载未完整归档；仅插值，未恢复内部真实挠度或内力。'
      : 'Expanded floor loads were not archived; interpolation only, not recovered interior displacement or forces.',
    axial: zh
      ? '桁架不恢复弯矩；轴力读取冻结值，杆件保持直线。旧桁架无单位元数据时按原 SI 求解契约使用 m、kN。'
      : 'No truss bending moments; axial force is frozen, members remain straight. Legacy SI truss records use the original m/kN solver contract.',
    consistency: zh
      ? '端部一致性未通过，降级为运动插值。'
      : 'Endpoint consistency failed; kinematic interpolation only.',
    loads: zh ? '单元荷载或组合信息不足。' : 'Incomplete member loads or combination.',
    stiffness: zh ? '材料或截面刚度不足。' : 'Missing material or section stiffness.',
    forces: zh ? '完整局部端力缺失。' : 'Complete local end forces unavailable.',
    engine: zh
      ? '此引擎尚无完整内部恢复契约。'
      : 'This engine has no supported interior recovery contract.',
    axes: zh ? '局部坐标信息不足。' : 'Local axes unavailable.',
    units: zh ? '单位不能确认。' : 'Units cannot be verified.',
    rotations: zh ? '端部转角缺失。' : 'End rotations unavailable.',
    displacements: zh ? '节点位移缺失。' : 'Nodal displacements unavailable.',
    element: zh ? '此单元类型不适用梁公式。' : 'Beam formulas do not apply to this element.',
    geometry: zh ? '几何信息不足。' : 'Geometry unavailable.',
  };
  const project = (p: Vec): [number, number] =>
    spatial ? [p[0] * 0.83 - p[1] * 0.62, -p[2] + p[0] * 0.28 + p[1] * 0.38] : [p[0], -p[2]];
  const all = rows.flatMap((r) =>
    r.samples.flatMap((p) => [
      project(p.position),
      project(p.position.map((v, i) => v + p.displacement[i] * scale) as Vec),
    ]),
  );
  const x0 = Math.min(...all.map((p) => p[0]), 0),
    x1 = Math.max(...all.map((p) => p[0]), 1),
    y0 = Math.min(...all.map((p) => p[1]), 0),
    y1 = Math.max(...all.map((p) => p[1]), 1);
  const factor = Math.min(840 / (x1 - x0 || 1), 320 / (y1 - y0 || 1));
  const screen = (p: Vec): [number, number] => {
    const v = project(p);
    return [500 + (v[0] - (x0 + x1) / 2) * factor, 280 + (v[1] - (y0 + y1) / 2) * factor];
  };
  const path = line<[number, number]>();
  const value = (p: Sample): number | undefined =>
    metric === 'ux'
      ? p.displacement[0]
      : metric === 'uy'
        ? p.displacement[1]
        : metric === 'uz'
          ? p.displacement[2]
          : metric === 'norm'
            ? Math.hypot(...p.displacement)
            : p[metric as 'N'];
  const unit = ['ux', 'uy', 'uz', 'norm'].includes(metric)
    ? 'm'
    : metric.startsWith('M') || metric === 'T'
      ? 'kN·m'
      : 'kN';
  const points = selected?.samples.filter((p) => value(p) !== undefined) || [];
  const max = Math.max(...points.map((p) => Math.abs(value(p)!)), 1e-20);
  const metrics = [
    'ux',
    'uy',
    'uz',
    'norm',
    ...(selected?.state === 'truss'
      ? ['N']
      : selected?.state === 'recovered'
        ? spatial
          ? ['N', 'V2', 'V3', 'M2', 'M3', 'T']
          : ['N', 'V2', 'M3']
        : []),
  ];
  return (
    <section className="member-view">
      <h2>{zh ? '单元内部响应 · 展示层' : 'Member interior response · Presentation layer'}</h2>
      <p>
        {zh
          ? '蓝色实线：已校核恢复；紫色虚线：仅端部位移／转角插值；桁架保持直杆。恢复值不参与评分，不替换冻结标答。'
          : 'Solid blue: checked recovery; dashed purple: end displacement/rotation interpolation only; trusses remain straight. Derived values never replace frozen references or affect scoring.'}
      </p>
      <div className="member-summary">
        {(['recovered', 'interpolated', 'truss', 'unavailable'] as const).map((s) => (
          <div key={s}>
            <span>{names[s]}</span>
            <strong>{rows.filter((r) => r.state === s).length}</strong>
          </div>
        ))}
      </div>
      <div className="lab-controls">
        <label>
          {zh ? '查看构件' : 'Inspect member'}
          <select
            value={selected?.id}
            onChange={(e) => {
              setId(e.target.value);
              setMetric('uz');
            }}
          >
            {rows.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id} · {names[r.state]}
              </option>
            ))}
          </select>
        </label>
        <label>
          {zh ? '曲线放大倍数' : 'Curve magnification'}
          <input
            type="number"
            min="0"
            max="10000"
            value={scale}
            onChange={(e) => setScale(Math.min(10000, Math.max(0, Number(e.target.value) || 0)))}
          />
        </label>
        <label>
          {zh ? '单元曲线分量' : 'Member curve component'}
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {metrics.map((k) => (
              <option key={k} value={k}>
                {k === 'norm' ? '|u|' : k}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() =>
            downloadJson(
              {
                schema: 'viewer-member-response-v1',
                reference: reference.id,
                engine,
                case: caseName,
                experimentalResult: false,
                rows,
              },
              `${reference.id}-derived-members.json`,
            )
          }
        >
          {zh ? '派生数据 JSON ↓' : 'Derived JSON ↓'}
        </button>
      </div>
      <p className="note">
        {selected?.id} · {selected ? names[selected.state] : ''} ·{' '}
        {selected ? reasons[selected.reason] : ''}
      </p>
      <PaperFigure
        title={zh ? '整体变形与单元内部曲线' : 'Overall deformation and member interior curve'}
        name={`${reference.id}-member-${selected?.id}-${metric}`}
        locale={locale}
        height={920}
      >
        <SvgText x={30} y={30} size={20} width={100} text={reference.id} />
        <text x="30" y="65" fontSize="14">
          {engine} · {caseName || '—'} · {zh ? '变形倍率' : 'Deformation scale'} ×{scale}
        </text>
        {rows
          .filter((r) => r.samples.length)
          .map((r) => (
            <g key={r.id}>
              <path
                d={path(r.samples.map((p) => screen(p.position))) || ''}
                fill="none"
                stroke="#c2cad5"
                strokeWidth="2"
              />
              <path
                d={
                  path(
                    r.samples.map((p) =>
                      screen(p.position.map((v, i) => v + p.displacement[i] * scale) as Vec),
                    ),
                  ) || ''
                }
                fill="none"
                stroke={
                  r.id === selected?.id
                    ? '#de852b'
                    : r.state === 'interpolated'
                      ? '#93498c'
                      : '#366bb6'
                }
                strokeWidth={r.id === selected?.id ? 3.5 : 2}
                strokeDasharray={r.state === 'interpolated' ? '6 4' : undefined}
              />
            </g>
          ))}
        <SvgText
          x={30}
          y={478}
          size={13}
          width={130}
          text={
            zh
              ? '灰：原形；蓝：荷载修正恢复／桁架直杆；紫色虚线：运动插值；橙：所选构件（保留虚实线状态）。'
              : 'Gray: original; blue: load-corrected / straight truss; purple dashed: kinematic interpolation; orange: selected (line style retained).'
          }
        />
        <text x="30" y="540" fontSize="16">
          {selected?.id} · {metric === 'norm' ? '|u|' : metric} [{unit}] ·{' '}
          {selected ? names[selected.state] : ''}
        </text>
        {points.length ? (
          <g>
            <line x1="140" y1="665" x2="940" y2="665" stroke="#b9c5d6" />
            <line x1="140" y1="570" x2="140" y2="760" stroke="#b9c5d6" />
            <path
              d={
                line<Sample>()
                  .x((p) => 140 + (800 * p.x) / selected.length)
                  .y((p) => 665 - (85 * value(p)!) / max)(points) || ''
              }
              fill="none"
              stroke={selected.state === 'interpolated' ? '#93498c' : '#366bb6'}
              strokeDasharray={selected.state === 'interpolated' ? '6 4' : undefined}
              strokeWidth="3"
            />
            <text x="25" y="586" fontSize="12">
              {f(max)}
            </text>
            <text x="25" y="751" fontSize="12">
              {f(-max)}
            </text>
            <text x="140" y="784" fontSize="12">
              0
            </text>
            <text x="820" y="784" fontSize="12">
              {f(selected.length)} m · n1 → n2
            </text>
          </g>
        ) : (
          <text x="30" y="630" fontSize="15">
            {zh
              ? '没有可用的内部曲线；请查阅原始节点／端力表。'
              : 'No interior curve available; see frozen node/end-force tables.'}
          </text>
        )}
        <SvgText
          x={30}
          y={822}
          width={130}
          size={12}
          text={`${selected ? reasons[selected.reason] : ''}\n${zh ? '位移分量为全局；N 为拉正。V2/M3 对应局部 y 弯曲；三维 V3/M2 对应另一平面。' : 'Displacements are global; N is tension-positive. V2/M3 use local-y bending; spatial V3/M2 use the other plane.'}\nSource: models/${reference.id}.json · viewer-member-response-v1 · ${zh ? '派生展示数据，非新实验结果' : 'Derived presentation data, not a new experimental result'}`}
        />
      </PaperFigure>
      <details>
        <summary>{zh ? '逐构件覆盖与限制' : 'Per-member coverage and limitations'}</summary>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>{zh ? '状态' : 'Status'}</th>
              <th>{zh ? '说明' : 'Reason'}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{names[r.state]}</td>
                <td>{reasons[r.reason]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}
