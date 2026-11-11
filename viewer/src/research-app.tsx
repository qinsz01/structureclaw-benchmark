import { useEffect, useMemo, useState } from 'react';
import type { Geometry, Locale } from './types';
import type {
  ResearchCaseSummary,
  ResearchCatalogueChoice,
  ResearchCatalogueFacet,
  ResearchCatalogueRow,
  ResearchIndex,
} from './research-types';
import { fetchData } from './data';
import { Thumbnail } from './thumbnail';
import { ResearchDetail } from './research-detail';
import { ResearchComposition } from './research-composition';
import {
  catalogueHash,
  familyLabel,
  filterResearchCases,
  readCatalogueLocation,
} from './research-catalogue';
import type { CatalogueFilters } from './research-catalogue';
import { TrialOverview, TrialBadge } from './trial-view';

export { familyLabel } from './research-catalogue';

function Catalogue({
  index,
  thumbnails,
  locale,
  maintainerMode,
}: {
  index: ResearchIndex;
  thumbnails: Record<string, Geometry>;
  locale: Locale;
  maintainerMode: boolean;
}) {
  const z = locale === 'zh';
  const initial = readCatalogueLocation(location.hash);
  const [filters, setFilters] = useState(initial.filters);
  const [page, setPage] = useState(initial.page);
  const { query, family, language, engine } = filters;
  const extraFields: [ResearchCatalogueFacet, string, string][] = [
    [
      'category',
      z ? '能力子类' : 'Capability subgroup',
      z ? '全部能力子类' : 'All capability subgroups',
    ],
    ['structure', z ? '结构类型' : 'Structure', z ? '全部结构' : 'All structures'],
    ['dimension', z ? '模型维度' : 'Dimension', z ? '全部维度' : 'All dimensions'],
    ['difficulty', z ? '预设难度' : 'Preset difficulty', z ? '全部难度' : 'All difficulty levels'],
    ['modality', z ? '输入模态' : 'Input modality', z ? '全部模态' : 'All modalities'],
  ];
  const activeExtraFilters = extraFields.filter(([key]) => filters[key]).length;
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(activeExtraFilters > 0);
  const filtered = useMemo(
    () => filterResearchCases(index, filters, locale),
    [index, filters, locale],
  );
  const rows = useMemo(
    () => new Map(index.catalogue?.cases.map((row) => [row.id, row])),
    [index.catalogue],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / 12));
  const currentPage = Math.min(page, pages);
  useEffect(() => {
    const hash = catalogueHash(filters, currentPage);
    history.replaceState(null, '', hash);
    sessionStorage.setItem('research-catalogue', hash);
  }, [filters, currentPage]);
  const setFilter = (key: keyof CatalogueFilters, value: string) => {
    setFilters((current) => ({
      ...current,
      [key]: value,
      ...(key === 'family' ? { category: '' } : {}),
    }));
    setPage(1);
  };
  const clear = () => {
    setFilters(readCatalogueLocation('#/').filters);
    setPage(1);
  };
  const inputReview = index.summary.publicInputReview;
  const maintainerStats: [string, number, string][] = [
    ['nativeVerified', index.summary.nativeVerified, z ? '原生求解已核验' : 'Native verified'],
    inputReview
      ? [
          'currentInputReviewed',
          inputReview.passed,
          z ? '当前输入盲审通过' : 'Current inputs passed',
        ]
      : ['inputReviewed', index.summary.inputReviewed, z ? '输入盲审已完成' : 'Input reviewed'],
    ['accepted', index.summary.accepted, z ? '最终验收' : 'Accepted'],
    [
      'agentNotRun',
      index.summary.agentNotRun,
      z ? 'StructureClaw 正式试验待运行' : 'StructureClaw formal trials not run',
    ],
  ];
  const totals = index.catalogue?.totals;
  const stats: [string, number, string][] = [
    ['cases', totals?.cases ?? index.cases.length, z ? '题目' : 'Cases'],
    ['turns', totals?.turns ?? index.summary.turns, z ? '对话轮次' : 'Turns'],
    ['states', totals?.states ?? index.summary.states, z ? '物理状态' : 'Physical states'],
    ...(totals
      ? [
          ['attachmentFiles', totals.attachmentFiles, z ? '输入文件' : 'Input files'] as [
            string,
            number,
            string,
          ],
        ]
      : []),
    ...(maintainerMode ? maintainerStats : []),
  ];
  return (
    <>
      <section className="research-hero">
        <div className="research-hero-copy">
          <span className="research-eyebrow">STRUCTURECLAW / RESEARCH CORPUS</span>
          <h1>Research 300</h1>
          <p>
            {z
              ? '逐轮查看工程题目、Codex 作答与评测结果。'
              : 'Explore engineering tasks, Codex answers, and evaluation results turn by turn.'}
          </p>
          <div className="research-hero-meta">
            <span>OpenSees · PKPM · YJK</span>
            <span>{z ? '中文与英文' : 'Chinese & English'}</span>
            {maintainerMode && <span>{index.evaluatorVersion}</span>}
          </div>
        </div>
        <div className="research-hero-art" aria-hidden="true">
          <span>MODEL / MM-082 · s1</span>
          <Thumbnail model={thumbnails['MM-082-s1']} />
          <div>
            <span>+X / +Y / +Z</span>
            <span>{z ? '基准参考几何' : 'BENCHMARK REFERENCE'}</span>
          </div>
        </div>
      </section>
      <section
        className={`research-stats${totals ? ' research-stats-with-files' : ''}${maintainerMode ? ' research-stats-maintainer' : ''}`}
        aria-label={z ? '基准规模' : 'Benchmark size'}
      >
        {stats.map(([key, value, label]) => (
          <div key={key} data-summary={key}>
            <b>{value}</b>
            <span>{label}</span>
          </div>
        ))}
      </section>
      {maintainerMode && (
        <p className="research-status-note">
          {z
            ? '300 例已编制、参考已就绪。原生求解核验、输入盲审、最终验收与模型试验是独立阶段。'
            : 'All 300 cases are authored and reference-ready. Native verification, blind input review, acceptance, and model trials are separate stages.'}
        </p>
      )}
      {maintainerMode && inputReview && (
        <p className="research-status-note" data-summary="publicInputReview">
          {z
            ? `当前公开输入：${inputReview.total} 题，盲审通过 ${inputReview.passed}，部分重建 ${inputReview.partial}，比对未通过 ${inputReview.failed}，待审 ${inputReview.pending}，证据失效 ${inputReview.invalid}。`
            : `Current public inputs: ${inputReview.total} cases; ${inputReview.passed} passed, ${inputReview.partial} partial reconstructions, ${inputReview.failed} failed comparisons, ${inputReview.pending} pending, ${inputReview.invalid} invalid records.`}
        </p>
      )}
      {index.codexTrial && (
        <TrialOverview
          trial={index.codexTrial}
          locale={locale}
          onFilter={(value) => setFilter('trial', value)}
        />
      )}
      {index.catalogue && <ResearchComposition catalogue={index.catalogue} locale={locale} />}
      <section className="research-catalogue" aria-label={z ? '案例目录' : 'Case catalogue'}>
        <div className="research-section-heading">
          <div>
            <span className="research-eyebrow">EXPLORE / 001—300</span>
            <h2>{z ? '案例目录' : 'Case catalogue'}</h2>
          </div>
          <div className="research-catalogue-actions">
            <a
              className="research-text-link"
              href={`${import.meta.env.BASE_URL}benchmark-inputs.zip`}
              download
            >
              {z ? '下载题目包' : 'Download tasks'} ↓
            </a>
            {index.catalogue && (
              <span className="research-catalogue-downloads">
                <a
                  className="research-text-link"
                  href={`${import.meta.env.BASE_URL}data/benchmark-catalogue.xlsx`}
                  download
                  aria-label={z ? '下载分类目录 Excel' : 'Download catalogue Excel'}
                >
                  Excel ↓
                </a>
                <a
                  className="research-text-link"
                  href={`${import.meta.env.BASE_URL}data/catalogue.json`}
                  download
                  aria-label={z ? '下载分类目录 JSON' : 'Download catalogue JSON'}
                >
                  JSON ↓
                </a>
              </span>
            )}
            <span className="result-count">
              <b>{filtered.length}</b> / {totals?.cases ?? index.cases.length} {z ? '题' : 'cases'}
            </span>
          </div>
        </div>
        <div className="research-filters">
          <label className="research-search">
            <span>{z ? '搜索案例' : 'Search cases'}</span>
            <input
              type="search"
              value={query}
              placeholder={z ? '编号、题目、结构或模态…' : 'ID, task, structure, or modality…'}
              onChange={(e) => setFilter('query', e.target.value)}
            />
          </label>
          <label>
            <span>{z ? '任务大类' : 'Family'}</span>
            <select value={family} onChange={(e) => setFilter('family', e.target.value)}>
              <option value="">{z ? '全部任务大类' : 'All families'}</option>
              {Object.keys(index.summary.byFamily).map((f) => (
                <option key={f} value={f}>
                  {familyLabel(f, locale)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>{z ? '输入语言' : 'Input language'}</span>
            <select value={language} onChange={(e) => setFilter('language', e.target.value)}>
              <option value="">{z ? '全部语言' : 'All languages'}</option>
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </label>
          <label>
            <span>{z ? '求解器' : 'Engine'}</span>
            <select value={engine} onChange={(e) => setFilter('engine', e.target.value)}>
              <option value="">{z ? '全部求解器' : 'All engines'}</option>
              {Object.keys(index.summary.byEngine).map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <button className="research-clear" onClick={clear}>
            {z ? '清除筛选' : 'Clear filters'}
          </button>
          {index.codexTrial && (
            <label>
              <span>{z ? 'Codex 结果' : 'Codex result'}</span>
              <select
                value={filters.trial || ''}
                onChange={(e) => setFilter('trial', e.target.value)}
              >
                <option value="">{z ? '全部实测结果' : 'All trial results'}</option>
                <option value="passed">{z ? '历史通过' : 'Historical pass'}</option>
                <option value="not-passed">{z ? '历史未通过' : 'Historical failure'}</option>
                <option value="repaired">{z ? '另有修复验证' : 'Separate repair check'}</option>
              </select>
            </label>
          )}
          {index.catalogue && (
            <details
              className="research-more-filters"
              open={moreFiltersOpen}
              onToggle={(event) => setMoreFiltersOpen(event.currentTarget.open)}
            >
              <summary>
                {z ? '更多筛选' : 'More filters'}
                {activeExtraFilters > 0 && (
                  <span>{z ? `${activeExtraFilters} 项已选` : `${activeExtraFilters} active`}</span>
                )}
              </summary>
              <div className="research-extra-filter-grid">
                {extraFields.map(([key, label, all]) => (
                  <label key={key}>
                    <span>{label}</span>
                    <select
                      value={filters[key]}
                      onChange={(event) => setFilter(key, event.target.value)}
                    >
                      <option value="">{all}</option>
                      {index
                        .catalogue!.definitions[key].filter(
                          (choice) => key !== 'category' || !family || choice.family === family,
                        )
                        .map((choice) => (
                          <option key={choice.key} value={choice.key} title={choice.description}>
                            {key === 'category' && !family && choice.family
                              ? `${familyLabel(choice.family, locale)} · `
                              : ''}
                            {choice[locale]}
                          </option>
                        ))}
                    </select>
                  </label>
                ))}
              </div>
              <p className="research-filter-note">
                {z
                  ? '难度为题目预设分档，可与其他条件组合筛选。'
                  : 'Preset difficulty describes the task and can be combined with every other filter.'}
              </p>
            </details>
          )}
        </div>
        {filtered.length ? (
          <div className="research-case-grid">
            {filtered.slice((currentPage - 1) * 12, currentPage * 12).map((item) => (
              <CaseCard
                key={item.id}
                item={item}
                model={thumbnails[`${item.id}-s1`]}
                locale={locale}
                maintainerMode={maintainerMode}
                catalogueRow={rows.get(item.id)}
                modalityChoice={index.catalogue?.definitions.modality.find(
                  (choice) => choice.key === rows.get(item.id)?.modality,
                )}
              />
            ))}
          </div>
        ) : (
          <div className="research-empty">
            <h3>{z ? '未找到匹配案例' : 'No matching cases'}</h3>
            <p>
              {z ? '调整搜索词或筛选条件。' : 'Adjust the search or filters to explore the corpus.'}
            </p>
          </div>
        )}
        <nav className="pagination" aria-label={z ? '目录分页' : 'Catalogue pages'}>
          <button
            disabled={currentPage === 1}
            onClick={() => setPage(currentPage - 1)}
            aria-label={z ? '上一页' : 'Previous page'}
          >
            ← {z ? '上一页' : 'Previous'}
          </button>
          <span>
            {currentPage} / {pages}
          </span>
          <button
            disabled={currentPage === pages}
            onClick={() => setPage(currentPage + 1)}
            aria-label={z ? '下一页' : 'Next page'}
          >
            {z ? '下一页' : 'Next'} →
          </button>
        </nav>
      </section>
    </>
  );
}

function CaseCard({
  item,
  model,
  locale,
  maintainerMode,
  catalogueRow,
  modalityChoice,
}: {
  item: ResearchCaseSummary;
  model?: Geometry;
  locale: Locale;
  maintainerMode: boolean;
  catalogueRow?: ResearchCatalogueRow;
  modalityChoice?: ResearchCatalogueChoice;
}) {
  const z = locale === 'zh';
  return (
    <a href={`#/case/${item.id}`} className="case-card research-case-card">
      <div className="research-card-top">
        <code>{item.id}</code>
        <span className={`research-engine engine-${item.engine.toLowerCase()}`}>{item.engine}</span>
      </div>
      <div className="research-card-geometry">
        <Thumbnail model={model} />
        <span>{z ? '参考几何' : 'Reference geometry'}</span>
      </div>
      <div className="research-card-copy">
        {item.codexTrial && <TrialBadge {...item.codexTrial} locale={locale} />}
        <div className="research-card-family">{familyLabel(item.family, locale)}</div>
        <h3 title={item.description}>{item.description}</h3>
        <div className="research-card-tags">
          <span>{item.locale === 'zh' ? '中文' : 'English'}</span>
          <span>{modalityChoice?.[locale] || item.modality}</span>
          <span>
            {item.turnCount} {z ? '轮' : 'turns'}
          </span>
          <span>
            {item.stateCount} {z ? '状态' : 'states'}
          </span>
        </div>
      </div>
      <div className="research-card-bottom">
        {maintainerMode ? (
          <span>
            {item.status.nativeVerified
              ? z
                ? '● 原生已核验'
                : '● Native verified'
              : z
                ? '○ 原生待核验'
                : '○ Native pending'}
          </span>
        ) : (
          <span>
            {[item.structure, catalogueRow?.dimension, catalogueRow?.difficulty]
              .filter(Boolean)
              .join(' · ')}
          </span>
        )}
        {maintainerMode && item.strictComparison === 'difference' ? (
          <span className="research-difference">{z ? '严格比较差异' : 'Strict difference'}</span>
        ) : (
          <span aria-hidden="true">↗</span>
        )}
      </div>
    </a>
  );
}

export function ResearchApp() {
  const [locale, setLocale] = useState<Locale>(() =>
    localStorage.getItem('research-locale') === 'en' ? 'en' : 'zh',
  );
  const [hash, setHash] = useState(location.hash);
  const [maintainerMode, setMaintainerMode] = useState(
    () => localStorage.getItem('research-maintainer') === 'true',
  );
  const [index, setIndex] = useState<ResearchIndex>();
  const [thumbnails, setThumbnails] = useState<Record<string, Geometry>>({});
  const [error, setError] = useState(false);
  const z = locale === 'zh';
  useEffect(() => {
    const listener = () => setHash(location.hash);
    window.addEventListener('hashchange', listener);
    return () => window.removeEventListener('hashchange', listener);
  }, []);
  useEffect(() => {
    document.documentElement.lang = z ? 'zh-CN' : 'en';
    localStorage.setItem('research-locale', locale);
  }, [locale, z]);
  useEffect(() => {
    let active = true;
    Promise.all([
      fetchData<ResearchIndex>('index.json'),
      fetchData<Record<string, Geometry>>('thumbnails.json'),
    ])
      .then(([data, thumbs]) => {
        if (!active) return;
        if (data.corpusId !== 'research-300' || data.cases.length !== 300)
          throw new Error('Incorrect corpus');
        setIndex(data);
        setThumbnails(thumbs);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, []);
  const route = hash.split('?')[0];
  const caseMatch = /^#\/case\/([^/]+)$/.exec(route);
  const caseId = caseMatch?.[1];
  const missing =
    !!route && route !== '#/' && (!caseId || (index && !index.cases.some((c) => c.id === caseId)));
  return (
    <div className="research-app" data-mode={maintainerMode ? 'maintainer' : 'public'}>
      <header className="research-header">
        <a className="research-brand" href="#/">
          <img src="./mark.svg" alt="" />
          <span>
            StructureClaw<small>RESEARCH 300</small>
          </span>
        </a>
        <div className="research-header-actions">
          <a className="research-text-link" href={`${import.meta.env.BASE_URL}research300-v3/index.html`}>
            {z ? '工程综合版 v3' : 'Engineering edition v3'}
          </a>
          <span>{z ? '工程基准浏览器' : 'Engineering benchmark explorer'}</span>
          <button
            className="research-maintainer-toggle"
            aria-pressed={maintainerMode}
            onClick={() => {
              const enabled = !maintainerMode;
              setMaintainerMode(enabled);
              localStorage.setItem('research-maintainer', String(enabled));
            }}
          >
            {z ? '维护者模式' : 'Maintainer mode'}
          </button>
          <div className="language-switch" aria-label={z ? '界面语言' : 'Interface language'}>
            <button aria-pressed={z} onClick={() => setLocale('zh')}>
              中文
            </button>
            <button aria-pressed={!z} onClick={() => setLocale('en')}>
              EN
            </button>
          </div>
        </div>
      </header>
      <main className="research-main">
        {!index ? (
          <div role={error ? 'alert' : 'status'} className="research-loading">
            <h2>
              {error
                ? z
                  ? '研究语料加载失败'
                  : 'Research corpus unavailable'
                : z
                  ? '正在加载研究基准…'
                  : 'Loading the research corpus…'}
            </h2>
            {error && <button onClick={() => location.reload()}>{z ? '重试' : 'Retry'}</button>}
          </div>
        ) : missing ? (
          <div className="research-empty">
            <h1>{z ? '未找到案例' : 'Case not found'}</h1>
            <p>
              {z
                ? '请从 research-300 目录选择一个案例。'
                : 'Choose a case from the research-300 catalogue.'}
            </p>
            <a className="research-text-link" href="#/">
              {z ? '返回案例目录' : 'Back to catalogue'} →
            </a>
          </div>
        ) : caseId ? (
          <ResearchDetail
            key={caseId}
            id={caseId}
            locale={locale}
            hash={hash}
            evaluatorVersion={index.evaluatorVersion}
            maintainerMode={maintainerMode}
          />
        ) : (
          <Catalogue
            key={hash}
            index={index}
            thumbnails={thumbnails}
            locale={locale}
            maintainerMode={maintainerMode}
          />
        )}
      </main>
      <footer className="research-footer">
        <span>StructureClaw · research-300</span>
        <span>
          {z
            ? '结构工程任务 · 公开输入与参考结果'
            : 'Structural engineering tasks · Public inputs and reference results'}
        </span>
      </footer>
    </div>
  );
}
