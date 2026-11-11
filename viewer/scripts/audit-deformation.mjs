import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readResearchCorpus } from './research-data.mjs';

export function deformationCoverageAudit(corpus) {
  const states = [],
    turns = [];
  for (const { detail, models } of corpus.cases) {
    for (const state of detail.states)
      for (const field of state.deformationFields) {
        const model = models.find((m) => m.state === state.state).model;
        states.push({
          caseId: detail.id,
          state: state.state,
          engine: detail.engine,
          dimension: model.coordinate_system.dimension,
          selection: field.selection,
          ...field.coverage,
        });
      }
    for (const turn of detail.turns) {
      if (turn.state === null) continue;
      const selected = [
        ...new Map(
          turn.quantities.map((q) => [`${q.selection.kind}:${q.selection.id}`, q.selection]),
        ).values(),
      ];
      for (const selection of selected) {
        const field = states.find(
          (s) =>
            s.caseId === detail.id &&
            s.state === turn.state &&
            s.selection.kind === selection.kind &&
            s.selection.id === selection.id,
        );
        if (!field)
          throw Error(
            `Missing deformation field: ${detail.id}/${turn.id}/${JSON.stringify(selection)}`,
          );
        turns.push({
          ...field,
          turnId: turn.id,
          requestedQuantities: turn.quantities.filter(
            (q) => q.selection.kind === selection.kind && q.selection.id === selection.id,
          ).length,
        });
      }
    }
  }
  const summarize = (rows) => {
    const groups = {};
    for (const row of rows)
      for (const key of [
        'all',
        `engine:${row.engine}`,
        `dimension:${row.dimension}`,
        `${row.engine}/${row.dimension}`,
        `family:${row.caseId.split('-')[0]}`,
      ]) {
        const g = (groups[key] ||= {
          selections: 0,
          complete: 0,
          partial: 0,
          unavailable: 0,
          nodes: 0,
          elements: 0,
          nativeComponents: 0,
          constraintComponents: 0,
        });
        g.selections++;
        g.nodes += row.completeNodes;
        g.elements += row.completeElements;
        g.nativeComponents += row.nativeComponents;
        g.constraintComponents += row.constraintComponents;
        g[
          row.completeNodes === row.totalNodes && row.completeElements === row.totalElements
            ? 'complete'
            : row.completeNodes
              ? 'partial'
              : 'unavailable'
        ]++;
      }
    return groups;
  };
  return {
    schemaVersion: 1,
    purpose: 'retained-native-node-deformation-coverage',
    scoringPolicyUnchanged: true,
    stateSelections: { summary: summarize(states), rows: states },
    turnSelections: { summary: summarize(turns), rows: turns },
  };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
  const audit = deformationCoverageAudit(readResearchCorpus(root));
  if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(audit, null, 2) + '\n');
  console.log(
    JSON.stringify(
      {
        stateSelections: audit.stateSelections.summary,
        turnSelections: audit.turnSelections.summary,
      },
      null,
      2,
    ),
  );
}
