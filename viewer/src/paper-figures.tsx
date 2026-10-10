import { useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { Assertion, CaseDetail, Geometry, Index, Locale, Reference } from './types';
import { referenceResult, resultUnit } from './reference-math';
import { formatNumber } from './data';
import { Thumbnail } from './thumbnail';
import { assertionNames, familyNames, label } from './i18n';

export function lines(text: string, limit = 64) {
  const output: string[] = [];
  let row = '',
    width = 0;
  for (const c of text) {
    const w = c.charCodeAt(0) > 255 ? 2 : 1;
    if (c === '\n' || width + w > limit) {
      const space = c !== '\n' ? row.lastIndexOf(' ') : -1;
      const split = space > row.length / 2 ? space : row.length;
      output.push(row.slice(0, split));
      row = row.slice(split).trimStart();
      width = [...row].reduce((n, ch) => n + (ch.charCodeAt(0) > 255 ? 2 : 1), 0);
    }
    if (c !== '\n') {
      row += c;
      width += w;
    }
  }
  if (row) output.push(row);
  return output;
}
export function SvgText({
  text,
  x,
  y,
  width = 64,
  size = 15,
  color = '#52647a',
}: {
  text: string;
  x: number;
  y: number;
  width?: number;
  size?: number;
  color?: string;
}) {
  return (
    <text x={x} y={y} fontSize={size} fill={color}>
      {lines(text, width).map((s, i) => (
        <tspan key={i} x={x} dy={i ? size * 1.5 : 0}>
          {s}
        </tspan>
      ))}
    </text>
  );
}
export function PaperFigure({
  title,
  name,
  locale,
  width = 1000,
  height,
  children,
}: {
  title: string;
  name: string;
  locale: Locale;
  width?: number;
  height: number;
  children: ReactNode;
}) {
  const svg = useRef<SVGSVGElement>(null),
    [error, setError] = useState(false),
    [busy, setBusy] = useState(false);
  async function save(png: boolean) {
    if (!svg.current) return;
    setBusy(true);
    setError(false);
    let url = '';
    try {
      const clone = svg.current.cloneNode(true) as SVGSVGElement;
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      clone.setAttribute('width', String(width));
      clone.setAttribute('height', String(height));
      const blob = new Blob([new XMLSerializer().serializeToString(clone)], {
        type: 'image/svg+xml;charset=utf-8',
      });
      url = URL.createObjectURL(blob);
      let href = url;
      if (png) {
        const img = new Image();
        await new Promise<void>((resolve, reject) => {
          img.onload = () => resolve();
          img.onerror = reject;
          img.src = url;
        });
        const canvas = document.createElement('canvas');
        canvas.width = width * 3;
        canvas.height = height * 3;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas unavailable');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        href = canvas.toDataURL('image/png');
      }
      const a = document.createElement('a');
      a.href = href;
      a.download = `${name}-${locale}.${png ? 'png' : 'svg'}`;
      a.click();
    } catch {
      setError(true);
    } finally {
      if (url) setTimeout(() => URL.revokeObjectURL(url), 1000);
      setBusy(false);
    }
  }
  return (
    <div className="paper-figure">
      <div className="paper-toolbar">
        <h3>{title}</h3>
        <div>
          <button disabled={busy} onClick={() => save(false)}>
            SVG ↓
          </button>
          <button disabled={busy} onClick={() => save(true)}>
            PNG ×3 ↓
          </button>
        </div>
      </div>
      {error && (
        <p role="alert">
          {locale === 'zh' ? '导出失败，请重试。' : 'Export failed. Please retry.'}
        </p>
      )}
      <svg
        ref={svg}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={title}
        fontFamily="Arial, Microsoft YaHei, sans-serif"
        fill="#243650"
        style={{ background: '#fff' }}
      >
        <title>{title}</title>
        <rect width={width} height={height} fill="white" />
        {children}
      </svg>
    </div>
  );
}
export function PaperOverview({
  index,
  thumbnails,
  locale,
}: {
  index: Index;
  thumbnails: Record<string, Geometry>;
  locale: Locale;
}) {
  const families = [...new Set(index.cases.map((c) => c.family))];
  const [chosen, setChosen] = useState(() =>
    families.map((f) => {
      const candidates = index.cases.filter((c) => c.family === f);
      return (
        candidates.find((c) =>
          f === 'interactive_robustness'
            ? c.turnCount > 1
            : f === 'multimodal_reverse_engineering'
              ? c.structure === 'frame'
              : c.referenceIds.length > 0,
        ) || candidates[0]
      ).id;
    }),
  );
  const cards = chosen.map((id) => index.cases.find((c) => c.id === id)!);
  const zh = locale === 'zh';
  return (
    <details className="paper-workbench">
      <summary>{zh ? '论文图版 · 案例覆盖总览' : 'Paper figures · Case coverage overview'}</summary>
      <p>
        {zh
          ? '每类选一个代表案例，可替换；以下为任务组成，不是模型性能或难度评分。'
          : 'Select one representative per family. This describes tasks, not model performance or measured difficulty.'}
      </p>
      <div className="paper-selectors">
        {families.map((f, i) => (
          <label key={f}>
            {label(familyNames, f, locale)}
            <select
              value={chosen[i]}
              onChange={(e) => setChosen(chosen.map((v, j) => (i === j ? e.target.value : v)))}
            >
              {index.cases
                .filter((c) => c.family === f)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id}
                  </option>
                ))}
            </select>
          </label>
        ))}
      </div>
      <PaperFigure
        title={zh ? '基准任务覆盖与代表案例' : 'Benchmark coverage and representative cases'}
        name="benchmark-overview"
        locale={locale}
        height={150 + Math.ceil(cards.length / 2) * 270}
      >
        <text x="32" y="38" fontSize="23" fontWeight="bold">
          {zh ? 'StructureClaw · 基准任务覆盖' : 'StructureClaw · Benchmark coverage'}
        </text>
        <text x="32" y="68" fontSize="14">
          {index.cases.length} {zh ? '案例' : 'cases'} · {index.modelCount}{' '}
          {zh ? '独立参考模型' : 'distinct reference models'} · {index.corpus.benchmarkVersion}
        </text>
        {cards.map((c, i) => {
          const x = 32 + (i % 2) * 485,
            y = 92 + Math.floor(i / 2) * 270;
          return (
            <g key={c.id} transform={`translate(${x},${y})`}>
              <rect width="460" height="248" rx="8" fill="#f7f9fc" stroke="#dce4ef" />
              <text x="18" y="28" fontSize="17" fontWeight="bold">
                {label(familyNames, c.family, locale)} ·{' '}
                {index.cases.filter((v) => v.family === c.family).length}
              </text>
              <svg x="10" y="35" width="220" height="130" viewBox="0 0 360 180">
                <Thumbnail model={thumbnails[c.referenceIds[0]]} />
              </svg>
              <SvgText
                x={235}
                y={63}
                text={`${c.structure} / ${c.modality}\n${c.turnCount} ${zh ? '轮次' : 'turns'}\n${c.referenceIds.length} ${zh ? '参考模型' : 'references'}`}
                width={26}
              />
              <SvgText x={18} y={185} text={c.id} width={56} size={13} />
              <text x="18" y="230" fontSize="12" fill="#62728a">
                {c.referenceIds.length
                  ? zh
                    ? '冻结参考几何'
                    : 'Frozen reference geometry'
                  : zh
                    ? '行为型任务 · 无参考几何'
                    : 'Behavior task · no reference geometry'}
              </text>
            </g>
          );
        })}
        {cards.length === 3 && (
          <g transform="translate(517,362)">
            <rect width="460" height="248" rx="8" fill="#f7f9fc" stroke="#dce4ef" />
            <text x="18" y="28" fontSize="17" fontWeight="bold">
              {zh ? '输入模态分布' : 'Input modality distribution'}
            </text>
            {[...new Set(index.cases.map((c) => c.modality))].map((modality, i) => {
              const count = index.cases.filter((c) => c.modality === modality).length;
              return (
                <g key={modality} transform={`translate(18,${65 + i * 45})`}>
                  <text y="5" fontSize="14">
                    {modality}
                  </text>
                  <rect
                    x="80"
                    y="-10"
                    width={(290 * count) / index.cases.length}
                    height="20"
                    rx="3"
                    fill="#4f74b9"
                  />
                  <text x={90 + (290 * count) / index.cases.length} y="5" fontSize="14">
                    {count}
                  </text>
                </g>
              );
            })}
            <text x="18" y="228" fontSize="12" fill="#62728a">
              {zh
                ? '按案例计数；同一参考模型可被多个案例引用。'
                : 'Case counts; references may be shared across cases.'}
            </text>
          </g>
        )}
        <text x="32" y={132 + Math.ceil(cards.length / 2) * 270} fontSize="12" fill="#62728a">
          {zh
            ? '来源：冻结 benchmark 清单；代表案例为人工可选，不表示性能。'
            : 'Source: frozen benchmark manifest; selected examples do not indicate performance.'}
        </text>
      </PaperFigure>
    </details>
  );
}
export function TaskFlow({ data, locale }: { data: CaseDetail; locale: Locale }) {
  const zh = locale === 'zh';
  let offset = 90;
  const rows = data.turns.map((turn, i) => {
    const expectations = turn.assertions
      .map(
        (a) => label(assertionNames, a.type, locale) + (a.description ? `: ${a.description}` : ''),
      )
      .join('\n');
    const height =
      Math.max(lines(turn.message, 58).length * 23, lines(expectations, 53).length * 23) + 86;
    const row = { turn, i, expectations, y: offset, height };
    offset += height + 28;
    return row;
  });
  return (
    <details className="paper-workbench">
      <summary>
        {zh ? '论文图版 · 输入与预期任务流程' : 'Paper figures · Input and expected task flow'}
      </summary>
      <PaperFigure
        title={zh ? '任务流程（冻结输入与评判约束）' : 'Task flow (frozen input and criteria)'}
        name={`${data.scenario.id}-flow`}
        locale={locale}
        height={offset + 90}
      >
        <SvgText text={data.scenario.id} x={30} y={32} size={20} width={90} />
        <text x="30" y="70" fontSize="13">
          {zh
            ? '原始输入 → 预期约束；不是智能体执行轨迹。'
            : 'Original input → expected criteria; not an agent execution trace.'}
        </text>
        {rows.map(({ turn, i, expectations, y, height }) => (
          <g key={i} transform={`translate(30,${y})`}>
            <rect width="940" height={height} fill="#f7f9fc" stroke="#dce4ef" rx="8" />
            <SvgText
              x={18}
              y={25}
              size={14}
              width={112}
              text={`${zh ? '轮次' : 'Turn'} ${i + 1} · ${data.references[i].join(', ') || (zh ? '无参考模型' : 'No reference model')}`}
            />
            <SvgText text={turn.message} x={18} y={76} width={58} />
            <text x="475" y="82" fontSize="22">
              →
            </text>
            <SvgText text={expectations} x={510} y={76} width={53} />
          </g>
        ))}
        <SvgText
          x={30}
          y={offset + 12}
          text={`Source: ${data.source}\nSHA-256: ${data.sourceSha256}`}
          size={12}
          width={140}
        />
      </PaperFigure>
    </details>
  );
}
export function EvidenceFigure({
  reference,
  locale,
  input,
  assertions,
  engineTarget,
}: {
  reference: Reference;
  locale: Locale;
  input: string;
  assertions: Assertion[];
  engineTarget?: string;
}) {
  const zh = locale === 'zh',
    m = reference.model;
  const selected = referenceResult(reference, assertions, engineTarget);
  const entries = Object.entries(selected.result?.displacements || {}).flatMap(([node, row]) =>
    Object.entries(row)
      .filter(([k, v]) => /^u[xyz]$/.test(k) && Number.isFinite(v))
      .map(([component, value]) => ({ node, component, value })),
  );
  const max = entries.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))[0];
  const loadRows = m.load_cases.flatMap((c) =>
    c.loads.map(
      (l) =>
        `${c.id} / ${l.node || l.element || '—'}: ${Object.entries(l)
          .filter(([k, v]) => /^[fw][xyz]$/.test(k) && v !== 0)
          .map(([k, v]) => `${k}=${v}`)
          .join(', ')} ${m.unit_system === 'SI' ? (l.type === 'distributed' ? 'kN/m' : 'kN') : ''}`,
    ),
  );
  const loads =
    loadRows.slice(0, 6).join('\n') +
    (loadRows.length > 6
      ? `\n… ${zh ? '共' : 'total'} ${loadRows.length} ${zh ? '条，完整数据见模型' : 'records; see model for full data'}`
      : '');
  const condition = `${m.nodes.length} ${zh ? '节点' : 'nodes'} / ${m.elements.length} ${zh ? '构件' : 'members'}\n${m.nodes.filter((n) => n.restraints?.some(Boolean)).length} ${zh ? '约束节点' : 'restrained nodes'}\n${loads}`;
  const resultText =
    max && selected.result
      ? `${selected.engine} / ${selected.caseName || '—'}\n${zh ? '最大绝对平移分量（非任务目标推断）' : 'Largest absolute translation component (not an inferred task target)'}\n${max.node} / ${max.component} = ${formatNumber(max.value)} ${resultUnit(selected.result, 'displacements', max.component)}\n${zh ? '全局坐标；保留正负号。' : 'Global coordinates; signs retained.'}`
      : zh
        ? '该轮无可展示的数值标答；依据原始评判约束。'
        : 'No numerical reference available for this turn; use original criteria.';
  const row1 = Math.max(245, lines(input, 58).length * 23 + 65),
    row2 = Math.max(lines(condition, 58).length, lines(resultText, 58).length) * 23 + 75;
  const h = 120 + row1 + row2;
  return (
    <PaperFigure
      title={zh ? '建模证据链' : 'Modeling evidence chain'}
      name={`${reference.id}-evidence`}
      locale={locale}
      height={h}
    >
      <text x="25" y="35" fontSize="20" fontWeight="bold">
        {reference.id}
      </text>
      <text x="25" y="80" fontSize="16">
        {zh ? '(a) 原始任务' : '(a) Original task'}
      </text>
      <SvgText text={input} x={25} y={110} width={58} />
      <text x="525" y="80" fontSize="16">
        {zh ? '(b) 冻结参考几何' : '(b) Frozen geometry'}
      </text>
      <svg x="520" y="110" width="440" height="200" viewBox="0 0 360 180">
        <Thumbnail model={m} />
      </svg>
      <text x="25" y={80 + row1} fontSize="16">
        {zh ? '(c) 荷载与边界条件' : '(c) Loads and boundaries'}
      </text>
      <SvgText x={25} y={115 + row1} width={58} text={condition} />
      <text x="525" y={80 + row1} fontSize="16">
        {zh ? '(d) 数值标答摘要' : '(d) Numerical reference summary'}
      </text>
      <SvgText x={525} y={115 + row1} width={58} text={resultText} />
      <text x="25" y={h - 24} fontSize="12" fill="#62728a">
        {zh
          ? `输入 → 几何 → 条件 → 标答；来源：models/${reference.id}.json`
          : `Input → geometry → conditions → reference; source: models/${reference.id}.json`}
      </text>
    </PaperFigure>
  );
}
