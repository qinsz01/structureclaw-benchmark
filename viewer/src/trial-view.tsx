import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { dataUrl, fetchData, downloadJson } from './data';
import type { Locale } from './types';
import type { TrialAsset, TrialCase, TrialIndex, TrialTurn } from './trial-types';
import { PublicText } from './research-public-text';
import { parsePublicText } from './public-text';
import './trial.css';

export function TrialOverview({
  trial,
  locale,
  onFilter,
}: {
  trial: TrialIndex;
  locale: Locale;
  onFilter: (value: string) => void;
}) {
  const z = locale === 'zh';
  const diversity = trial.edition === 'section-diversity-v1';
  return (
    <section className="trial-overview" aria-label={z ? 'Codex 评测结果' : 'Codex trial results'}>
      <div className="trial-heading">
        <div>
          <span className="research-eyebrow">
            CODEX / FULL 300 · {trial.revision.toUpperCase()}
          </span>
          <h2>
            {z
              ? diversity
                ? 'Codex · 截面多样性版实测'
                : 'Codex 实测结果'
              : diversity
                ? 'Codex · section diversity trial'
                : 'Codex trial results'}
          </h2>
        </div>
        <span>
          {trial.model} · {trial.reasoningEffort}
        </span>
      </div>
      <div className="trial-stats">
        <button onClick={() => onFilter('passed')}>
          <b>
            {trial.cases.passed}
            <small> / {trial.cases.completed}</small>
          </b>
          <span>
            {z ? '题目通过' : 'Cases passed'} ·{' '}
            {((100 * trial.cases.passed) / trial.cases.completed).toFixed(1)}%
          </span>
        </button>
        <div>
          <b>
            {trial.turns.passed}
            <small> / {trial.turns.completed}</small>
          </b>
          <span>
            {z ? '轮次通过' : 'Turns passed'} ·{' '}
            {((100 * trial.turns.passed) / trial.turns.completed).toFixed(1)}%
          </span>
        </div>
        <button onClick={() => onFilter('not-passed')}>
          <b>{trial.cases.notPassed}</b>
          <span>{z ? '未通过 · 点击筛选' : 'Not passed · filter'}</span>
        </button>
        {diversity ? (
          <div>
            <b>{trial.diversity?.distinctJ}</b>
            <span>
              {z ? '不同 J · 同值最多覆盖 ' : 'Distinct J · maximum repeated coverage '}
              {trial.diversity?.maximumJCases}/300
            </span>
          </div>
        ) : (
          <button onClick={() => onFilter('repaired')}>
            <b>2</b>
            <span>{z ? '缺陷已修复并定向验证' : 'Defects repaired and checked'}</span>
          </button>
        )}
      </div>
      <div className="trial-engine-bars">
        {Object.entries(trial.byEngine).map(([engine, row]) => (
          <div key={engine}>
            <div>
              <strong>{engine}</strong>
              <span>
                {row.passed} / {row.cases}
              </span>
            </div>
            <div
              className="trial-bar"
              role="img"
              aria-label={`${engine}: ${row.passed}/${row.cases}`}
            >
              <span style={{ width: `${(100 * row.passed) / row.cases}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="trial-attributions" aria-label={z ? '未通过归因' : 'Failure attribution'}>
        {Object.entries(trial.attributionCounts).map(([key, count]) => (
          <span key={key}>
            <b>{count}</b> {attribution[key]?.[z ? 0 : 1] || key}
          </span>
        ))}
      </div>
      <p>
        {diversity
          ? z
            ? '本版 300 题、420 轮均为真实 Codex 作答。30 道题面修正后重新作答，旧记录保留；原版 282/300 单独归档。题目和模型预览保留原版，Codex 页展示本次实际题面与附件。StructureClaw 正式试验及外部独立盲审待完成。'
            : 'All 300 cases and 420 turns are actual Codex calls. Thirty source-corrected cases were rerun with prior evidence retained; the baseline 282/300 is separate. The catalogue/model preview remains the baseline; the Codex tab shows the exact received edition. Formal StructureClaw trials and external blind review remain pending.'
          : z
            ? '原始 300 题成绩保持不变。INT-056 新题面三轮复测通过；STD-080 的 PKPM 适配器验证通过，两者单独记录。此处是 Codex 校验，StructureClaw 正式试验尚未运行。'
            : 'The original 300-case scores are unchanged. INT-056 passed a fresh three-turn trial; STD-080 passed a PKPM adapter regression. These checks are recorded separately. This is a Codex validation; the formal StructureClaw trial has not run.'}
      </p>
    </section>
  );
}

export function TrialBadge({
  status,
  repaired,
  locale,
}: {
  status: string;
  repaired?: boolean;
  locale: Locale;
}) {
  const z = locale === 'zh';
  return (
    <span className={`trial-badge ${status === 'passed' ? 'trial-pass' : 'trial-fail'}`}>
      {status === 'passed'
        ? z
          ? 'Codex · 通过'
          : 'Codex · passed'
        : z
          ? 'Codex · 未通过'
          : 'Codex · not passed'}
      {repaired && <small>{z ? '另有修复验证' : 'separate repair check'}</small>}
    </span>
  );
}

function Answer({ text, assets }: { text: string; assets: TrialAsset[] }) {
  // Candidate Markdown is untrusted text. Only verified, locally exported
  // artifacts can become links; HTML and arbitrary external URLs stay inert.
  const inline = (value: string): ReactNode[] =>
    value.split(/(\*\*[^*]+\*\*|`[^`]+`|!?\[[^\]]*\]\([^)]+\))/g).map((part, i) => {
      if (part.startsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>;
      if (part.startsWith('`')) return <code key={i}>{part.slice(1, -1)}</code>;
      const match = part.match(/^!?\[([^\]]*)\]\(([^)]+)\)$/);
      if (match) {
        const tail = match[2].split('/scratch/')[1];
        const asset = assets.find((a) => tail && a.scratchPath === tail);
        return asset ? (
          <a key={i} href={dataUrl(asset.path)} target="_blank" rel="noreferrer">
            {match[1]}
          </a>
        ) : (
          <span key={i}>{match[1]}</span>
        );
      }
      return part;
    });
  return (
    <div className="trial-answer">
      {text.split(/(```[\s\S]*?```)/g).map((chunk, n) => {
        if (chunk.startsWith('```'))
          return <pre key={n}>{chunk.replace(/^```[^\n]*\n?/, '').replace(/```$/, '')}</pre>;
        return parsePublicText(chunk).map((b, i) => {
          const key = `${n}-${i}`;
          if (b.type === 'table')
            return (
              <div className="research-public-table" key={key} tabIndex={0}>
                <table>
                  <thead>
                    <tr>
                      {b.headers.map((h, j) => (
                        <th key={j}>{inline(h)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {b.rows.map((r, j) => (
                      <tr key={j}>
                        {r.map((c, k) => (
                          <td key={k}>{inline(c)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          if (b.type === 'heading') return <h4 key={key}>{inline(b.text)}</h4>;
          if (b.type === 'list')
            return (
              <ul key={key}>
                {b.items.map((t, j) => (
                  <li key={j}>{inline(t)}</li>
                ))}
              </ul>
            );
          return <p key={key}>{inline(b.text)}</p>;
        });
      })}
    </div>
  );
}

const attribution: Record<string, [string, string]> = {
  candidate_modeling: ['结构建模错误', 'Structural modeling error'],
  candidate_derived_sign: ['派生量符号错误', 'Incorrect derived-result sign'],
  candidate_input_transcription: ['图纸属性抄写差异', 'Drawing transcription difference'],
  candidate_report_convention: [
    '表格采用了不同的内力符号约定',
    'Table uses different action signs',
  ],
  candidate_missing_answer_table: [
    '最终答复缺少要求的结果表',
    'Required table absent from final answer',
  ],
  sut_capability: ['SUT 输入兼容缺口', 'SUT input compatibility gap'],
  input_interpretation_dispute: ['原题面存在解释歧义', 'Original input was ambiguous'],
};

function TrialAppendix({ asset, locale }: { asset: TrialAsset; locale: Locale }) {
  const [text, setText] = useState<string>();
  const [error, setError] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let active = true;
    if (open && text === undefined)
      fetch(dataUrl(asset.path))
        .then((response) => {
          if (!response.ok) throw Error('Attachment unavailable');
          return response.text();
        })
        .then(
          (value) => active && setText(value),
          () => active && setError(true),
        );
    return () => {
      active = false;
    };
  }, [open, asset.path, text]);
  return (
    <details className="trial-appendix" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>
        {locale === 'zh' ? '查看题目附件' : 'Read task attachment'} · {asset.name}
      </summary>
      {error ? (
        <p role="alert">{locale === 'zh' ? '附件加载失败。' : 'Unable to load attachment.'}</p>
      ) : text === undefined ? (
        <p role="status">{locale === 'zh' ? '正在读取…' : 'Loading…'}</p>
      ) : (
        <PublicText text={text} />
      )}
    </details>
  );
}

export function TrialPanel({
  caseId,
  turnId,
  locale,
}: {
  caseId: string;
  turnId: string;
  locale: Locale;
}) {
  const z = locale === 'zh';
  const [result, setResult] = useState<{ id: string; data?: TrialCase; error?: boolean }>();
  const [repair, setRepair] = useState<{
    turns: TrialTurn[];
    artifacts: TrialAsset[];
    sutCommit: string;
  }>();
  const [repairError, setRepairError] = useState(false);
  const [version, setVersion] = useState(() =>
    caseId === 'INT-056' &&
    new URLSearchParams(location.hash.split('?')[1]).get('trialVersion') === 'repair'
      ? 'repair'
      : new URLSearchParams(location.hash.split('?')[1]).get('trialVersion') === 'historical'
        ? 'historical'
        : 'current',
  );
  const changeVersion = (value: string) => {
    setVersion(value);
    const params = new URLSearchParams(location.hash.split('?')[1]);
    if (value !== 'current') params.set('trialVersion', value);
    else params.delete('trialVersion');
    history.replaceState(null, '', `${location.hash.split('?')[0]}?${params}`);
  };
  useEffect(() => {
    let active = true;
    const prefix = version === 'current' ? 'trials' : 'trials/historical';
    fetchData<TrialCase>(`${prefix}/cases/${caseId}.json`).then(
      (data) => active && setResult({ id: `${caseId}/${version}`, data }),
      () => active && setResult({ id: `${caseId}/${version}`, error: true }),
    );
    if (caseId === 'INT-056')
      fetchData<{ turns: TrialTurn[]; artifacts: TrialAsset[]; sutCommit: string }>(
        'trials/historical/repair-INT-056.json',
      ).then(
        (data) => active && setRepair(data),
        () => active && setRepairError(true),
      );
    return () => {
      active = false;
    };
  }, [caseId, version]);
  if (result?.id !== `${caseId}/${version}` || !result.data)
    return (
      <p role={result?.error ? 'alert' : 'status'}>
        {result?.error
          ? z
            ? '此案例的 Codex 记录加载失败。'
            : 'Unable to load the Codex record.'
          : z
            ? '正在读取 Codex 作答…'
            : 'Loading Codex answer…'}
      </p>
    );
  const trial = result.data;
  const turn = (version === 'repair' ? repair?.turns : trial.turns)?.find((t) => t.id === turnId);
  const category = trial.attribution?.category;
  return (
    <div className="trial-panel" data-trial-version={version}>
      <header className="trial-heading">
        <div>
          <h2>{z ? 'Codex 作答与评测' : 'Codex answer & evaluation'}</h2>
          <p>
            {trial.model} ·{' '}
            {version === 'repair'
              ? z
                ? '修复后新会话'
                : 'Fresh repair trial'
              : `2026-10-27 · ${trial.revision}`}
          </p>
        </div>
        {
          <label>
            {z ? '查看版本' : 'Version'}
            <select
              aria-label={z ? '作答版本' : 'Answer version'}
              value={version}
              onChange={(e) => changeVersion(e.target.value)}
            >
              <option value="current">
                {z ? '截面多样性 v1 · 300 题' : 'Section diversity v1 · 300 cases'}
              </option>
              <option value="historical">
                {z ? '原版 300 题运行' : 'Baseline 300-case trial'}
              </option>
              {caseId === 'INT-056' && (
                <option value="repair">
                  {z ? '原版题面修复后三轮复测' : 'Baseline three-turn repair trial'}
                </option>
              )}
            </select>
          </label>
        }
      </header>
      <p className="trial-version-note">
        {z
          ? '下面展示所选作答实际收到的题面与附件；其他题目和模型预览页展示原版。本次参数以这里的题面为准。多样性版按相同题源保留原记录，题源修正的 30 题使用新会话；原版成绩独立保留。交互和图件复核由评估器作者完成，尚无外部独立盲审。'
          : 'The question and attachments below are exactly those received. Other task and model preview tabs show the baseline; use the inputs here for this trial. The diversity edition retains identical-source cases and uses fresh whole-case threads for 30 source corrections. Baseline scores stay separate. Interaction and figure reviews are by the evaluator author, without external blind acceptance.'}
      </p>
      {caseId === 'STD-080' && version === 'historical' && (
        <div className="trial-repair-note">
          {z
            ? '兼容缺口已修复：原始模型在 PKPM 原生重算，396 个请求量通过严格容差。这是适配器验证，不是新的 Codex 完整作答成绩。'
            : 'Compatibility repaired: the original model passed all 396 strict numerical checks in a fresh native PKPM run. This is an adapter regression, not a new full Codex answer score.'}
        </div>
      )}
      {version !== 'repair' && category && (
        <div className="trial-failure-note">
          <strong>{attribution[category]?.[z ? 0 : 1] || category}</strong>
          <details>
            <summary>{z ? '原始归因说明' : 'Original attribution'}</summary>
            <p>{trial.attribution?.reason}</p>
          </details>
        </div>
      )}
      {turn ? (
        <>
          <div className="trial-turn-heading">
            <code>
              {caseId} / {turn.id}
            </code>
            <TrialBadge status={turn.status} locale={locale} />
            {turn.execution && <span>{turn.execution.elapsedSeconds.toFixed(1)} s</span>}
          </div>
          <section className="research-panel trial-question">
            <h3>{z ? '当时题面' : 'Question received'}</h3>
            <PublicText text={turn.instruction} />
            {turn.attachments
              ?.filter((a) => a.name.endsWith('.md'))
              .map((a) => (
                <TrialAppendix key={a.path} asset={a} locale={locale} />
              ))}
            <div className="trial-files">
              {turn.attachments?.map((a) => (
                <a key={a.path} href={dataUrl(a.path)} target="_blank" rel="noreferrer">
                  {a.name} ↗
                </a>
              ))}
            </div>
            {turn.attachments
              ?.filter((a) => /\.png$/i.test(a.path))
              .map((a) => (
                <a key={a.path} href={dataUrl(a.path)} target="_blank" rel="noreferrer">
                  <img
                    className="trial-input-image"
                    src={dataUrl(a.path)}
                    alt={a.name}
                    loading="lazy"
                  />
                </a>
              ))}
          </section>
          <section className="research-panel">
            <div className="trial-heading">
              <h3>{z ? 'Codex 原始作答' : 'Original Codex answer'}</h3>
              <div className="trial-files">
                {turn.answerFile && (
                  <a
                    href={dataUrl(turn.answerFile.path)}
                    download={`${caseId}-${turn.id}-answer.txt`}
                  >
                    {z ? '下载原文' : 'Download answer'}
                  </a>
                )}
                <button
                  onClick={() =>
                    downloadJson(
                      {
                        caseId,
                        version,
                        model: trial.model,
                        sutCommit: version === 'repair' ? repair?.sutCommit : trial.sutCommit,
                        ...turn,
                      },
                      `${caseId}-${turn.id}-${version}.json`,
                    )
                  }
                >
                  JSON ↓
                </button>
              </div>
            </div>
            <Answer
              text={turn.answer}
              assets={version === 'repair' ? repair?.artifacts || [] : trial.artifacts}
            />
          </section>
          <section className="research-panel trial-metrics">
            <h3>{z ? '本轮评分依据' : 'Turn evaluation gates'}</h3>
            {turn.metrics.map((m, i) => (
              <details key={i} className={m.pass ? 'gate-pass' : 'gate-fail'}>
                <summary>
                  <span>{m.pass ? '✓' : '×'}</span>
                  <code>{m.metric}</code>
                  <b>{m.pass ? (z ? '通过' : 'passed') : z ? '未通过' : 'not passed'}</b>
                </summary>
                <pre>
                  {typeof m.actual === 'string' ? m.actual : JSON.stringify(m.actual, null, 2)}
                </pre>
              </details>
            ))}
          </section>
          {!!turn.artifacts?.length && (
            <section className="research-panel">
              <h3>{z ? '本轮生成的图件与文件' : 'Figures & files from this turn'}</h3>
              <div className="trial-files">
                {turn.artifacts.map((a) => (
                  <a key={a.path + a.name} href={dataUrl(a.path)} target="_blank" rel="noreferrer">
                    {a.scratchPath} ↗
                  </a>
                ))}
              </div>
              <div className="trial-gallery">
                {turn.artifacts
                  .filter((a) => /\.(png|jpg|jpeg)$/i.test(a.path))
                  .map((a) => (
                    <a key={a.path} href={dataUrl(a.path)} target="_blank" rel="noreferrer">
                      <img src={dataUrl(a.path)} alt={a.name} loading="lazy" />
                    </a>
                  ))}
              </div>
            </section>
          )}
        </>
      ) : (
        <p role={repairError ? 'alert' : 'status'}>
          {repairError
            ? z
              ? '复测记录加载失败，请刷新重试。'
              : 'Unable to load the repair trial. Reload to retry.'
            : z
              ? '正在读取本轮记录…'
              : 'Loading turn…'}
        </p>
      )}
    </div>
  );
}
