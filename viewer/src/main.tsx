import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type {
  Assertion,
  Attachment,
  CaseDetail,
  CaseSummary,
  Geometry,
  Index,
  Locale,
  Reference,
  Result,
} from './types';
import { assertionNames, familyNames, label, structureNames, words } from './i18n';
import { dataUrl, downloadJson, fetchData, formatNumber } from './data';
import { Thumbnail } from './thumbnail';
import DrawingPreview from './drawing';
import { initialIndex, readViewState, saveViewState } from './view-state';
import './styles.css';
import { ResultLab } from './result-lab';
import { PaperOverview, TaskFlow, EvidenceFigure } from './paper-figures';
import { referenceResult, resultUnit } from './reference-math';
import type { Pick } from './reference-math';
const Scene = lazy(() => import('./scene'));

function useData<T>(path: string | null): { data?: T; error?: boolean } {
  const [state, setState] = useState<{ path: string | null; data?: T; error?: boolean }>({
    path: null,
  });
  useEffect(() => {
    let active = true;
    if (path)
      fetchData<T>(path).then(
        (data) => {
          if (active) setState({ path, data });
        },
        () => {
          if (active) setState({ path, error: true });
        },
      );
    return () => {
      active = false;
    };
  }, [path]);
  return state.path === path ? state : {};
}
function Loading({ locale, error = false }: { locale: Locale; error?: boolean }) {
  const t = words[locale];
  return (
    <div className="loading" role="status">
      {error ? t.error : t.loading}
      {error && <button onClick={() => location.reload()}>{t.retry}</button>}
    </div>
  );
}
function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
function Tags({ item, locale }: { item: CaseSummary; locale: Locale }) {
  return (
    <div className="tags">
      <span>{label(structureNames, item.structure, locale)}</span>
      <span>{item.locale === 'zh' ? '中文' : 'EN'}</span>
      <span>{item.difficulty}</span>
    </div>
  );
}
function Requirements({ assertions, locale }: { assertions: Assertion[]; locale: Locale }) {
  return (
    <ul className="requirements">
      {assertions.map((a, i) => (
        <li key={i}>
          <span className="requirement-dot" />
          <div>
            <strong>{label(assertionNames, a.type, locale)}</strong>
            {a.description && <p>{a.description}</p>}
            {a.groundTruthId && <code>{a.groundTruthId}</code>}
            {a.expected != null && <span className="requirement-value">{String(a.expected)}</span>}
          </div>
        </li>
      ))}
    </ul>
  );
}
function Library({
  index,
  thumbnails,
  locale,
}: {
  index: Index;
  thumbnails: Record<string, Geometry>;
  locale: Locale;
}) {
  const t = words[locale];
  const params = new URLSearchParams(location.hash.split('?')[1]);
  const [query, setQuery] = useState(params.get('q') || ''),
    [family, setFamily] = useState(params.get('family') || ''),
    [language, setLanguage] = useState(params.get('lang') || ''),
    [structure, setStructure] = useState(params.get('structure') || ''),
    [page, setPage] = useState(Math.max(1, Number(params.get('page')) || 1));
  const filtered = useMemo(
    () =>
      index.cases.filter(
        (c) =>
          (!family || c.family === family) &&
          (!language || c.locale === language) &&
          (!structure || c.structure === structure) &&
          c.search.toLowerCase().includes(query.trim().toLowerCase()),
      ),
    [index, query, family, language, structure],
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / 12)),
    currentPage = Math.min(page, totalPages);
  useEffect(() => {
    const search = new URLSearchParams();
    if (query) search.set('q', query);
    if (family) search.set('family', family);
    if (language) search.set('lang', language);
    if (structure) search.set('structure', structure);
    if (page > 1) search.set('page', String(page));
    const hash = `#/${search.size ? '?' + search : ''}`;
    history.replaceState(null, '', hash);
    sessionStorage.setItem('explorer-library', hash);
  }, [query, family, language, structure, page]);
  const reset = () => {
    setQuery('');
    setFamily('');
    setLanguage('');
    setStructure('');
    setPage(1);
  };
  const hero = Object.values(thumbnails).find((m) => m.coordinate_system.dimension === '3d');
  return (
    <>
      <PaperOverview index={index} thumbnails={thumbnails} locale={locale} />
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span />
            {t.eyebrow}
          </div>
          <h1>{t.title}</h1>
          <p>{t.intro}</p>
          <div className="hero-stats">
            <div>
              <b>{index.cases.length}</b>
              <span>{t.cases}</span>
            </div>
            <div>
              <b>{Object.keys(index.corpus.taskFamilies).length}</b>
              <span>{t.families}</span>
            </div>
            <div>
              <b>{new Set(index.cases.map((c) => c.locale)).size}</b>
              <span>{t.languages}</span>
            </div>
          </div>
        </div>
        <div className="hero-art">
          <div className="orbit-label">REFERENCE / 3D</div>
          <Thumbnail model={hero} />
          <div className="art-foot">
            <span>● {t.reference}</span>
            <code>x · y · z</code>
          </div>
        </div>
      </section>
      <section className="library" aria-label={t.library}>
        <div className="library-heading">
          <div>
            <span className="section-kicker">EXPLORE THE CORPUS</span>
            <h2>{t.library}</h2>
          </div>
          <span className="muted">
            {t.version} <code>{index.corpus.benchmarkVersion}</code>
          </span>
        </div>
        <div className="filter-bar">
          <div className="family-tabs" role="group" aria-label={t.families}>
            {['', ...Object.keys(index.corpus.taskFamilies)].map((f) => (
              <button
                key={f}
                aria-pressed={family === f}
                onClick={() => {
                  setFamily(f);
                  setPage(1);
                }}
              >
                {f ? label(familyNames, f, locale) : t.all}
                <span>{f ? index.corpus.taskFamilies[f].total : index.cases.length}</span>
              </button>
            ))}
          </div>
          <div className="search-row">
            <label className="search">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="10" cy="10" r="6.5" />
                <path d="m15 15 5 5" />
              </svg>
              <input
                type="search"
                value={query}
                placeholder={t.search}
                aria-label={t.search}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(1);
                }}
              />
            </label>
            <select
              aria-label={t.anyLanguage}
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value);
                setPage(1);
              }}
            >
              <option value="">{t.anyLanguage}</option>
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
            <select
              aria-label={t.anyStructure}
              value={structure}
              onChange={(e) => {
                setStructure(e.target.value);
                setPage(1);
              }}
            >
              <option value="">{t.anyStructure}</option>
              {[...new Set(index.cases.map((c) => c.structure))].map((s) => (
                <option key={s} value={s}>
                  {label(structureNames, s, locale)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="result-count">
          <span>
            <b>{filtered.length}</b> {t.found}
          </span>
          {(query || family || language || structure) && (
            <button onClick={reset}>{t.reset} ×</button>
          )}
          <span className="original-note">{t.original}</span>
        </div>
        <div className="case-grid">
          {filtered.slice((currentPage - 1) * 12, currentPage * 12).map((c) => (
            <a className="case-card" key={c.id} href={`#/case/${encodeURIComponent(c.id)}`}>
              <div className={`card-preview ${c.referenceIds.length ? '' : 'behavior-preview'}`}>
                <span className="preview-tag">
                  {c.referenceIds.length
                    ? c.modality === 'text'
                      ? t.reference
                      : c.modality === 'dxf'
                        ? t.dxf
                        : t.image
                    : t.behavior}
                </span>
                <Thumbnail model={thumbnails[c.referenceIds[0]]} />
                <span className="card-arrow">↗</span>
              </div>
              <div className="card-body">
                <div className="card-family">
                  {label(familyNames, c.family, locale)}
                  {c.turnCount > 1 && (
                    <span>
                      {c.turnCount} {t.turn}
                    </span>
                  )}
                </div>
                <h3>{c.description}</h3>
                <Tags item={c} locale={locale} />
                <code className="case-id">{c.id}</code>
              </div>
            </a>
          ))}
        </div>
        {!filtered.length && (
          <div className="empty">
            <h3>{t.empty}</h3>
            <p>{t.emptyHint}</p>
            <button onClick={reset}>{t.reset}</button>
          </div>
        )}
        {filtered.length > 0 && (
          <nav className="pagination" aria-label={t.page}>
            <button
              disabled={currentPage === 1}
              onClick={() => {
                setPage(currentPage - 1);
                document.querySelector('.library')?.scrollIntoView();
              }}
            >
              ← {t.prevPage}
            </button>
            <span>
              {currentPage} / {totalPages}
            </span>
            <button
              disabled={currentPage === totalPages}
              onClick={() => {
                setPage(currentPage + 1);
                document.querySelector('.library')?.scrollIntoView();
              }}
            >
              {t.nextPage} →
            </button>
          </nav>
        )}
      </section>
    </>
  );
}

function NumericTable({
  result,
  kind,
  locale,
  onPick,
  pick,
}: {
  result: Result;
  kind: 'displacements' | 'reactions' | 'forces';
  locale: Locale;
  onPick: (pick: Pick) => void;
  pick: Pick | null;
}) {
  const t = words[locale],
    units = result.meta?.units || result.units || {};
  if (kind !== 'forces') {
    const values = result[kind] || {};
    const order =
      kind === 'displacements'
        ? ['ux', 'uy', 'uz', 'rx', 'ry', 'rz']
        : ['fx', 'fy', 'fz', 'mx', 'my', 'mz'];
    const columns = [...new Set(Object.values(values).flatMap((v) => Object.keys(v)))].sort(
      (a, b) => order.indexOf(a) - order.indexOf(b),
    );
    if (!columns.length) return <p className="muted">{t.unavailable}</p>;
    return (
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t.nodes}</th>
              {columns.map((c) => (
                <th key={c}>
                  {c}
                  <br />
                  <span>
                    {units[
                      kind === 'displacements'
                        ? c.startsWith('r')
                          ? 'rotation'
                          : 'displacement'
                        : c.startsWith('m')
                          ? 'moment'
                          : 'force'
                    ] || '—'}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(values).map(([id, row]) => (
              <tr key={id}>
                <td>
                  <code>{id}</code>
                </td>
                {columns.map((c) => (
                  <td
                    key={c}
                    data-component={c}
                    className={`number ${pick?.kind === 'node' && pick.entity === id && pick.component === c ? 'is-selected' : ''}`}
                    title={row[c] == null ? t.unavailable : String(row[c])}
                  >
                    {row[c] == null ? (
                      '—'
                    ) : (
                      <button
                        className="numeric-pick"
                        onClick={() =>
                          onPick({
                            entity: id,
                            kind: 'node',
                            component: c,
                            value: row[c],
                            unit: resultUnit(result, kind, c),
                          })
                        }
                      >
                        {formatNumber(row[c])}
                      </button>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  const rows: { entity: string; component: string; value: number; unit: string }[] = [];
  const walk = (obj: unknown, entity: string, prefix = '') => {
    if (!obj || typeof obj !== 'object') return;
    for (const [key, value] of Object.entries(obj)) {
      const component = prefix ? `${prefix}.${key}` : key;
      if (typeof value === 'number') {
        const type = /^(M|T|m)/.test(key) ? 'moment' : /^(N|V|F|axial)/i.test(key) ? 'force' : '';
        rows.push({ entity, component, value, unit: units[type] || '—' });
      } else if (typeof value === 'object') walk(value, entity, component);
    }
  };
  for (const [entity, values] of Object.entries(result[kind] || {})) walk(values, entity);
  if (!rows.length) return <p className="muted">{t.unavailable}</p>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>{t.entity}</th>
            <th>{t.component}</th>
            <th>{t.value}</th>
            <th>{t.unit}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.entity + row.component}>
              <td>
                <code>{row.entity}</code>
              </td>
              <td>{row.component}</td>
              <td
                className={`number ${pick?.kind === 'member' && pick.entity === row.entity && (pick.component === row.component || pick.component.startsWith('max(')) ? 'is-selected' : ''}`}
                title={String(row.value)}
              >
                <button
                  className="numeric-pick"
                  onClick={() =>
                    onPick({
                      entity: row.entity,
                      kind: 'member',
                      component: row.component,
                      value: row.value,
                      unit: row.unit,
                    })
                  }
                >
                  {formatNumber(row.value)}
                </button>
              </td>
              <td>{row.unit}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Numbers({
  reference,
  assertions,
  engineTarget,
  locale,
  onPick,
  pick,
}: {
  reference: Reference;
  assertions: Assertion[];
  engineTarget?: string;
  locale: Locale;
  onPick: (pick: Pick) => void;
  pick: Pick | null;
}) {
  const t = words[locale];
  const [kind, setKind] = useState<'displacements' | 'reactions' | 'forces'>('displacements');
  const assertion = assertions.find(
    (a) => a.type === 'numerical_matches' && a.groundTruthId === reference.id,
  );
  if (!assertion) return <p className="note">{t.missingNumbers}</p>;
  const engine = (assertion.engineId || engineTarget || 'builtin-opensees').replace('builtin-', '');
  const commercial = reference.commercial?.engines[engine];
  const result = engine === 'opensees' ? reference.numerical?.result : commercial?.response;
  if (!result)
    return (
      <p className="note">
        {t.missingEngine} · {engine}
      </p>
    );
  const engineName =
    engine === 'opensees'
      ? `${reference.numerical?.solver.name} ${reference.numerical?.solver.version}`
      : `${commercial?.identity.name} ${commercial?.identity.configuredVersion}`;
  const caseName =
    engine === 'opensees'
      ? reference.numerical?.analysisSelection.loadCombinationId
      : result.caseKey;
  const displacements = Object.entries(result.displacements || {}).flatMap(([node, values]) =>
    Object.entries(values)
      .filter(([k]) => /^u[xyz]$/.test(k))
      .map(([component, value]) => ({ node, component, value })),
  );
  const max = displacements.reduce<(typeof displacements)[number] | null>(
    (a, b) => (!a || Math.abs(b.value) > Math.abs(a.value) ? b : a),
    null,
  );
  return (
    <>
      <div className="numeric-meta">
        <span>
          {t.engine}
          <b>{engineName}</b>
        </span>
        <span>
          {t.case}
          <b>{caseName || t.noData}</b>
        </span>
        {max && (
          <span>
            {locale === 'zh' ? '最大绝对平移分量' : 'Largest absolute translation component'}
            <button
              className="numeric-pick"
              title={String(max.value)}
              onClick={() =>
                onPick({
                  entity: max.node,
                  kind: 'node',
                  component: max.component,
                  value: max.value,
                  unit: resultUnit(result, 'displacements', max.component),
                })
              }
            >
              {formatNumber(max.value)}{' '}
              <small>
                {(result.meta?.units || result.units)?.displacement || ''} · {max.node}/
                {max.component}
              </small>
            </button>
          </span>
        )}
      </div>
      <p className="muted small">{t.numericalNote}</p>
      <div className="result-tabs">
        {(['displacements', 'reactions', 'forces'] as const).map((k) => (
          <button key={k} aria-pressed={kind === k} onClick={() => setKind(k)}>
            {k === 'displacements' ? t.displacement : k === 'reactions' ? t.reactions : t.forces}
          </button>
        ))}
      </div>
      <NumericTable result={result} kind={kind} locale={locale} onPick={onPick} pick={pick} />
      <details>
        <summary>{t.more}</summary>
        <Json value={engine === 'opensees' ? reference.numerical : commercial} />
      </details>
    </>
  );
}
function ImagePreview({ src, name, locale }: { src: string; name: string; locale: Locale }) {
  const [open, setOpen] = useState(false);
  const t = words[locale];
  const ref = React.useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (open) ref.current?.showModal();
    else ref.current?.close();
  }, [open]);
  return (
    <>
      <button
        className="attachment-image"
        aria-label={`${t.imageOpen}: ${name}`}
        onClick={() => setOpen(true)}
      >
        <img src={src} alt={name} loading="lazy" />
        <span>{t.imageOpen} ↗</span>
      </button>
      <dialog
        ref={ref}
        onCancel={() => setOpen(false)}
        onClick={(e) => {
          if (e.target === ref.current) setOpen(false);
        }}
      >
        <button className="dialog-close" aria-label={t.modalClose} onClick={() => setOpen(false)}>
          ×
        </button>
        <img src={src} alt={name} />
        <p>{name}</p>
      </dialog>
    </>
  );
}
function ReferencePanel({
  input,
  id,
  assertions,
  locale,
  engineTarget,
  attachment,
}: {
  id: string;
  input: string;
  assertions: Assertion[];
  locale: Locale;
  engineTarget?: string;
  attachment?: Attachment;
}) {
  const { data, error } = useData<Reference>(`models/${id}.json`);
  const [pick, setPick] = useState<Pick | null>(null);
  const t = words[locale];
  if (!data) return <Loading locale={locale} error={error} />;
  const numericalContext = referenceResult(data, assertions, engineTarget);
  return (
    <>
      <div className="reference-heading">
        <div>
          <span className="section-kicker">REFERENCE MODEL</span>
          <h2>{t.reference}</h2>
        </div>
        <span className="model-size">
          {data.model.coordinate_system.dimension.toUpperCase()} · {data.model.nodes.length}{' '}
          {t.nodes} · {data.model.elements.length} {t.elements}
        </span>
      </div>
      <Suspense fallback={<Loading locale={locale} />}>
        <Scene
          key={id}
          model={data.model}
          locale={locale}
          name={id}
          attachment={attachment}
          resultPick={pick}
          resultContext={`${numericalContext.engine} / ${numericalContext.caseName || '—'}`}
        />
      </Suspense>
      <div className="reference-caption">
        <code>{id}</code>
        <span>
          {data.model.coordinate_system.semantics} · {data.model.coordinate_system.plane || 'xyz'} ·{' '}
          {data.model.unit_system}
        </span>
      </div>
      <section className="reference-results">
        <h2>{t.results}</h2>
        <div
          className="answer-summary"
          aria-label={locale === 'zh' ? '标答摘要' : 'Reference summary'}
        >
          <div>
            <span>{locale === 'zh' ? '模型规模' : 'Model size'}</span>
            <strong>
              {data.model.nodes.length} {t.nodes} / {data.model.elements.length} {t.elements}
            </strong>
          </div>
          <div>
            <span>{locale === 'zh' ? '约束节点' : 'Restrained nodes'}</span>
            <strong>{data.model.nodes.filter((n) => n.restraints?.some(Boolean)).length}</strong>
          </div>
          <div>
            <span>{t.loadCase}</span>
            <strong>{data.model.load_cases.map((c) => c.id).join(' · ')}</strong>
          </div>
          <div>
            <span>
              {locale === 'zh' ? '模型外包尺寸（X × Y × Z）' : 'Model extents (X × Y × Z)'}
            </span>
            <strong>
              {(['x', 'y', 'z'] as const)
                .map((axis) =>
                  formatNumber(
                    Math.max(...data.model.nodes.map((n) => n[axis])) -
                      Math.min(...data.model.nodes.map((n) => n[axis])),
                  ),
                )
                .join(' × ')}{' '}
              {data.model.unit_system === 'SI' ? 'm' : ''}
            </strong>
          </div>
        </div>
        <Numbers
          reference={data}
          assertions={assertions}
          engineTarget={engineTarget}
          locale={locale}
          onPick={setPick}
          pick={pick}
        />
      </section>
      <ResultLab
        reference={data}
        assertions={assertions}
        engineTarget={engineTarget}
        locale={locale}
        pick={pick}
        onPick={setPick}
      />
      <details className="paper-workbench">
        <summary>
          {locale === 'zh' ? '论文图版 · 建模证据链' : 'Paper figures · Modeling evidence chain'}
        </summary>
        <EvidenceFigure
          reference={data}
          locale={locale}
          input={input}
          assertions={assertions}
          engineTarget={engineTarget}
        />
      </details>
      <details className="wide-details">
        <summary>{t.parameters}</summary>
        <p className="note">{t.unitNote}</p>
        {(
          [
            [
              t.geometry,
              {
                nodes: data.model.nodes,
                elements: data.model.elements,
                coordinate_system: data.model.coordinate_system,
              },
            ],
            [t.materials, data.model.materials],
            [t.sections, data.model.sections],
            [t.loadDetails, data.model.load_cases],
            [t.combinations, data.model.load_combinations],
            [t.stories, data.model.stories || []],
          ] as [string, unknown][]
        ).map(([name, value]) => (
          <details key={name}>
            <summary>{name}</summary>
            <Json value={value} />
          </details>
        ))}
        <button className="text-button" onClick={() => downloadJson(data.model, `${id}.json`)}>
          {t.download} · JSON ↓
        </button>
      </details>
    </>
  );
}
function Detail({ item, index, locale }: { item: CaseSummary; index: Index; locale: Locale }) {
  const { data, error } = useData<CaseDetail>(`cases/${item.id}.json`);
  const t = words[locale];
  const [turnIndex, setTurnIndex] = useState(() => initialIndex('turn', item.turnCount)),
    [modelIndex, setModelIndex] = useState(() =>
      initialIndex('model', item.referenceIds.length || 1),
    );
  const [share, setShare] = useState('');
  const position = index.cases.findIndex((c) => c.id === item.id);
  if (!data) return <Loading locale={locale} error={error} />;
  const turn = data.turns[turnIndex],
    references = data.references[turnIndex];
  const selectedModel = Math.min(modelIndex, Math.max(0, references.length - 1));
  const originalSpec = turn.engineeringSpecification || data.scenario.engineeringSpecification;
  return (
    <article className="detail">
      <nav className="breadcrumb">
        <a href={sessionStorage.getItem('explorer-library') || '#/'}>← {t.back}</a>
        <div>
          {position > 0 && (
            <a aria-label={t.prev} href={`#/case/${index.cases[position - 1].id}`}>
              ← {t.prev}
            </a>
          )}
          <span>
            {position + 1} / {index.cases.length}
          </span>
          {position < index.cases.length - 1 && (
            <a aria-label={t.next} href={`#/case/${index.cases[position + 1].id}`}>
              {t.next} →
            </a>
          )}
        </div>
      </nav>
      <header className="detail-title">
        <div className="eyebrow">{label(familyNames, item.family, locale)}</div>
        <h1>{item.description}</h1>
        <div className="detail-meta">
          <code>{item.id}</code>
          <Tags item={item} locale={locale} />
          <button
            className="share-view"
            onClick={async () => {
              saveViewState({ turn: turnIndex, model: selectedModel });
              try {
                await navigator.clipboard.writeText(location.href);
                setShare(locale === 'zh' ? '链接已复制' : 'Link copied');
              } catch {
                setShare(location.href);
              }
            }}
          >
            {locale === 'zh' ? '分享当前查看状态 ↗' : 'Share this view ↗'}
          </button>
          {share && <output className="share-status">{share}</output>}
        </div>
      </header>
      {data.turns.length > 1 && (
        <div className="turn-tabs" role="group" aria-label={t.turn}>
          {data.turns.map((_, i) => (
            <button
              key={i}
              aria-pressed={i === turnIndex}
              onClick={() => {
                setTurnIndex(i);
                setModelIndex(0);
                saveViewState({ turn: i, model: 0, camera: null, load: null });
                setShare('');
              }}
            >
              <span>{String(i + 1).padStart(2, '0')}</span>
              {t.turn} {i + 1}
            </button>
          ))}
        </div>
      )}
      <TaskFlow data={data} locale={locale} />
      <div className={`detail-layout ${data.scenario.attachments?.length ? 'with-drawing' : ''}`}>
        <aside className="input-panel">
          <div className="panel-title">
            <span className="section-kicker">{t.native}</span>
            <h2>{t.input}</h2>
          </div>
          <p className="task-text">{turn.message}</p>
          {originalSpec && (
            <details className="spec-details">
              <summary>{t.spec}</summary>
              <p className="spec-text">{originalSpec}</p>
            </details>
          )}
          {data.scenario.inputContract && (
            <details>
              <summary>{locale === 'zh' ? '输入信息约定' : 'Input contract'}</summary>
              <Json value={data.scenario.inputContract} />
            </details>
          )}
          {!!data.scenario.attachments?.length && (
            <section className="attachments">
              <h3>{t.attachments}</h3>
              {data.scenario.attachments.map((a) => (
                <div className="attachment" key={a.relPath}>
                  {a.mimeType.startsWith('image/') ? (
                    <ImagePreview src={dataUrl(a.relPath)} name={a.originalName} locale={locale} />
                  ) : (
                    <DrawingPreview path={a.relPath} locale={locale} />
                  )}
                  <div className="attachment-label">
                    <span>{a.originalName}</span>
                    <a
                      href={dataUrl(a.relPath)}
                      download={a.originalName}
                      aria-label={`${t.download}: ${a.originalName}`}
                    >
                      ↓
                    </a>
                  </div>
                </div>
              ))}
            </section>
          )}
          <p className="source-language">
            {t.original} · {item.locale === 'zh' ? '中文' : 'English'}
          </p>
        </aside>
        <div className="answer-panel">
          {references.length > 1 && (
            <label>
              {t.chooseModel}
              <select
                value={selectedModel}
                onChange={(e) => {
                  setModelIndex(Number(e.target.value));
                  saveViewState({ model: Number(e.target.value), camera: null, load: null });
                  setShare('');
                }}
              >
                {references.map((id, i) => (
                  <option key={id} value={i}>
                    {id}
                  </option>
                ))}
              </select>
            </label>
          )}
          {references.length ? (
            <ReferencePanel
              input={turn.message}
              key={`${turnIndex}-${references[selectedModel]}`}
              id={references[selectedModel]}
              assertions={turn.assertions}
              engineTarget={data.scenario.analysisEngineTarget}
              locale={locale}
              attachment={data.scenario.attachments?.[0]}
            />
          ) : (
            <div className="behavior-answer">
              <div className="behavior-illustration">
                <Thumbnail />
              </div>
              <span className="section-kicker">EXPECTED BEHAVIOR</span>
              <h2>{t.noModel}</h2>
              <p>{t.noModelHint}</p>
            </div>
          )}
          <section className="expected-panel">
            <h2>{t.expected}</h2>
            <Requirements assertions={turn.assertions} locale={locale} />
            <details>
              <summary>{t.criteria}</summary>
              <Json value={turn.assertions} />
            </details>
          </section>
        </div>
      </div>
      <details className="provenance">
        <summary>{t.source}</summary>
        <p>{t.sourceNote}</p>
        <dl>
          <dt>{t.version}</dt>
          <dd>{index.corpus.benchmarkVersion}</dd>
          <dt>{t.source}</dt>
          <dd>
            <code>{data.source}</code>
          </dd>
          <dt>SHA-256</dt>
          <dd>
            <code>{data.sourceSha256}</code>
          </dd>
        </dl>
        <button
          className="text-button"
          onClick={() => downloadJson(data.scenario, `${item.id}.json`)}
        >
          {t.download} · JSON ↓
        </button>
        <details>
          <summary>{t.raw}</summary>
          <Json value={data.scenario} />
        </details>
        <details>
          <summary>{locale === 'zh' ? '参考文件指纹' : 'Reference file fingerprints'}</summary>
          <Json
            value={index.sources.filter(
              (s) =>
                s.source.startsWith('fixtures/') &&
                (s.source.endsWith('.json') ||
                  data.scenario.attachments?.some((a) => a.relPath === s.source)),
            )}
          />
        </details>
      </details>
    </article>
  );
}
function App() {
  const [locale, setLocale] = useState<Locale>(() =>
    localStorage.getItem('explorer-locale') === 'en' ? 'en' : 'zh',
  );
  const [route, setRoute] = useState(location.hash);
  const { data: index, error } = useData<Index>('index.json');
  const { data: thumbnails, error: thumbError } =
    useData<Record<string, Geometry>>('thumbnails.json');
  const t = words[locale];
  useEffect(() => {
    const change = () => {
      setRoute(location.hash);
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  useEffect(() => {
    localStorage.setItem('explorer-locale', locale);
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
  }, [locale]);
  let caseId = '';
  try {
    caseId = route.startsWith('#/case/') ? decodeURIComponent(route.slice(7).split('?')[0]) : '';
  } catch {
    caseId = '__invalid__';
  }
  const item = index?.cases.find((c) => c.id === caseId);
  useEffect(() => {
    document.title = `${item ? item.description + ' · ' : ''}StructureClaw Benchmark`;
  }, [item]);
  return (
    <>
      <header className="site-header">
        <a href="#/" className="brand">
          <img src="./mark.svg" alt="" />
          <span>
            StructureClaw<span className="brand-sub">Benchmark Explorer</span>
          </span>
        </a>
        <div className="header-actions">
          <a href="#/">{t.library}</a>
          <span className="header-divider" />
          <div className="language-switch" role="group" aria-label="Language / 语言">
            <button aria-pressed={locale === 'zh'} onClick={() => setLocale('zh')}>
              中
            </button>
            <button aria-pressed={locale === 'en'} onClick={() => setLocale('en')}>
              EN
            </button>
          </div>
        </div>
      </header>
      <main>
        {!index || !thumbnails ? (
          <Loading locale={locale} error={error || thumbError} />
        ) : caseId ? (
          item ? (
            <Detail key={caseId} item={item} index={index} locale={locale} />
          ) : (
            <div className="empty">
              <h1>{t.notFound}</h1>
              <a href="#/">{t.back}</a>
            </div>
          )
        ) : (
          <Library
            key={route.startsWith('#/case/') ? 'detail' : 'library'}
            index={index}
            thumbnails={thumbnails}
            locale={locale}
          />
        )}
      </main>
      <footer className="site-footer">
        <span>
          StructureClaw <span className="muted">/ Benchmark</span>
        </span>
        <span>{t.footer}</span>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        >
          {t.top} ↑
        </a>
      </footer>
    </>
  );
}
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: boolean }> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <div className="loading">
        <p>页面加载失败 / Unable to display this page</p>
        <button onClick={() => location.reload()}>重新加载 / Reload</button>
      </div>
    ) : (
      this.props.children
    );
  }
}
createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
