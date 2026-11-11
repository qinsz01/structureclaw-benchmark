import { useState } from 'react';
import type { Locale } from './types';
import type {
  ResearchCatalogue,
  ResearchCatalogueFacet,
  ResearchCatalogueMetrics,
} from './research-types';

export function ResearchComposition({
  catalogue,
  locale,
}: {
  catalogue: ResearchCatalogue;
  locale: Locale;
}) {
  const z = locale === 'zh';
  const [facet, setFacet] = useState<ResearchCatalogueFacet>('family');
  const facets: [ResearchCatalogueFacet, string][] = [
    ['family', z ? '任务大类' : 'Family'],
    ['category', z ? '能力子类' : 'Capability subgroup'],
    ['structure', z ? '结构类型' : 'Structure'],
    ['dimension', z ? '模型维度' : 'Dimension'],
    ['difficulty', z ? '预设难度' : 'Preset difficulty'],
    ['modality', z ? '输入模态' : 'Input modality'],
    ['engine', z ? '求解器' : 'Engine'],
    ['language', z ? '输入语言' : 'Input language'],
  ];
  const metrics: [keyof ResearchCatalogueMetrics, string][] = [
    ['cases', z ? '题数' : 'Cases'],
    ['turns', z ? '轮次' : 'Turns'],
    ['states', z ? '状态数' : 'States'],
    ['attachmentFiles', z ? '输入文件' : 'Input files'],
    ['attachmentUses', z ? '文件使用次数' : 'File uses'],
    ['markdownFiles', 'Markdown'],
    ['pngFiles', 'PNG'],
    ['dxfFiles', 'DXF'],
  ];
  const share = (cases: number) =>
    `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(
      catalogue.totals.cases ? (100 * cases) / catalogue.totals.cases : 0,
    )}%`;
  return (
    <details className="research-composition">
      <summary>
        <span>
          <strong>{z ? '基准构成' : 'Benchmark composition'}</strong>
          <small>
            {z ? '按能力、结构与输入查看统计' : 'Counts by capability, structure, and input'}
          </small>
        </span>
        <span className="research-details-indicator" aria-hidden="true">
          +
        </span>
      </summary>
      <div className="research-composition-body">
        <div className="research-composition-controls">
          <label>
            <span>{z ? '统计维度' : 'Composition dimension'}</span>
            <select
              value={facet}
              onChange={(event) => setFacet(event.target.value as ResearchCatalogueFacet)}
            >
              {facets.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <p>
            {z
              ? `每题归入一个能力子类；占比均以全部 ${catalogue.totals.cases} 题为分母，不随目录筛选变化。`
              : `Each task has one primary capability subgroup. Shares use all ${catalogue.totals.cases} cases and remain independent of catalogue filters.`}
          </p>
        </div>
        {facet === 'difficulty' && (
          <p className="research-composition-note">
            {z
              ? '难度为题目预设分档，不代表模型实测表现。'
              : 'Difficulty is assigned to the authored task and does not represent measured model performance.'}
          </p>
        )}
        <div
          className="research-composition-table"
          tabIndex={0}
          role="region"
          aria-label={z ? '基准构成统计表' : 'Benchmark composition table'}
        >
          <table>
            <thead>
              <tr>
                <th scope="col">{facets.find(([key]) => key === facet)?.[1]}</th>
                {metrics.map(([key, label], i) => (
                  <MetricHeading key={key} label={label} showShare={i === 0} locale={locale} />
                ))}
              </tr>
            </thead>
            <tbody>
              {catalogue.breakdowns[facet].map((bucket) => (
                <tr key={bucket.key} data-bucket={bucket.key}>
                  <th scope="row">
                    {bucket[locale]}
                    {facet === 'category' && bucket.family && (
                      <small className="research-composition-family">
                        {catalogue.definitions.family.find(
                          (family) => family.key === bucket.family,
                        )?.[locale] || bucket.family}
                      </small>
                    )}
                  </th>
                  {metrics.map(([key], i) => (
                    <MetricCell
                      key={key}
                      metric={key}
                      value={bucket[key]}
                      share={i === 0 ? share(bucket.cases) : undefined}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">{z ? '全部基准' : 'Whole corpus'}</th>
                {metrics.map(([key], i) => (
                  <MetricCell
                    key={key}
                    metric={key}
                    value={catalogue.totals[key]}
                    share={i === 0 ? share(catalogue.totals.cases) : undefined}
                  />
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="research-composition-note">
          {z
            ? '输入文件按每题内的文件路径去重；文件使用次数按各轮实际引用累计。Markdown、PNG、DXF 均按文件计数，题数与文件数分开统计。'
            : 'Input files count each path once per case; file uses count occurrences across turns. Markdown, PNG, and DXF columns count files, separately from case counts.'}
        </p>
      </div>
    </details>
  );
}

function MetricHeading({
  label,
  showShare,
  locale,
}: {
  label: string;
  showShare: boolean;
  locale: Locale;
}) {
  return (
    <>
      <th scope="col">{label}</th>
      {showShare && <th scope="col">{locale === 'zh' ? '全库占比' : 'Corpus share'}</th>}
    </>
  );
}

function MetricCell({ metric, value, share }: { metric: string; value: number; share?: string }) {
  return (
    <>
      <td data-metric={metric}>{value}</td>
      {share !== undefined && <td data-metric="share">{share}</td>}
    </>
  );
}
