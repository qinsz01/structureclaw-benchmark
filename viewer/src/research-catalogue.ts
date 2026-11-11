import type { Locale } from './types';
import type { ResearchCaseSummary, ResearchCatalogueFacet, ResearchIndex } from './research-types';

export type CatalogueFilters = {
  trial?: string;
  query: string;
  family: string;
  language: string;
  engine: string;
  category: string;
  structure: string;
  dimension: string;
  difficulty: string;
  modality: string;
};

const parameters: [keyof CatalogueFilters, string][] = [
  ['query', 'q'],
  ['family', 'family'],
  ['language', 'lang'],
  ['engine', 'engine'],
  ['category', 'category'],
  ['structure', 'structure'],
  ['dimension', 'dimension'],
  ['difficulty', 'difficulty'],
  ['modality', 'modality'],
];

export function readCatalogueLocation(hash: string): { filters: CatalogueFilters; page: number } {
  const params = new URLSearchParams(hash.split('?')[1]);
  const filters = Object.fromEntries(
    parameters.map(([key, parameter]) => [key, params.get(parameter) || '']),
  ) as CatalogueFilters;
  if (params.get('trial')) filters.trial = params.get('trial')!;
  const requestedPage = Number(params.get('page'));
  return {
    filters,
    page: Number.isFinite(requestedPage) ? Math.max(1, Math.floor(requestedPage)) : 1,
  };
}

export function catalogueHash(filters: CatalogueFilters, page: number): string {
  const params = new URLSearchParams();
  for (const [key, parameter] of parameters) {
    if (filters[key]) params.set(parameter, filters[key]);
  }
  if (filters.trial) params.set('trial', filters.trial);
  if (page > 1) params.set('page', String(page));
  return `#/${params.size ? '?' + params : ''}`;
}

export const familyLabel = (family: string, locale: Locale) =>
  ({
    standard_workflow: locale === 'zh' ? '标准工作流' : 'Standard workflow',
    interactive_robustness: locale === 'zh' ? '交互鲁棒性' : 'Interactive robustness',
    multimodal_reverse_engineering:
      locale === 'zh' ? '多模态逆向建模' : 'Multimodal reconstruction',
  })[family] || family;

export function filterResearchCases(
  index: Pick<ResearchIndex, 'cases' | 'catalogue'>,
  filters: CatalogueFilters,
  locale: Locale,
): ResearchCaseSummary[] {
  const rows = new Map(index.catalogue?.cases.map((row) => [row.id, row]));
  const terms = filters.query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const facets: ResearchCatalogueFacet[] = [
    'category',
    'structure',
    'dimension',
    'difficulty',
    'modality',
  ];
  return index.cases.filter((item) => {
    if (filters.trial === 'passed' && item.codexTrial?.status !== 'passed') return false;
    if (filters.trial === 'not-passed' && (!item.codexTrial || item.codexTrial.status === 'passed'))
      return false;
    if (filters.trial === 'repaired' && !item.codexTrial?.repaired) return false;
    const row = rows.get(item.id);
    if (
      (filters.family && item.family !== filters.family) ||
      (filters.language && item.locale !== filters.language) ||
      (filters.engine && item.engine !== filters.engine) ||
      facets.some((facet) => {
        const value =
          row?.[facet] ?? (facet === 'structure' || facet === 'modality' ? item[facet] : '');
        return filters[facet] && value !== filters[facet];
      })
    )
      return false;
    const labels = row
      ? facets.flatMap((facet) => {
          const choice = index.catalogue?.definitions[facet]?.find(
            (entry) => entry.key === row[facet],
          );
          return choice ? [choice.zh, choice.en] : [];
        })
      : [];
    const haystack = [
      item.id,
      item.description,
      item.family,
      familyLabel(item.family, locale),
      item.engine,
      item.structure,
      item.modality,
      row?.title,
      row?.focus,
      row?.category,
      row?.dimension,
      row?.difficulty,
      ...labels,
    ]
      .join(' ')
      .toLocaleLowerCase();
    return terms.every((term) => haystack.includes(term));
  });
}
