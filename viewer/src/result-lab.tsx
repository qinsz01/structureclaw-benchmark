import { useState } from 'react';
import type { Assertion, Locale, Reference, Result } from './types';
import { beamCheck, memberMoment, referenceResult, resultUnit } from './reference-math';
import type { Pick } from './reference-math';
import { formatNumber as f } from './data';
import { PaperFigure, SvgText } from './paper-figures';

function ResultPlot({
  reference,
  result,
  caseName,
  engine,
  locale,
  pick,
  onPick,
}: {
  reference: Reference;
  result: Result;
  caseName?: string;
  engine: string;
  locale: Locale;
  pick: Pick | null;
  onPick: (pick: Pick) => void;
}) {
  const zh = locale === 'zh',
    m = reference.model;
  const [mode, setMode] = useState('uz'),
    [deformed, setDeformed] = useState(false),
    [scale, setScale] = useState(10);
  const displacementUnit = resultUnit(result, 'displacements', 'uz');
  const canDeform = displacementUnit === 'm' && m.unit_system === 'SI';
  const unit = mode === 'moment' ? resultUnit(result, 'forces', 'M') : displacementUnit;
  const metric =
    mode === 'moment'
      ? zh
        ? '端弯矩 |M| 最大值'
        : 'Largest end |M|'
      : mode === 'norm'
        ? '|u|'
        : mode;
  const values: Record<string, number> = {};
  if (mode === 'moment')
    for (const e of m.elements) {
      const v = memberMoment(result.forces?.[e.id]);
      if (v !== undefined) values[e.id] = v;
    }
  else
    for (const n of m.nodes) {
      const d = result.displacements?.[n.id];
      const v =
        mode === 'norm' && d && ['ux', 'uy', 'uz'].every((k) => typeof d[k] === 'number')
          ? Math.hypot(d.ux, d.uy, d.uz)
          : d?.[mode];
      if (typeof v === 'number' && Number.isFinite(v)) values[n.id] = v;
    }
  const range = Object.values(values),
    min = range.length ? Math.min(...range) : 0,
    max = range.length ? Math.max(...range) : 0;
  const color = (value?: number) =>
    value === undefined
      ? '#a6afbc'
      : `hsl(${225 - 195 * (max === min ? 0.5 : (value - min) / (max - min))} 67% 45%)`;
  const spatial = m.coordinate_system.dimension === '3d',
    plane = m.coordinate_system.plane;
  const project = (n: { x: number; y: number; z: number }) =>
    spatial
      ? { x: 0.83 * n.x - 0.62 * n.y, y: -n.z + 0.28 * n.x + 0.38 * n.y }
      : { x: plane === 'yz' ? n.y : n.x, y: -(plane === 'xy' ? n.y : n.z) };
  const points = Object.fromEntries(m.nodes.map((n) => [n.id, project(n)]));
  const displaced = Object.fromEntries(
    m.nodes.flatMap((n) => {
      const d = result.displacements?.[n.id];
      return d && ['ux', 'uy', 'uz'].every((k) => typeof d[k] === 'number' && Number.isFinite(d[k]))
        ? [[n.id, project({ x: n.x + scale * d.ux, y: n.y + scale * d.uy, z: n.z + scale * d.uz })]]
        : [];
    }),
  );
  const all = [
    ...Object.values(points),
    ...(deformed && canDeform ? Object.values(displaced) : []),
  ];
  const x0 = Math.min(...all.map((p) => p.x)),
    x1 = Math.max(...all.map((p) => p.x)),
    y0 = Math.min(...all.map((p) => p.y)),
    y1 = Math.max(...all.map((p) => p.y));
  const s = Math.min(790 / Math.max(x1 - x0, 1), 285 / Math.max(y1 - y0, 1));
  const X = (x: number) => 500 + (x - (x0 + x1) / 2) * s,
    Y = (y: number) => 265 + (y - (y0 + y1) / 2) * s;
  const selectedNode =
    pick?.kind === 'node' ? m.nodes.find((n) => n.id === pick.entity) : undefined;
  const selectedMember =
    pick?.kind === 'member' ? m.elements.find((e) => e.id === pick.entity) : undefined;
  const located = selectedNode
    ? points[selectedNode.id]
    : selectedMember
      ? points[selectedMember.nodes[0]]
      : undefined;
  return (
    <>
      <div className="lab-controls">
        <label>
          {zh ? '着色指标' : 'Color metric'}
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="uz">uz</option>
            <option value="ux">ux</option>
            <option value="uy">uy</option>
            <option value="norm">|u|</option>
            <option value="moment">{zh ? '构件端弯矩 |M|' : 'Member end |M|'}</option>
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={deformed}
            disabled={!canDeform}
            onChange={(e) => setDeformed(e.target.checked)}
          />
          {zh ? '叠加节点变形' : 'Overlay nodal deformation'}
        </label>
        <label>
          {zh ? '变形倍率' : 'Deformation scale'}
          <input
            type="number"
            min="0"
            max="10000"
            step="1"
            value={scale}
            onChange={(e) => setScale(Math.max(0, Math.min(10000, Number(e.target.value) || 0)))}
          />
        </label>
      </div>
      <PaperFigure
        title={zh ? '结果定位与变形示意' : 'Result locations and deformation schematic'}
        name={`${reference.id}-results-${mode}`}
        locale={locale}
        height={630}
      >
        <SvgText x={30} y={35} text={reference.id} size={20} width={100} />
        <text x="30" y="72" fontSize="14">
          {engine} · {caseName || '—'} · {metric} [{unit}]
        </text>
        {m.elements.map((e) => {
          const a = points[e.nodes[0]],
            b = points[e.nodes[1]];
          if (!a || !b) return null;
          const active = pick?.kind === 'member' && pick.entity === e.id;
          const select = () => {
            if (values[e.id] !== undefined && mode === 'moment')
              onPick({
                entity: e.id,
                kind: 'member',
                component: 'max(|n1.M|, |n2.M|)',
                value: values[e.id],
                unit,
              });
          };
          return (
            <g key={e.id}>
              <line
                x1={X(a.x)}
                y1={Y(a.y)}
                x2={X(b.x)}
                y2={Y(b.y)}
                stroke={active ? '#e07820' : mode === 'moment' ? color(values[e.id]) : '#a8b7c9'}
                strokeWidth={active ? 7 : 4}
              />
              {mode === 'moment' && values[e.id] !== undefined && (
                <rect
                  x={X(a.x)}
                  y={Y(a.y) - 9}
                  width={Math.hypot(X(b.x) - X(a.x), Y(b.y) - Y(a.y))}
                  height="18"
                  transform={`rotate(${(Math.atan2(Y(b.y) - Y(a.y), X(b.x) - X(a.x)) * 180) / Math.PI} ${X(a.x)} ${Y(a.y)})`}
                  fill="transparent"
                  role="button"
                  tabIndex={0}
                  aria-label={`${e.id} M`}
                  onClick={select}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      select();
                    }
                  }}
                >
                  <title>
                    {e.id}: {f(values[e.id])} {unit}
                  </title>
                </rect>
              )}
            </g>
          );
        })}
        {deformed &&
          canDeform &&
          m.elements.map((e) => {
            const a = displaced[e.nodes[0]],
              b = displaced[e.nodes[1]];
            return a && b ? (
              <line
                key={e.id}
                x1={X(a.x)}
                y1={Y(a.y)}
                x2={X(b.x)}
                y2={Y(b.y)}
                stroke="#993d88"
                strokeWidth="2.5"
                strokeDasharray="7 4"
              />
            ) : null;
          })}
        {m.nodes.map((n) => {
          const p = points[n.id],
            v = values[n.id],
            active = pick?.kind === 'node' && pick.entity === n.id;
          const select = () => {
            if (v !== undefined && mode !== 'moment')
              onPick({ entity: n.id, kind: 'node', component: mode, value: v, unit });
          };
          return (
            <g key={n.id}>
              {n.restraints?.some(Boolean) && (
                <path
                  d={`M${X(p.x) - 8} ${Y(p.y) + 14}h16M${X(p.x)} ${Y(p.y) + 6}v8`}
                  stroke="#52647a"
                  strokeWidth="2"
                />
              )}
              <circle
                cx={X(p.x)}
                cy={Y(p.y)}
                r={active ? 8 : 5}
                fill={active ? '#e07820' : mode === 'moment' ? '#52647a' : color(v)}
                stroke="white"
                strokeWidth="1.5"
              />
              {mode !== 'moment' && v !== undefined && (
                <circle
                  cx={X(p.x)}
                  cy={Y(p.y)}
                  r="13"
                  fill="transparent"
                  role="button"
                  tabIndex={0}
                  aria-label={`${n.id} ${mode}`}
                  onClick={select}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      select();
                    }
                  }}
                >
                  <title>
                    {n.id}: {f(v)} {unit}
                  </title>
                </circle>
              )}
            </g>
          );
        })}
        {located && pick && (
          <g>
            <line
              x1={X(located.x)}
              y1={Y(located.y)}
              x2="60"
              y2="448"
              stroke="#e07820"
              strokeDasharray="3 3"
            />
            <text x="30" y="467" fontSize="15" fill="#aa4e16">
              {pick.kind === 'node' ? (zh ? '节点' : 'Node') : zh ? '构件' : 'Member'} {pick.entity}{' '}
              · {pick.component} = {f(pick.value)} {pick.unit} · {caseName || '—'}
            </text>
          </g>
        )}
        <text x="30" y="500" fontSize="12">
          {range.length
            ? `${f(min)} → ${f(max)} ${unit}`
            : zh
              ? '该指标无可用数据'
              : 'No data for this metric'}
        </text>
        {Array.from({ length: 20 }, (_, i) => (
          <rect
            key={i}
            x={290 + i * 14}
            y="487"
            width="14"
            height="13"
            fill={color(min + ((max - min) * i) / 19)}
          />
        ))}
        <text x="590" y="500" fontSize="12">
          {zh ? '灰色：无该指标；橙色：选中' : 'Gray: unavailable; orange: selected'}
        </text>
        <SvgText
          x={30}
          y={530}
          width={130}
          size={12}
          text={`${zh ? '离散节点／构件端值，不是连续应力云图。节点为全局分量；端弯矩为原始局部分量 M。' : 'Discrete node / member-end values, not a continuous stress field. Nodal components are global; end M is the stored local component.'}\n${deformed && canDeform ? (zh ? `变形 ×${scale}；仅连接已有完整节点位移，直线连线不表示单元内部挠曲。` : `Deformation ×${scale}; straight segments connect complete nodal data, not within-element curvature.`) : zh ? '显示原始几何；支座短线仅表示存在约束，详细自由度见模型。' : 'Original geometry; support ticks indicate restraint presence; see model for DOFs.'}\nSource: models/${reference.id}.json · ${engine} · ${caseName || '—'}`}
        />
      </PaperFigure>
    </>
  );
}

export function ResultLab({
  reference,
  assertions,
  engineTarget,
  locale,
  pick,
  onPick,
}: {
  reference: Reference;
  assertions: Assertion[];
  engineTarget?: string;
  locale: Locale;
  pick: Pick | null;
  onPick: (pick: Pick) => void;
}) {
  const zh = locale === 'zh',
    selected = referenceResult(reference, assertions, engineTarget);
  const check = selected.engine === 'opensees' && selected.result ? beamCheck(reference) : null;
  const archived =
    selected.engine === 'opensees' && selected.result
      ? (
          reference.numerical as unknown as {
            verification?: {
              equilibrium?: {
                pass: boolean;
                forceResidual: number[];
                momentResidual: number[];
                limits: { force: number; moment: number };
              }[];
            };
          }
        )?.verification
      : undefined;
  if (!selected.result) return null;
  const names = {
    deflection: zh ? '控制位置竖向位移' : 'Vertical displacement at control location',
    left: zh ? '左支座竖向反力' : 'Left vertical reaction',
    right: zh ? '右支座竖向反力' : 'Right vertical reaction',
  };
  return (
    <section className="result-lab">
      <div className="section-kicker">REFERENCE LAB</div>
      <h2>{zh ? '参考结果与计算校核' : 'Reference results and calculation checks'}</h2>
      <p className="muted">
        {zh
          ? '点击数值表或图中节点／构件定位。所选分量、全局最大值与任务要求分别展示；辅助计算不会修改标答或评分。'
          : 'Click numerical cells or plotted entities to locate values. Selected components, global extrema and task requirements are distinct; auxiliary calculations do not change references or scoring.'}
      </p>
      <ResultPlot
        reference={reference}
        result={selected.result}
        caseName={selected.caseName}
        engine={selected.engine}
        locale={locale}
        pick={pick}
        onPick={onPick}
      />
      <details className="calculation-panel">
        <summary>
          {zh ? '辅助解析计算与校核' : 'Auxiliary analytical calculations and checks'}
        </summary>
        {!check ? (
          <p>
            {zh
              ? '当前模型或工况不满足本工具的解析条件。支持：等截面水平 XZ 梁、全跨均布荷载简支梁，或端点集中力悬臂梁；其余模型只展示冻结数值与已有校核证据。'
              : 'This model or case is outside the analytical scope: prismatic horizontal XZ beams with full-span uniform loading and simple supports, or a cantilever with a tip load. Other models show frozen results and available archived verification.'}
          </p>
        ) : (
          <>
            <p>
              {zh
                ? '假设：Euler–Bernoulli 线弹性小变形、等截面、不计剪切变形。竖向 +Z 向上，q/P 为向下荷载；M 正值为正弯矩，V = dM/dx。解析曲线不是对节点数据插值。'
                : 'Assumptions: Euler–Bernoulli linear elasticity, small deformation, constant section, no shear deformation. +Z is upward; q/P is downward. M is positive sagging, V = dM/dx. Curves are analytical, not interpolated nodal results.'}
            </p>
            <p className="formula">
              L = {f(check.L)} m · E = {f(check.E / 1000)} MPa × 1000 = {f(check.E)} kN/m² · Iᵧ ={' '}
              {f(check.I)} m⁴ · {check.family === 'uniform' ? 'q' : 'P'} = {f(check.load)}{' '}
              {check.family === 'uniform' ? 'kN/m' : 'kN'}
            </p>
            <p className="muted small">
              {zh
                ? 'E 换算沿用仓库 opensees_static_analysis.py 的材料约定；荷载按冻结 analysisSelection.factors 合成。比较保留位移正负号，误差按解析值绝对值归一化；解析值为零时仅使用绝对误差。'
                : 'E conversion follows the material convention in opensees_static_analysis.py; loads use frozen analysisSelection.factors. Comparisons retain displacement signs; relative error uses the absolute analytical value. At zero, only absolute error is used.'}
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {[
                      zh ? '位置与公式' : 'Location and formula',
                      zh ? '解析值' : 'Analytical',
                      zh ? '冻结标答' : 'Frozen reference',
                      zh ? '绝对误差' : 'Absolute error',
                      zh ? '相对误差' : 'Relative error',
                    ].map((t) => (
                      <th key={t}>{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {check.checks.map((c) => (
                    <tr key={c.label}>
                      <td>
                        {names[c.label]} · {c.node}
                        <br />
                        <code>{c.formula}</code>
                        <br />
                        <code>= {c.substitution}</code>
                      </td>
                      <td>
                        {f(c.expected)} {c.unit}
                      </td>
                      <td>{c.actual === undefined ? '—' : `${f(c.actual)} ${c.unit}`}</td>
                      <td>
                        {c.actual === undefined
                          ? '—'
                          : `${f(Math.abs(c.actual - c.expected))} ${c.unit}`}
                      </td>
                      <td>
                        {c.actual === undefined || c.expected === 0
                          ? '—'
                          : `${(Math.abs((c.actual - c.expected) / c.expected) * 100).toExponential(3)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              ΣFz = ΣRz − {check.family === 'uniform' ? 'qL' : 'P'} ={' '}
              {check.forceResidual === undefined ? '—' : f(check.forceResidual)} kN ·{' '}
              {zh
                ? '由当前展示数据重新计算，不作为评分断言。'
                : 'Recomputed from displayed data; not a scoring assertion.'}
            </p>
            <p>
              ΣMy ({zh ? '左端点' : 'left endpoint'}) ={' '}
              {check.family === 'uniform' ? '−L·Rz(L) + qL²/2' : 'My(0) + PL'} ={' '}
              {check.momentResidual === undefined ? '—' : f(check.momentResidual)} kN·m
            </p>
            <PaperFigure
              title={
                zh ? '解析曲线与冻结位移核验' : 'Analytical curves and frozen displacement checks'
              }
              name={`${reference.id}-calculation`}
              locale={locale}
              height={870}
            >
              <text x="35" y="36" fontSize="21" fontWeight="bold">
                {reference.id} · {selected.caseName}
              </text>
              <text x="35" y="65" fontSize="13">
                L={f(check.L)} m · E={f(check.E)} kN/m² · Iᵧ={f(check.I)} m⁴ ·{' '}
                {check.family === 'uniform' ? 'q' : 'P'}={f(check.load)}{' '}
                {check.family === 'uniform' ? 'kN/m' : 'kN'}
              </text>
              {(['displacement', 'moment', 'shear'] as const).map((k, i) => {
                const top = 100 + i * 200,
                  extent = Math.max(...check.samples.map((p) => Math.abs(p[k])), 1e-20),
                  x = (v: number) => 110 + (v / check.L) * 820,
                  y = (v: number) => top + 88 - (v / extent) * 65;
                const poly = check.samples.map((p) => `${x(p.x)},${y(p[k])}`).join(' ');
                const titles = { displacement: 'u_z [m]', moment: 'M [kN·m]', shear: 'V [kN]' };
                return (
                  <g key={k}>
                    <text x="35" y={top + 15} fontSize="15">
                      {titles[k]}
                    </text>
                    <line x1="110" y1={y(0)} x2="930" y2={y(0)} stroke="#a8b7c9" />
                    <line x1="110" y1={top + 23} x2="110" y2={top + 155} stroke="#a8b7c9" />
                    <text x="20" y={y(extent) + 4} fontSize="12">
                      {f(extent)}
                    </text>
                    <text x="20" y={y(-extent) + 4} fontSize="12">
                      {f(-extent)}
                    </text>
                    <polyline points={poly} fill="none" stroke="#3561b0" strokeWidth="3" />
                    {k === 'displacement' &&
                      reference.model.nodes.map((n) => {
                        const v = selected.result!.displacements?.[n.id]?.uz;
                        return typeof v === 'number' ? (
                          <circle
                            key={n.id}
                            cx={x(n.x - Math.min(...reference.model.nodes.map((p) => p.x)))}
                            cy={y(v)}
                            r="5"
                            fill="#dc812b"
                          >
                            <title>
                              {n.id}: {v}
                            </title>
                          </circle>
                        ) : null;
                      })}
                    {[0, check.L / 2, check.L].map((v) => (
                      <text key={v} x={x(v)} y={top + 177} textAnchor="middle" fontSize="12">
                        {f(v)}
                      </text>
                    ))}
                    <text x="940" y={top + 177} fontSize="12">
                      x [m]
                    </text>
                  </g>
                );
              })}
              <SvgText
                x={35}
                y={725}
                size={13}
                width={125}
                text={`${zh ? '蓝线：Euler–Bernoulli 解析解；橙点：冻结节点位移。内力曲线使用正弯矩约定，不能直接等同于局部端力符号。' : 'Blue: Euler–Bernoulli analytical solution; orange: frozen nodal displacements. Analytical moments use sagging-positive signs, distinct from local end-force conventions.'}\n${check.checks.map((c) => `${c.formula} = ${f(c.expected)} ${c.unit}; ${zh ? '标答' : 'reference'} = ${c.actual === undefined ? '—' : f(c.actual)}`).join('\n')}\nSource: models/${reference.id}.json / ${selected.engine} / ${selected.caseName}`}
              />
            </PaperFigure>
          </>
        )}
        {archived && (
          <div className="archived-checks">
            <h3>{zh ? '冻结文件中的校核记录' : 'Archived verification in the frozen file'}</h3>
            <p className="muted">
              {zh
                ? '以下为已有记录，不是本次重新运行求解器。残差、容差和通过状态均读取原文件。'
                : 'These are archived records, not a solver run in this session. Residuals, tolerances and statuses come from the original file.'}
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>ΣF [kN]</th>
                    <th>ΣM [kN·m]</th>
                    <th>{zh ? '容差 F / M' : 'Tolerance F / M'}</th>
                    <th>{zh ? '归档状态' : 'Archived status'}</th>
                  </tr>
                </thead>
                <tbody>
                  {archived.equilibrium?.map((e, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{e.forceResidual.map(f).join(', ')}</td>
                      <td>{e.momentResidual.map(f).join(', ')}</td>
                      <td>
                        {f(e.limits.force)} / {f(e.limits.moment)}
                      </td>
                      <td>{e.pass ? (zh ? '通过' : 'Passed') : zh ? '未通过' : 'Failed'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details>
              <summary>{zh ? '完整校核来源 JSON' : 'Full verification source JSON'}</summary>
              <pre>{JSON.stringify(archived, null, 2)}</pre>
            </details>
          </div>
        )}
      </details>
    </section>
  );
}
