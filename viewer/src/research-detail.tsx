import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import type { Locale, Raw } from './types';
import type {
  ResearchAttachment,
  ResearchCaseDetail,
  ResearchModel,
  ResearchState,
  ResearchStatus,
  ResearchTurn,
  SourceFile,
} from './research-types';
import { dataUrl, downloadJson, fetchData, formatNumber } from './data';
import DrawingPreview from './drawing';
import { ResearchResults } from './research-results';
import { PublicText } from './research-public-text';
import { visibleSupportRestraints } from './scene-loads';
import { publicInputForDownload } from './public-input';
import { publicModelForDownload } from './public-reference';
import { TrialPanel } from './trial-view';

const Scene = lazy(() => import('./scene'));
type Tab = 'input' | 'reference' | 'review' | 'codex';
const json = (value: unknown) => JSON.stringify(value, null, 2);
function Json({ value }: { value: unknown }) {
  return <pre className="research-json">{json(value)}</pre>;
}
function useData<T>(path: string | null) {
  const [result, setResult] = useState<{ path: string; data?: T; error?: boolean }>();
  useEffect(() => {
    let active = true;
    if (path)
      fetchData<T>(path).then(
        (data) => {
          if (active) setResult({ path, data });
        },
        () => {
          if (active) setResult({ path, error: true });
        },
      );
    return () => {
      active = false;
    };
  }, [path]);
  return result?.path === path ? result : undefined;
}
function readTurn(detail: ResearchCaseDetail, hash: string) {
  const params = new URLSearchParams(hash.split('?')[1]);
  const id = params.get('turn');
  const state = params.get('state');
  if (id) return detail.turns.find((turn) => turn.id === id);
  if (state) return detail.turns.find((turn) => String(turn.state) === state);
  return detail.turns[0];
}
function readTab(hash: string, maintainerMode: boolean): Tab {
  const tab = new URLSearchParams(hash.split('?')[1]).get('tab');
  return tab === 'codex' || tab === 'reference' || (tab === 'review' && maintainerMode)
    ? tab
    : 'input';
}
function updateLink(turn: ResearchTurn, tab: Tab) {
  const params = new URLSearchParams(location.hash.split('?')[1]);
  params.set('turn', turn.id);
  if (turn.state === null) {
    for (const key of ['state', 'camera', 'load', 'view', 'labels', 'loads', 'dims'])
      params.delete(key);
  } else params.set('state', String(turn.state));
  params.set('tab', tab);
  history.replaceState(null, '', `${location.hash.split('?')[0]}?${params}`);
}

export function ResearchDetail({
  id,
  locale,
  hash,
  evaluatorVersion,
  maintainerMode,
}: {
  id: string;
  locale: Locale;
  hash: string;
  evaluatorVersion: string;
  maintainerMode: boolean;
}) {
  const result = useData<ResearchCaseDetail>(`cases/${id}.json`);
  const z = locale === 'zh';
  if (!result?.data)
    return (
      <div className="research-loading" role={result?.error ? 'alert' : 'status'}>
        {result?.error
          ? z
            ? '案例加载失败，请重新加载。'
            : 'Unable to load the case. Reload to retry.'
          : z
            ? '正在读取案例…'
            : 'Loading case…'}
      </div>
    );
  return (
    <DetailContent
      key={hash}
      detail={result.data}
      locale={locale}
      hash={hash}
      evaluatorVersion={evaluatorVersion}
      maintainerMode={maintainerMode}
    />
  );
}

function DetailContent({
  detail,
  locale,
  hash,
  evaluatorVersion,
  maintainerMode,
}: {
  detail: ResearchCaseDetail;
  locale: Locale;
  hash: string;
  evaluatorVersion: string;
  maintainerMode: boolean;
}) {
  const z = locale === 'zh';
  const [turnId, setTurnId] = useState(() => readTurn(detail, hash)?.id);
  const [tab, setTab] = useState<Tab>(() => readTab(hash, maintainerMode));
  const [copied, setCopied] = useState(false);
  const [shareError, setShareError] = useState(false);
  const turn = detail.turns.find((item) => item.id === turnId);
  const activeTab =
    (turn?.state === null && tab === 'reference') || (!maintainerMode && tab === 'review')
      ? 'input'
      : tab;
  const state =
    turn?.state == null ? undefined : detail.states.find((item) => item.state === turn.state);
  useEffect(() => {
    if (turn) updateLink(turn, activeTab);
  }, [turn, activeTab]);
  const catalogue = sessionStorage.getItem('research-catalogue') || '#/';
  const changeTurn = (next: ResearchTurn) => {
    if (turn?.state !== next.state) {
      const params = new URLSearchParams(location.hash.split('?')[1]);
      params.delete('camera');
      params.delete('load');
      history.replaceState(null, '', `${location.hash.split('?')[0]}?${params}`);
    }
    setTurnId(next.id);
    if (next.state === null && tab === 'reference') setTab('input');
    setCopied(false);
    setShareError(false);
  };
  const tabs: [Tab, string][] = [
    ['input', z ? '公开输入' : 'Public input'],
    ['reference', z ? '基准参考' : 'Benchmark reference'],
    ['codex', z ? 'Codex 作答与评测' : 'Codex answer & evaluation'],
    ...(maintainerMode
      ? [['review', z ? '核验与来源' : 'Review & provenance'] as [Tab, string]]
      : []),
  ];
  return (
    <article className="research-detail" data-case-id={detail.id}>
      <div className="research-breadcrumb">
        <a href={catalogue}>← {z ? '返回案例目录' : 'Back to catalogue'}</a>
        <code>{detail.id}</code>
        <button
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(location.href);
              setCopied(true);
              setShareError(false);
            } catch {
              setShareError(true);
            }
          }}
        >
          {copied ? (z ? '链接已复制' : 'Link copied') : z ? '复制当前轮链接' : 'Copy turn link'}
        </button>
      </div>
      {shareError && (
        <p role="status" className="research-note">
          {z
            ? '请复制浏览器地址栏中的当前链接。'
            : 'Copy the current link from the browser address bar.'}
        </p>
      )}
      <header className="detail-title research-detail-title">
        <div className="research-eyebrow">
          {detail.id} / {detail.family.replaceAll('_', ' ')}
        </div>
        <h1>{detail.description}</h1>
        <div className="research-detail-meta">
          <span className={`research-engine engine-${detail.engine.toLowerCase()}`}>
            {detail.engine}
          </span>
          <span>{detail.locale === 'zh' ? '中文输入' : 'English input'}</span>
          <span>
            {detail.turns.length} {z ? '轮对话' : 'turns'} · {detail.states.length}{' '}
            {z ? '物理状态' : 'physical states'}
          </span>
          {maintainerMode && (
            <span>
              {z ? '冻结评测' : 'Frozen evaluator'}: {evaluatorVersion}
            </span>
          )}
        </div>
      </header>
      <nav
        className="turn-tabs research-turn-tabs"
        aria-label={z ? '对话轮次' : 'Conversation turns'}
      >
        {detail.turns.map((item, index) => (
          <button
            key={item.id}
            data-turn-id={item.id}
            aria-pressed={item.id === turnId}
            onClick={() => changeTurn(item)}
          >
            <span>
              {z ? '第' : 'Turn'} {index + 1}
              {z ? '轮' : ''}
            </span>
            {maintainerMode && (
              <small>
                {item.expectation} ·{' '}
                {item.state === null ? (z ? '待澄清' : 'no state') : `s${item.state}`}
              </small>
            )}
          </button>
        ))}
      </nav>
      {!turn ? (
        <div className="research-empty">
          <h2>{z ? '未找到请求的轮次' : 'Requested turn not found'}</h2>
          <p>{z ? '请从上方选择有效轮次。' : 'Select a valid turn above.'}</p>
        </div>
      ) : (
        <>
          {maintainerMode && (
            <div className="turn-identity" data-state={String(turn.state)}>
              <code>
                {detail.id} / {turn.id}
              </code>
              <span>
                {turn.state === null
                  ? z
                    ? '此轮没有可分析状态'
                    : 'No analyzable state in this turn'
                  : `${z ? '物理状态' : 'Physical state'} ${turn.state}`}
              </span>
              <span>{turn.expectation}</span>
            </div>
          )}
          <div
            className="research-detail-tabs"
            role="tablist"
            aria-label={z ? '查看内容' : 'Case views'}
          >
            {tabs.map(([key, label]) => (
              <button
                key={key}
                role="tab"
                id={`tab-${key}`}
                aria-controls={`panel-${key}`}
                aria-selected={activeTab === key}
                disabled={key === 'reference' && turn.state === null}
                onClick={() => setTab(key)}
              >
                {label}
              </button>
            ))}
          </div>
          <section
            id={`panel-${activeTab}`}
            role="tabpanel"
            aria-labelledby={`tab-${activeTab}`}
            className="research-tab-panel"
          >
            {activeTab === 'codex' && (
              <TrialPanel key={detail.id} caseId={detail.id} turnId={turn.id} locale={locale} />
            )}
            {activeTab === 'input' && (
              <PublicInput key={turn.id} detail={detail} turn={turn} locale={locale} />
            )}
            {activeTab === 'reference' && state && (
              <StateReference
                key={`${detail.id}-${turn.id}`}
                detail={detail}
                state={state}
                turn={turn}
                locale={locale}
                maintainerMode={maintainerMode}
              />
            )}
            {activeTab === 'reference' && !state && (
              <p role="alert">
                {z ? '此轮参考状态不可用。' : 'The reference state for this turn is unavailable.'}
              </p>
            )}
            {maintainerMode && activeTab === 'review' && (
              <Review
                detail={detail}
                turn={turn}
                locale={locale}
                evaluatorVersion={evaluatorVersion}
              />
            )}
          </section>
        </>
      )}
    </article>
  );
}

function PublicInput({
  detail,
  turn,
  locale,
}: {
  detail: ResearchCaseDetail;
  turn: ResearchTurn;
  locale: Locale;
}) {
  const z = locale === 'zh';
  return (
    <div className="research-input-view">
      <section className="research-panel research-instruction">
        <div className="research-panel-heading">
          <h2>{z ? '本轮指令' : 'Turn instruction'}</h2>
          <button
            onClick={() =>
              downloadJson(
                publicInputForDownload(detail.id, turn),
                `${detail.id}-${turn.id}-public-input.json`,
              )
            }
          >
            {z ? '下载公开输入 JSON' : 'Download public input JSON'}
          </button>
        </div>
        <PublicText className="task-text" lang={detail.locale} text={turn.instruction} />
      </section>
      <section className="research-attachments">
        <div className="research-section-heading">
          <h2>{z ? '本轮公开附件' : 'Public attachments for this turn'}</h2>
          <span>
            {turn.attachments.length} {z ? '个文件' : 'files'}
          </span>
        </div>
        {turn.attachments.length ? (
          turn.attachments.map((attachment, index) => (
            <Attachment
              key={attachment.path}
              attachment={attachment}
              locale={locale}
              first={index === 0}
            />
          ))
        ) : (
          <p className="research-note">
            {z
              ? '此轮没有新增附件；请按对话历史使用此前公开输入。'
              : 'No new attachments in this turn. Earlier public inputs remain in the conversation history.'}
          </p>
        )}
      </section>
    </div>
  );
}

function Attachment({
  attachment,
  locale,
  first,
}: {
  attachment: ResearchAttachment;
  locale: Locale;
  first: boolean;
}) {
  const z = locale === 'zh';
  const dxf = /\.dxf$/i.test(attachment.name);
  const image = !dxf && attachment.mimeType.startsWith('image/');
  const text = !image && !dxf;
  const [open, setOpen] = useState(image || dxf || first);
  const [contents, setContents] = useState<string>();
  const [error, setError] = useState(false);
  const modal = useRef<HTMLDialogElement>(null);
  const imageViewport = useRef<HTMLDivElement>(null);
  const fullImage = useRef<HTMLImageElement>(null);
  const [imageZoom, setImageZoom] = useState(0);
  const zoomImage = (factor: number) => {
    const img = fullImage.current;
    if (!img?.naturalWidth) return;
    const current = imageZoom || img.getBoundingClientRect().width / img.naturalWidth;
    setImageZoom(Math.min(4, Math.max(0.02, current * factor)));
  };
  useEffect(() => {
    let active = true;
    if (open && text && contents === undefined)
      fetch(dataUrl(attachment.path))
        .then((response) => {
          if (!response.ok) throw new Error('Attachment unavailable');
          return response.text();
        })
        .then((value) => {
          if (active) setContents(value);
        })
        .catch(() => {
          if (active) setError(true);
        });
    return () => {
      active = false;
    };
  }, [open, text, contents, attachment.path]);
  return (
    <div className="research-attachment" data-name={attachment.name}>
      <div className="research-attachment-heading">
        <button aria-expanded={open} onClick={() => setOpen(!open)}>
          <span aria-hidden="true">{open ? '−' : '+'}</span>
          <strong>{attachment.name}</strong>
          <small>{(attachment.bytes / 1024).toFixed(1)} KB</small>
        </button>
        <a href={dataUrl(attachment.path)} download={attachment.name}>
          {z ? '下载' : 'Download'} ↓
        </a>
      </div>
      {open && (
        <div className="research-attachment-body">
          {image ? (
            <>
              <button
                className="attachment-image"
                aria-label={`${z ? '放大' : 'Enlarge'} ${attachment.name}`}
                onClick={() => {
                  setImageZoom(0);
                  modal.current?.showModal();
                  imageViewport.current?.scrollTo(0, 0);
                }}
              >
                <img src={dataUrl(attachment.path)} alt={attachment.name} />
                <span>{z ? '点击放大' : 'Click to enlarge'} ↗</span>
              </button>
              <dialog
                className="research-image-dialog"
                ref={modal}
                aria-label={attachment.name}
                onClick={(e) => {
                  if (e.target === e.currentTarget) modal.current?.close();
                }}
              >
                <div className="research-image-dialog-header">
                  <strong>{attachment.name}</strong>
                  <div className="research-image-tools">
                    <button
                      aria-label={z ? '缩小图片' : 'Zoom out image'}
                      onClick={() => zoomImage(1 / 1.5)}
                    >
                      −
                    </button>
                    <button
                      aria-label={z ? '放大图片' : 'Zoom in image'}
                      onClick={() => zoomImage(1.5)}
                    >
                      +
                    </button>
                    <button
                      aria-label={z ? '适应窗口' : 'Fit image'}
                      onClick={() => {
                        setImageZoom(0);
                        imageViewport.current?.scrollTo(0, 0);
                      }}
                    >
                      {z ? '适应' : 'Fit'}
                    </button>
                    <button
                      aria-label={z ? '原始尺寸' : 'Actual image size'}
                      onClick={() => setImageZoom(1)}
                    >
                      1:1
                    </button>
                    <button
                      onClick={() => modal.current?.close()}
                      aria-label={z ? '关闭图片' : 'Close image'}
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div
                  className="research-image-viewport"
                  ref={imageViewport}
                  tabIndex={0}
                  aria-label={z ? '图纸查看区域' : 'Drawing image viewport'}
                >
                  <img
                    ref={fullImage}
                    src={dataUrl(attachment.path)}
                    alt={attachment.name}
                    className={imageZoom ? 'image-magnified' : ''}
                    style={
                      imageZoom && fullImage.current
                        ? { width: fullImage.current.naturalWidth * imageZoom }
                        : undefined
                    }
                  />
                </div>
                <a href={dataUrl(attachment.path)} download={attachment.name}>
                  {z ? '下载原图' : 'Download original image'} ↓
                </a>
              </dialog>
            </>
          ) : dxf ? (
            <DrawingPreview path={attachment.path} locale={locale} />
          ) : contents !== undefined && attachment.mimeType === 'text/markdown' ? (
            <PublicText className="research-public-appendix" text={contents} />
          ) : contents !== undefined ? (
            <pre className="research-attachment-text" tabIndex={0}>
              {contents}
            </pre>
          ) : (
            <p role={error ? 'alert' : 'status'}>
              {error
                ? z
                  ? '预览加载失败，请下载原文件。'
                  : 'Preview unavailable. Download the original file.'
                : z
                  ? '正在读取…'
                  : 'Loading…'}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function StateReference({
  detail,
  state,
  turn,
  locale,
  maintainerMode,
}: {
  detail: ResearchCaseDetail;
  state: ResearchState;
  turn: ResearchTurn;
  locale: Locale;
  maintainerMode: boolean;
}) {
  const loaded = useData<ResearchModel>(state.modelPath);
  const z = locale === 'zh';
  const model = loaded?.data?.model;
  if (!model)
    return (
      <div className="research-loading" role={loaded?.error ? 'alert' : 'status'}>
        {loaded?.error
          ? z
            ? '参考模型加载失败。'
            : 'Reference model unavailable.'
          : z
            ? '正在加载冻结模型…'
            : 'Loading the frozen model…'}
      </div>
    );
  if (
    loaded.data?.caseId !== detail.id ||
    loaded.data.state !== state.state ||
    loaded.data.sha256 !== state.modelSha256
  )
    return (
      <p role="alert">
        {z ? '模型绑定不一致，已停止显示。' : 'Model binding mismatch. Display stopped.'}
      </p>
    );
  return (
    <div className="research-state" data-state={state.state} data-model-sha256={state.modelSha256}>
      {maintainerMode && (
        <div className="research-review-banner">
          <strong>{z ? '基准维护者参考视图' : 'Benchmark-owner reference view'}</strong>
          <span>{z ? '冻结标答，仅供审阅。' : 'Frozen answers for review.'}</span>
        </div>
      )}
      <div className="research-reference-heading">
        <div>
          <h2>{z ? '参考结构' : 'Reference structure'}</h2>
          <p className="reference-caption">
            <code>
              {detail.id} · state {state.state}
            </code>{' '}
            · {turn.id} · {detail.engine}
          </p>
        </div>
        {maintainerMode ? (
          <a
            className="research-download"
            href={dataUrl(state.modelPath)}
            download={`${detail.id}-s${state.state}-model.json`}
          >
            {z ? '下载模型 JSON' : 'Download model JSON'} ↓
          </a>
        ) : (
          <button
            className="research-download"
            onClick={() =>
              downloadJson(
                publicModelForDownload(detail.id, turn.id, detail.engine, model),
                `${detail.id}-s${state.state}-model.json`,
              )
            }
          >
            {z ? '下载模型 JSON' : 'Download model JSON'} ↓
          </button>
        )}
      </div>
      <div className="research-geometry-summary">
        <span>
          <b>{model.nodes.length}</b> {z ? '节点' : 'nodes'}
        </span>
        <span>
          <b>{model.elements.length}</b> {z ? '构件' : 'members'}
        </span>
        <span>
          <b>
            {
              model.nodes.filter((node) => visibleSupportRestraints(model, node).some(Boolean))
                .length
            }
          </b>{' '}
          {z ? '物理支座' : 'physical supports'}
        </span>
        <span>
          {model.coordinate_system.dimension.toUpperCase()} ·{' '}
          {model.coordinate_system.plane?.toUpperCase() || 'XYZ'}
        </span>
        <span>{model.unit_system}</span>
      </div>
      <Suspense
        fallback={
          <div className="research-loading">
            {z ? '正在准备三维视图…' : 'Preparing the 3D view…'}
          </div>
        }
      >
        <Scene
          key={`${detail.id}-s${state.state}`}
          model={model}
          locale={locale}
          name={`${detail.id}-s${state.state}`}
        />
      </Suspense>
      <p className="reference-source">
        <strong>{z ? '评分参考' : 'Scoring reference'}:</strong> {state.reference.kind} ·{' '}
        {state.reference.solver?.name
          ? String(state.reference.solver.name)
          : `${z ? '目标引擎' : 'Target engine'}: ${detail.engine}`}
        {maintainerMode && (
          <>
            <br />
            <code>{state.reference.source}</code>
          </>
        )}
      </p>
      {maintainerMode && (
        <details className="research-disclosure">
          <summary>
            {z ? '原始模型属性、约束与荷载' : 'Raw model properties, restraints & loads'}
          </summary>
          <Json value={model} />
        </details>
      )}
      <ResearchResults
        model={model}
        modelSha256={state.modelSha256}
        deformationFields={state.deformationFields}
        quantities={turn.quantities}
        derived={turn.derived}
        locale={locale}
        caseId={detail.id}
        state={state.state}
        engine={detail.engine}
        turnId={turn.id}
        sourceHash={detail.sourceHash}
        referenceSource={state.reference}
        maintainerMode={maintainerMode}
      />
      {maintainerMode && (
        <details className="research-disclosure research-reference-evidence">
          <summary>
            {z
              ? '当前状态的参考与原生求解绑定'
              : 'Reference and native-solver bindings for this state'}
          </summary>
          <div className="research-binding-grid">
            <div>
              <h3>{z ? '评分参考' : 'Scoring reference'}</h3>
              <Json value={state.reference} />
            </div>
            <div>
              <h3>{z ? '原生核验参考' : 'Native verification reference'}</h3>
              <Json value={state.nativeReference} />
            </div>
          </div>
          <h3>{z ? '原生收据' : 'Native receipts'}</h3>
          <Json value={state.receipts} />
        </details>
      )}
    </div>
  );
}

type ComparisonFailure = {
  id: string;
  state: number;
  native: number;
  diagnostic: number;
  unit: string;
  delta: number;
  frozenLimit: number;
  referenceAllowance: number;
  engineeringLimit: number;
  engineeringPass: boolean;
  location?: Raw;
  component?: string;
};
type Comparison = {
  comparisons: number;
  strict: { passed: number; failed: number; failures: ComparisonFailure[] };
  engineering: { passed: number; failed: number };
};
function Diagnostics({ detail, locale }: { detail: ResearchCaseDetail; locale: Locale }) {
  const z = locale === 'zh';
  const rawComparisons = detail.diagnostics?.comparisons;
  const comparisons = (Array.isArray(rawComparisons) ? undefined : rawComparisons) as
    Record<string, Comparison> | undefined;
  const names = Object.keys(comparisons || {});
  const [selected, setSelected] = useState(names[0] || '');
  const comparison = comparisons?.[selected];
  if (!comparison && Array.isArray(rawComparisons)) {
    const counts = detail.diagnostics?.comparisonCounts as {
      passed: number;
      failed: number;
      primitive: number;
      derived: number;
    };
    return (
      <div className="research-diagnostics">
        <h3>{z ? '原生与独立参考比较' : 'Native / independent reference comparison'}</h3>
        <div className="diagnostic-summary">
          <div>
            <span>{z ? '冻结严格容差' : 'Strict frozen tolerance'}</span>
            <strong>
              {counts.failed} {z ? '项差异' : 'differences'}
            </strong>
            <small>
              {counts.passed} / {counts.primitive + counts.derived} {z ? '通过' : 'pass'}
            </small>
          </div>
          <div>
            <span>{z ? '工程策略诊断' : 'Engineering policy diagnostic'}</span>
            <strong>{z ? '未应用' : 'Not applied'}</strong>
            <small>{z ? '使用原始冻结容差' : 'Original frozen tolerance used'}</small>
          </div>
        </div>
        <p className="research-note">
          {z
            ? '评分参考为独立矩阵结果；OpenSees 原生结果用于独立交叉核对。下列证据保留历史核验阶段字段，当前状态以上方清单为准。'
            : 'The independent matrix result is the scoring reference; native OpenSees results provide a cross-check. Archived evidence retains historical stage fields; current status comes from the manifest above.'}
        </p>
        <details className="research-disclosure">
          <summary>{z ? '完整比较证据' : 'Full comparison evidence'}</summary>
          <Json value={detail.diagnostics} />
        </details>
      </div>
    );
  }
  if (!comparison)
    return (
      <p className="research-note">
        {z
          ? '此案例未提供交叉比较诊断。原生核验状态另列。'
          : 'No cross-solver comparison is available for this case. Native verification is reported separately.'}
      </p>
    );
  return (
    <div className="research-diagnostics">
      <div className="research-panel-heading">
        <h3>{z ? '数值比较诊断' : 'Numerical comparison diagnostics'}</h3>
        <label>
          {z ? '比较来源' : 'Comparison source'}{' '}
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            {names.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="diagnostic-summary">
        <div>
          <span>{z ? '冻结严格容差' : 'Strict frozen tolerance'}</span>
          <strong className={comparison.strict.failed ? 'research-difference' : ''}>
            {comparison.strict.failed} {z ? '项差异' : 'differences'}
          </strong>
          <small>
            {comparison.strict.passed} / {comparison.comparisons} {z ? '通过' : 'pass'}
          </small>
        </div>
        <div data-engineering-failed={comparison.engineering.failed}>
          <span>{z ? '工程策略诊断' : 'Engineering policy diagnostic'}</span>
          <strong>
            {comparison.engineering.failed} {z ? '项差异' : 'differences'}
          </strong>
          <small>
            {comparison.engineering.passed} / {comparison.comparisons} {z ? '通过' : 'pass'}
          </small>
        </div>
      </div>
      <p className="research-note">
        {z
          ? '工程精度策略扩大数值接受范围；它不等同于原始严格容差通过，也不代表最终验收或模型试验通过。'
          : 'The engineering precision policy widens the numerical acceptance region. Its result does not establish a strict-tolerance pass, final acceptance, or a completed model trial.'}
      </p>
      {!!comparison.strict.failures.length && (
        <div className="research-table-scroll">
          <table className="strict-differences">
            <thead>
              <tr>
                {[
                  z ? '数值 / 位置' : 'Quantity / location',
                  z ? '原生参考' : 'Native reference',
                  z ? '诊断值' : 'Diagnostic value',
                  '|Δ|',
                  z ? '严格限值' : 'Strict limit',
                  z ? '工程附加量' : 'Engineering allowance',
                ].map((value) => (
                  <th key={value}>{value}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparison.strict.failures.map((failure) => (
                <tr key={`${failure.state}-${failure.id}`}>
                  <td>
                    <code>{failure.id}</code>
                    <small>
                      s{failure.state} · {failure.unit}
                    </small>
                  </td>
                  {[
                    failure.native,
                    failure.diagnostic,
                    failure.delta,
                    failure.frozenLimit,
                    failure.referenceAllowance,
                  ].map((value, index) => (
                    <td key={index} title={String(value)}>
                      {formatNumber(value)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <details className="research-disclosure">
        <summary>
          {z ? '完整比较证据与精度策略' : 'Full comparison evidence & precision policy'}
        </summary>
        <Json value={detail.diagnostics} />
      </details>
    </div>
  );
}

function Review({
  detail,
  turn,
  locale,
  evaluatorVersion,
}: {
  detail: ResearchCaseDetail;
  turn: ResearchTurn;
  locale: Locale;
  evaluatorVersion: string;
}) {
  const z = locale === 'zh';
  const editionReview = detail.publicInputReview;
  const reviewStatus = {
    pending: z ? '待独立盲审' : 'Pending independent review',
    passed: z ? '通过' : 'Passed',
    failed: z ? '未通过' : 'Failed',
    partial: z ? '覆盖不完整' : 'Incomplete coverage',
    invalid: z ? '证据无效或过期' : 'Invalid or stale evidence',
  };
  const reviewCategories: Record<string, string> = {
    geometry: z ? '几何' : 'Geometry',
    topology: z ? '连接关系' : 'Topology',
    restraints: z ? '支承约束' : 'Restraints',
    materials: z ? '材料' : 'Materials',
    sections: z ? '截面与分配' : 'Sections and assignment',
    loads: z ? '荷载' : 'Loads',
    axes: z ? '坐标与局部轴' : 'Axes',
    settings: z ? '分析设置' : 'Settings',
    clarification: z ? '澄清边界' : 'Clarification',
  };
  const findingLabels: Record<string, string> = {
    missing: z ? '缺失' : 'Missing',
    mismatch: z ? '不一致' : 'Mismatch',
    unexpected: z ? '额外内容' : 'Unexpected',
    'missing-observation': z ? '缺少来源观察' : 'Missing observation',
    'unsupported-resolution': z ? '提前补全未明确值' : 'Unsupported resolution',
    'missing-clarification': z ? '缺少澄清请求' : 'Missing clarification',
    'unexpected-clarification': z ? '不适用的澄清请求' : 'Unexpected clarification',
    'invalid-evidence': z ? '证据无效' : 'Invalid evidence',
  };
  const stages: [keyof ResearchStatus, string][] = [
    ['authored', z ? '题目编制' : 'Authored'],
    ['referenceReady', z ? '参考就绪' : 'Reference ready'],
    ['nativeVerified', z ? '原生核验' : 'Native verified'],
    ['inputReviewed', z ? '冻结输入盲审' : 'Frozen input reviewed'],
    ['accepted', z ? '最终验收' : 'Accepted'],
    ['agentNotRun', z ? '模型试验' : 'Model trials'],
  ];
  const sources: SourceFile[] =
    turn.state === null
      ? turn.attachments.map((attachment) => ({
          source: attachment.source,
          sha256: attachment.sha256,
          path: attachment.path,
          role: 'public-attachment',
        }))
      : detail.sources;
  return (
    <div className="research-review">
      <section className="research-panel research-input-diagnostics">
        <h2>{z ? '本轮输入诊断' : 'Current turn input diagnostics'}</h2>
        <p className="research-note">
          {turn.expectation} · {turn.id}
        </p>
        {turn.inputBinding && (
          <details className="research-disclosure research-input-edition">
            <summary>{z ? '输入文件绑定' : 'Input file bindings'}</summary>
            <Json value={turn.inputBinding} />
          </details>
        )}
        <details className="research-disclosure">
          <summary>{z ? '响应契约' : 'Response contract'}</summary>
          <Json value={turn.responseContract} />
        </details>
        {turn.state === null && (
          <details className="research-disclosure">
            <summary>{z ? '未明确字段' : 'Unresolved fields'}</summary>
            <Json value={turn.unresolvedFields} />
          </details>
        )}
      </section>
      {editionReview && (
        <section className="research-panel" data-edition-review={editionReview.status}>
          <div className="research-panel-heading">
            <h2>{z ? '当前输入独立盲审' : 'Current input independent blind review'}</h2>
            <strong>{reviewStatus[editionReview.status]}</strong>
          </div>
          <p>
            {z
              ? '此状态绑定当前交付输入、公开审查包和重建证据。'
              : 'This status is bound to the current delivered input, public review packet and reconstruction evidence.'}
          </p>
          {Object.keys(editionReview.coverage).length > 0 && (
            <div className="research-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{z ? '核验项目' : 'Review category'}</th>
                    <th>{z ? '匹配 / 必需' : 'Matched / required'}</th>
                    <th>{z ? '缺失' : 'Missing'}</th>
                    <th>{z ? '不一致' : 'Mismatch'}</th>
                    <th>{z ? '额外' : 'Unexpected'}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(editionReview.coverage).map(([category, coverage]) => (
                    <tr key={category}>
                      <td>{reviewCategories[category] || category}</td>
                      <td>
                        {coverage.matched} / {coverage.required}
                      </td>
                      <td>{coverage.missing}</td>
                      <td>{coverage.mismatched}</td>
                      <td>{coverage.unexpected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {editionReview.findings.length > 0 && (
            <div className="research-review-findings">
              <p>
                {z
                  ? `发现 ${editionReview.findings.length} 项问题`
                  : `${editionReview.findings.length} review findings`}
              </p>
              <ul>
                {editionReview.findings.slice(0, 8).map((finding, index) => (
                  <li key={index}>
                    {finding.turnId && `${finding.turnId} · `}
                    {finding.category &&
                      `${reviewCategories[finding.category] || finding.category}: `}
                    {findingLabels[finding.code] || finding.code}
                    {finding.path && ` · ${finding.path}`}
                    {finding.message && ` · ${finding.message}`}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <details className="research-disclosure">
            <summary>{z ? '输入盲审证据' : 'Input review evidence'}</summary>
            <Json value={editionReview} />
          </details>
        </section>
      )}
      <div className="research-review-banner">
        <strong>{z ? '冻结基准验收状态' : 'Frozen benchmark acceptance status'}</strong>
        <span>{evaluatorVersion}</span>
      </div>
      <section className="review-status">
        {stages.map(([key, label]) => (
          <div key={key} data-status={key} data-complete={detail.status[key]}>
            <span>{label}</span>
            <strong
              className={
                key !== 'agentNotRun' && detail.status[key]
                  ? 'research-complete'
                  : 'research-pending'
              }
            >
              {key === 'agentNotRun'
                ? detail.status[key]
                  ? z
                    ? '未运行'
                    : 'Not run'
                  : z
                    ? '已运行'
                    : 'Run recorded'
                : detail.status[key]
                  ? z
                    ? '已完成'
                    : 'Complete'
                  : z
                    ? '待完成'
                    : 'Pending'}
            </strong>
          </div>
        ))}
      </section>
      <p className="research-note">
        {z
          ? '以上状态取自当前冻结清单。历史编题计划中的“待运行”描述不覆盖当前原生核验状态。输入盲审与端到端模型试验仍是独立任务。'
          : 'These stages come from the current frozen manifest. Historical authoring-plan wording does not override native verification. Blind input review and end-to-end model trials remain separate tasks.'}
      </p>
      {turn.state !== null && (
        <section className="research-panel">
          <Diagnostics detail={detail} locale={locale} />
        </section>
      )}
      <section className="research-panel">
        <h2>{z ? '来源与文件绑定' : 'Sources & file bindings'}</h2>
        <p className="research-source-hash">
          {z ? '案例输入摘要' : 'Case input hash'} <code>{detail.sourceHash}</code>
        </p>
        <details className="research-disclosure">
          <summary>
            {z ? `查看 ${sources.length} 个来源文件` : `Inspect ${sources.length} source files`}
          </summary>
          <div className="research-table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{z ? '文件' : 'File'}</th>
                  <th>SHA-256</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source, index) => (
                  <tr key={`${source.source}-${index}`}>
                    <td>
                      {source.path ? (
                        <a href={dataUrl(source.path)} download>
                          {source.source} ↓
                        </a>
                      ) : (
                        <code>{source.source}</code>
                      )}
                      <small>{source.role}</small>
                    </td>
                    <td>
                      <code>{source.sha256}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>
      {turn.state !== null && (
        <section className="research-panel">
          <h2>{z ? '维护者原始记录' : 'Original reviewer records'}</h2>
          <div className="research-downloads">
            <button onClick={() => downloadJson(detail, `${detail.id}-review-record.json`)}>
              {z ? '下载完整审阅记录 JSON' : 'Download full review JSON'}
            </button>
          </div>
          <details className="research-disclosure">
            <summary>{z ? '验收记录 JSON' : 'Acceptance record JSON'}</summary>
            <Json value={detail.acceptance} />
          </details>
          <details className="research-disclosure">
            <summary>
              {z
                ? '原始编题契约（含历史计划）'
                : 'Original authoring contract (includes historical plan)'}
            </summary>
            <p className="research-note">
              {z
                ? '历史文字仅用于溯源；当前状态以上方冻结清单为准。'
                : 'Historical wording is retained for provenance. Use the frozen manifest stages above for current status.'}
            </p>
            <Json value={detail.contract} />
          </details>
        </section>
      )}
    </div>
  );
}
