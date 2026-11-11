import fs from 'node:fs';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import provider from '../../lib/corpus-provider.cjs';
import validation from '../../lib/research300-validation.cjs';
import evaluation from '../../lib/research300-evaluation.cjs';
import precision from '../../lib/reference-precision.cjs';
import commercialChecker from '../../scripts/check-research300-commercial.cjs';
import inputReview from '../../lib/public-input-review.cjs';
import catalogueProjection from '../../lib/research300-catalogue.cjs';
import { readNativeDisplacementFields } from './native-displacements.mjs';

const {
  loadCorpus,
  loadCase,
  getPublicTurnInput,
  getFrozenPublicTurnInput,
  getResponseContract,
  resolveCaseFile,
  listFiles,
  sha256,
} = provider;
const { sourceHash, validateResearchCase } = validation;
const digest = (value) => sha256(Buffer.from(JSON.stringify(value)));
const expect = (condition, message) => {
  if (!condition) throw new Error(message);
};
const equal = (actual, expected, message) => expect(isDeepStrictEqual(actual, expected), message);
const prefix = 'corpora/research-300';
const mime = {
  '.json': 'application/json',
  '.txt': 'text/plain',
  '.md': 'text/markdown',
  '.csv': 'text/csv',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.dxf': 'image/vnd.dxf',
};
const units = {
  m: ['length', 1],
  mm: ['length', 0.001],
  rad: ['rotation', 1],
  N: ['force', 1],
  kN: ['force', 1000],
  'N.m': ['moment', 1],
  'N*m': ['moment', 1],
  'kN.m': ['moment', 1000],
  'kN*m': ['moment', 1000],
  'kN·m': ['moment', 1000],
};

/** Convert a displayed answer while preserving its original frozen value and provenance. */
export function requestedUnit(row, unit) {
  const from = units[row.unit],
    to = units[unit];
  expect(from && to && from[0] === to[0], `Incompatible requested unit: ${row.unit} -> ${unit}`);
  const factor = from[1] / to[1];
  return {
    ...structuredClone(row),
    sourceValue: row.value,
    sourceUnit: row.unit,
    value: row.value * factor,
    unit,
    ...(row.tolerance
      ? {
          tolerance: {
            absolute: row.tolerance.absolute * Math.abs(factor),
            relative: row.tolerance.relative,
          },
        }
      : {}),
    ...(row.engineeringPrecision
      ? { engineeringPrecision: precision.convertPrecision(row, unit, factor) }
      : {}),
  };
}

export function createResearchReader(root) {
  root = path.resolve(root);
  const sources = new Map();
  const bytes = (source, expectedHash, role) => {
    const file = resolveCaseFile(root, source);
    const value = fs.readFileSync(file),
      hash = sha256(value);
    if (expectedHash !== undefined) expect(hash === expectedHash, `Stale source hash: ${source}`);
    const old = sources.get(source);
    expect(!old || old.sha256 === hash, `Source changed during export: ${source}`);
    const descriptor = { source, sha256: hash, ...(role ? { role } : {}) };
    sources.set(source, { ...old, ...descriptor });
    return { bytes: value, descriptor };
  };
  const json = (source, hash, role) => JSON.parse(bytes(source, hash, role).bytes.toString('utf8'));
  return { root, sources, bytes, json };
}

function statusFromValidation(result) {
  return {
    authored: result.authored,
    referenceReady: result.referenceReady,
    nativeVerified: result.nativeVerified,
    inputReviewed: result.inputReviewed,
    accepted: result.accepted,
    agentNotRun: result.agentStatus === 'not-run',
  };
}
function manifestStatus(entry) {
  return {
    authored: entry.validation.authored,
    referenceReady: entry.validation.referenceReady,
    nativeVerified: entry.statuses.native === 'native-verified',
    inputReviewed: entry.statuses.inputReview === 'independently-reviewed',
    accepted: entry.validation.accepted,
    agentNotRun: entry.statuses.agent === 'not-run',
  };
}

/** Verify a complete case against its frozen manifest entry before projecting any browser data. */
export function readResearchCase(reader, corpus, entry, planCase, commercialDiagnostics = null) {
  const { id } = entry,
    base = `${prefix}/cases/${id}`;
  const caseDir = resolveCaseFile(reader.root, base, { directory: true });
  const localSources = new Set();
  const read = (name, hash, role) => {
    const source = `${base}/${name}`;
    localSources.add(source);
    return reader.json(source, hash, role);
  };
  const descriptor = (name, hash, role) => {
    const source = `${base}/${name}`;
    localSources.add(source);
    return reader.bytes(source, hash, role).descriptor;
  };
  const files = [...entry.publicFiles, ...entry.privateFiles].sort((a, b) =>
    a.path.localeCompare(b.path, 'en'),
  );
  equal(
    listFiles(caseDir).sort(),
    files.map((file) => file.path).sort(),
    `${id}: frozen file inventory differs`,
  );
  for (const file of files) {
    const source = `${base}/${file.path}`;
    localSources.add(source);
    const actual = reader.bytes(
      source,
      file.sha256,
      entry.publicFiles.includes(file) ? 'public-input' : 'reviewer-source',
    );
    expect(actual.bytes.length === file.bytes, `${id}: frozen file size differs: ${file.path}`);
  }
  const record = loadCase(corpus, id),
    { contract } = record;
  for (const field of ['id', 'modelId', 'family', 'language', 'plannedEngine'])
    equal(contract[field], entry[field], `${id}: manifest ${field} differs`);
  equal(entry.contract, `cases/${id}/contract.json`, `${id}: manifest contract path differs`);
  expect(sourceHash(caseDir, contract) === entry.sourceHash, `${id}: stale manifest sourceHash`);
  const validationResult = validateResearchCase({
    root: reader.root,
    caseDir,
    planCase,
    stage: 'reference-ready',
  });
  expect(
    validationResult.valid,
    `${id}: invalid research source: ${validationResult.errors.join('; ')}`,
  );
  const status = statusFromValidation(validationResult);
  equal(status, manifestStatus(entry), `${id}: stale manifest status / native qualification`);
  const reference = read('independent-reference.json', undefined, 'frozen-scoring-reference');
  const acceptance = read('acceptance.json', undefined, 'native-qualification');
  expect(
    acceptance.sourceHash === entry.sourceHash &&
      acceptance.independentReferenceSha256 ===
        reader.sources.get(`${base}/independent-reference.json`).sha256,
    `${id}: stale acceptance binding`,
  );
  const sourceManifest = { schemaVersion: 1, files: validation.authoredFiles(caseDir, contract) };
  equal(reference.sourceManifest, sourceManifest, `${id}: stale scoring source manifest`);
  expect(reference.id === id, `${id}: scoring reference case differs`);
  const commercial = contract.plannedEngine !== 'OpenSees';
  expect(
    commercial
      ? reference.referenceKind === `native-${contract.plannedEngine.toLowerCase()}` &&
          reference.notCommercialScoringTruth === false
      : reference.referenceKind === 'independent-elastic-matrix',
    `${id}: scoring reference engine differs`,
  );
  const nativeName = commercial ? 'independent-reference.json' : 'native-opensees-reference.json';
  const native = commercial
    ? reference
    : read(nativeName, undefined, 'same-engine-native-reference');
  expect(
    native.sourceHash === entry.sourceHash && native.id === id,
    `${id}: stale same-engine native source binding`,
  );
  equal(native.inputHashes, reference.inputHashes, `${id}: stale native input bindings`);
  equal(native.sourceManifest, sourceManifest, `${id}: stale native source manifest`);
  expect(
    native.referenceKind === `native-${contract.plannedEngine.toLowerCase()}`,
    `${id}: native reference engine differs`,
  );
  let qualification;
  if (commercial) {
    const evidence = acceptance.sameEngineTruth.evidence;
    qualification = read(evidence.path, evidence.sha256, 'same-engine-native-review');
  } else {
    qualification = read('native-independent-review.json', undefined, 'same-engine-native-review');
    expect(
      qualification.caseId === id &&
        qualification.sourceHash === entry.sourceHash &&
        qualification.decision === 'verified',
      `${id}: stale native review binding`,
    );
    expect(
      qualification.independentReferenceSha256 ===
        reader.sources.get(`${base}/independent-reference.json`).sha256 &&
        qualification.nativeReferenceSha256 === reader.sources.get(`${base}/${nativeName}`).sha256,
      `${id}: native review reference binding differs`,
    );
    // Global descriptors in this historical review may predate later commercial
    // revisions. Current evidence is checked below against these case bindings.
  }
  const metadata = (document) =>
    Object.fromEntries(
      Object.entries(document).filter(([key]) => !['states', 'checks'].includes(key)),
    );
  const referenceDescriptor = {
    ...descriptor('independent-reference.json', undefined, 'frozen-scoring-reference'),
    kind: reference.referenceKind,
    solver: reference.solver || null,
  };
  const nativeDescriptor = {
    ...descriptor(nativeName, undefined, 'same-engine-native-reference'),
    kind: native.referenceKind,
    solver:
      native.solver ||
      (commercial
        ? { product: contract.plannedEngine, engineBinding: native.engineBinding || null }
        : null),
    metadata: { ...metadata(native), qualification },
  };
  const states = reference.states.map((frozen) => {
    const state = frozen.state,
      name = contract.modelStates[state - 1];
    expect(typeof name === 'string', `${id}: unknown reference state ${state}`);
    if (frozen.model !== undefined)
      expect(frozen.model === name, `${id}: scoring model state differs`);
    const modelSource = descriptor(name, reference.inputHashes[name], 'reviewer-model');
    const nativeState = native.states.filter((item) => item.state === state);
    expect(
      nativeState.length === 1 && nativeState[0].model === name,
      `${id}: native model state differs`,
    );
    for (const key of ['sourceModelSha256', 'originalModelSha256']) {
      if (nativeState[0][key] !== undefined)
        expect(nativeState[0][key] === modelSource.sha256, `${id}: native model hash differs`);
    }
    const selections = [
      ...new Map(frozen.quantities.map((q) => [JSON.stringify(q.selection), q.selection])).values(),
    ];
    const receipts = selections.map((selection) => {
      const matches = acceptance.sameEngineTruth.receipts.filter(
        (r) => r.state === state && isDeepStrictEqual(r.selection, selection),
      );
      expect(
        matches.length === 1,
        `${id}: missing or duplicate native receipt ${state}/${JSON.stringify(selection)}`,
      );
      const receipt = matches[0],
        body = read(receipt.path, receipt.sha256, 'same-engine-native-receipt');
      expect(
        body.engine === contract.plannedEngine &&
          body.modelSha256 === modelSource.sha256 &&
          body.state === state &&
          isDeepStrictEqual(body.selection, selection) &&
          body.status === 'succeeded' &&
          body.runId &&
          body.engineVersion,
        `${id}: invalid native receipt binding`,
      );
      if (body.sourceHash !== undefined)
        expect(body.sourceHash === entry.sourceHash, `${id}: stale native receipt sourceHash`);
      for (const artifact of body.artifacts)
        descriptor(artifact.path, artifact.sha256, 'native-receipt-artifact');
      return { ...body, source: `${base}/${receipt.path}`, sha256: receipt.sha256 };
    });
    const deformationFields = readNativeDisplacementFields({
      reader,
      base,
      caseId: id,
      engine: contract.plannedEngine,
      sourceHash: entry.sourceHash,
      state,
      model: record.models[state - 1],
      modelSource,
      selections,
      receipts,
    });
    for (const field of deformationFields)
      for (const source of field.sources) localSources.add(source.source);
    return {
      state,
      deformationFields,
      modelPath: `models/${id}-s${state}.json`,
      modelSha256: modelSource.sha256,
      reference: referenceDescriptor,
      quantities: frozen.quantities,
      derived: frozen.derived || [],
      selections,
      receipts,
      nativeReference: nativeDescriptor,
    };
  });
  const publicTurns = [],
    turns = contract.turns.map((turn, index) => {
      const input = getPublicTurnInput(record, index),
        frozenInput = getFrozenPublicTurnInput(record, index),
        responseContract = getResponseContract(record, index);
      equal(input.responseContract, responseContract, `${id}: public response contract differs`);
      equal(
        frozenInput.responseContract,
        responseContract,
        `${id}: frozen response contract differs`,
      );
      publicTurns.push({
        id: turn.id,
        instruction: frozenInput.instruction,
        attachments: turn.attachments,
        responseContract,
      });
      if (input.inputBinding) {
        const editionBase = `${prefix}/public-inputs`;
        const validatorSources = input.inputBinding.validatorSources || [
          {
            path: 'scripts/research300/public_input_editorial.py',
            sha256: input.inputBinding.editorialValidatorSha256,
          },
        ];
        for (const [source, hash] of [
          [`${editionBase}/manifest.json`, input.inputBinding.editionManifestSha256],
          [`${editionBase}/${id}/input.json`, input.inputBinding.editionBundleSha256],
          ...validatorSources.map((source) => [source.path, source.sha256]),
          ...(input.inputBinding.authorAuditSha256
            ? [[`${editionBase}/${id}/author-audit.json`, input.inputBinding.authorAuditSha256]]
            : []),
        ]) {
          reader.bytes(source, hash, 'public-input-edition');
          localSources.add(source);
        }
      }
      const state = turn.expectation === 'clarify' ? null : turn.state;
      const frozen = states.find((item) => item.state === state);
      const project = (wanted, rows) =>
        wanted.map((request) => {
          const matches = rows.filter((row) => row.id === request.id);
          expect(
            matches.length === 1,
            `${id}/${turn.id}: missing or ambiguous frozen answer ${request.id}`,
          );
          const row = matches[0];
          for (const key of ['selection', 'location', 'component', 'operation'])
            if (request[key] !== undefined)
              equal(
                row[key],
                request[key],
                `${id}/${turn.id}: answer selector differs: ${request.id}`,
              );
          return requestedUnit(row, request.unit);
        });
      expect(state === null || frozen, `${id}/${turn.id}: missing model state`);
      if (state === null)
        expect(
          !responseContract.quantities.length && !responseContract.derived.length,
          `${id}/${turn.id}: clarification exposes a numerical answer`,
        );
      return {
        id: input.turnId,
        state,
        expectation: turn.expectation,
        instruction: input.instruction,
        ...(input.inputBinding
          ? {
              inputEdition: input.inputEdition,
              publicInputSha256: input.publicInputSha256,
              inputBinding: input.inputBinding,
            }
          : {}),
        attachments: input.attachments.map((attachment) => {
          const source = path.relative(reader.root, attachment.path).split(path.sep).join('/'),
            saved = reader.bytes(source, attachment.sha256, 'public-input');
          localSources.add(source);
          return {
            name: attachment.name,
            path: `attachments/${id}/${attachment.relPath}`,
            source,
            sha256: saved.descriptor.sha256,
            bytes: saved.bytes.length,
            mimeType:
              mime[path.extname(attachment.relPath).toLowerCase()] || 'application/octet-stream',
          };
        }),
        responseContract,
        quantities: state === null ? [] : project(responseContract.quantities, frozen.quantities),
        derived: state === null ? [] : project(responseContract.derived, frozen.derived),
        requiredOutputs: responseContract.outputs,
        unresolvedFields: turn.unresolvedFields || [],
      };
    });
  equal(
    entry.responseContractTurnHashes,
    publicTurns.map((t) => ({ turnId: t.id, sha256: digest(t.responseContract) })),
    `${id}: stale turn response contract hash`,
  );
  expect(
    entry.responseContractSha256 ===
      digest(publicTurns.map((t) => ({ turnId: t.id, responseContract: t.responseContract }))),
    `${id}: stale response contract hash`,
  );
  expect(
    entry.publicSha256 === digest({ files: entry.publicFiles, turns: publicTurns }),
    `${id}: stale public input hash`,
  );
  expect(entry.privateSha256 === digest(entry.privateFiles), `${id}: stale private file hash`);
  const orderedFiles = [...entry.publicFiles, ...entry.privateFiles].sort((a, b) =>
    a.path < b.path ? -1 : a.path > b.path ? 1 : 0,
  );
  expect(entry.filesSha256 === digest(orderedFiles), `${id}: stale file inventory hash`);
  let diagnostics = null,
    strictComparison = 'not-available';
  if (commercial) {
    expect(commercialDiagnostics, `${id}: current commercial diagnostics missing`);
    const rows = commercialDiagnostics.document.cases.filter((row) => row.id === id);
    expect(rows.length === 1, `${id}: missing current commercial diagnostic row`);
    const row = rows[0];
    expect(
      row.engine === contract.plannedEngine && row.sourceHash === entry.sourceHash,
      `${id}: stale diagnostic source binding`,
    );
    for (const artifact of row.artifacts) {
      reader.bytes(artifact.path, artifact.sha256, `diagnostic-${artifact.role}`);
      localSources.add(artifact.path);
    }
    for (const [kind, name] of [
      ['matrix', 'independent-reference-matrix-diagnostic.json'],
      ['OpenSees', 'native-opensees-reference.json'],
    ]) {
      const diagnostic = read(name, undefined, 'cross-engine-diagnostic');
      equal(
        row.comparisons[kind],
        commercialChecker.compareDocuments(reference, diagnostic, record.referenceRequests),
        `${id}: stale ${kind} diagnostic comparison`,
      );
    }
    localSources.add(commercialDiagnostics.source);
    diagnostics = {
      ...row,
      source: commercialDiagnostics.source,
      sha256: commercialDiagnostics.sha256,
      comparisonPolicy: commercialDiagnostics.document.comparisonPolicy,
    };
    strictComparison = Object.values(row.comparisons).some(
      (comparison) => comparison.strict.failed > 0,
    )
      ? 'difference'
      : 'pass';
  } else if (qualification.numericalComparison) {
    const current = commercialDiagnostics?.openSees;
    expect(current, `${id}: current native comparison missing`);
    const rows = current.document.cases.filter((row) => row.id === id);
    expect(
      rows.length === 1 && rows[0].sourceHash === entry.sourceHash,
      `${id}: stale native comparison source binding`,
    );
    equal(
      rows[0],
      qualification.numericalComparison,
      `${id}: current native comparison differs from reviewed case evidence`,
    );
    for (const artifact of rows[0].artifacts) {
      const source = `${prefix}/cases/${artifact.path}`;
      reader.bytes(source, artifact.sha256, `native-comparison-${artifact.role}`);
      localSources.add(source);
    }
    localSources.add(current.source);
    diagnostics = { ...rows[0], source: current.source, sha256: current.sha256 };
    strictComparison = diagnostics.comparisonCounts.failed ? 'difference' : 'pass';
  }
  const description = planCase.title;
  const publicInputReview = turns[0]?.inputBinding
    ? inputReview.getPublicInputReview(record, turns[0].inputBinding)
    : undefined;
  for (const evidence of publicInputReview?.evidence || []) {
    reader.bytes(evidence.path, evidence.sha256, 'public-input-independent-review');
    localSources.add(evidence.path);
  }
  const summary = {
    id,
    description,
    family: contract.family,
    locale: contract.locale,
    engine: contract.plannedEngine,
    structure: planCase.structure,
    modality: contract.attachments.some((name) => /\.dxf$/i.test(name))
      ? 'dxf'
      : contract.attachments.some((name) => /\.(png|svg)$/i.test(name))
        ? 'image'
        : 'text',
    turnCount: turns.length,
    stateCount: states.length,
    sourceHash: entry.sourceHash,
    status,
    strictComparison,
  };
  const detail = {
    schemaVersion: 1,
    corpusId: 'research-300',
    id,
    description,
    family: contract.family,
    locale: contract.locale,
    engine: contract.plannedEngine,
    sourceHash: entry.sourceHash,
    status,
    turns,
    states,
    acceptance,
    ...(publicInputReview ? { publicInputReview } : {}),
    diagnostics,
    sources: [...localSources].sort().map((source) => reader.sources.get(source)),
    contract,
  };
  return {
    summary,
    detail,
    models: states.map((state) => ({
      caseId: id,
      state: state.state,
      model: record.models[state.state - 1],
      source: `${base}/${contract.modelStates[state.state - 1]}`,
      sha256: state.modelSha256,
    })),
  };
}

export function summarizePublicInputReviews(cases) {
  const summary = {
    edition: 'current',
    total: 0,
    reviewed: 0,
    passed: 0,
    failed: 0,
    partial: 0,
    pending: 0,
    invalid: 0,
  };
  for (const item of cases) {
    const review = item.detail.publicInputReview;
    if (review?.inputEdition !== summary.edition) continue;
    summary.total += 1;
    const status = ['passed', 'failed', 'partial'].includes(review.status)
      ? review.verified
        ? review.status
        : 'invalid'
      : review.status === 'pending'
        ? 'pending'
        : 'invalid';
    summary[status] += 1;
    if (['passed', 'failed', 'partial'].includes(status)) summary.reviewed += 1;
  }
  return summary;
}

export function readResearchCorpus(root) {
  const reader = createResearchReader(root);
  const manifest = reader.json(`${prefix}/manifest.json`, undefined, 'frozen-corpus-manifest');
  expect(
    manifest.corpusId === 'research-300' &&
      manifest.schemaVersion === 1 &&
      manifest.validation.valid &&
      !manifest.validation.partial,
    'A complete frozen research-300 manifest is required',
  );
  const corpus = loadCorpus({ corpus: 'research-300', root });
  equal(
    corpus.cases.map((c) => c.id),
    manifest.cases.map((c) => c.id),
    'Research case inventory differs from the frozen manifest',
  );
  expect(corpus.cases.length === 300, 'The research corpus must contain exactly 300 cases');
  const plan = reader.json(
    manifest.sourcePlan.path,
    manifest.sourcePlan.sha256,
    'frozen-source-plan',
  );
  const sourceTasks = reader.json(
    `planning/sources/${plan.sources.tasks.file}`,
    plan.sources.tasks.sha256,
    'archived-task-classification',
  );
  const taxonomy = reader.json('planning/research300-taxonomy.json', undefined, 'current-task-classification');
  const diagnosticSource = `${prefix}/evidence/commercial-native-diagnostic-comparison.json`;
  const document = reader.json(diagnosticSource, undefined, 'current-commercial-diagnostics');
  expect(
    document.schemaVersion === 2 &&
      document.evidenceValid === true &&
      document.comparisonPolicy.default === 'strict' &&
      document.comparisonPolicy.engineeringDiagnosticOnly === true,
    'Current strict commercial diagnostics are unavailable',
  );
  reader.bytes(document.sourcePlan.path, document.sourcePlan.sha256, 'diagnostic-source-plan');
  const commercialDiagnostics = {
    document,
    source: diagnosticSource,
    sha256: reader.sources.get(diagnosticSource).sha256,
  };
  const crossCheckSource = `${prefix}/evidence/reference-cross-check.json`;
  const crossCheckDocument = reader.json(crossCheckSource, undefined, 'current-native-comparison');
  commercialDiagnostics.openSees = {
    document: crossCheckDocument,
    source: crossCheckSource,
    sha256: reader.sources.get(crossCheckSource).sha256,
  };
  const cases = manifest.cases.map((entry) =>
    readResearchCase(
      reader,
      corpus,
      entry,
      plan.cases.find((c) => c.id === entry.id),
      commercialDiagnostics,
    ),
  );
  const summaries = cases.map((c) => c.summary);
  for (const stage of [
    'authored',
    'referenceReady',
    'nativeVerified',
    'inputReviewed',
    'accepted',
    'agentNotRun',
  ])
    expect(
      manifest.summary[stage] === summaries.filter((c) => c.status[stage]).length,
      `Manifest ${stage} count differs`,
    );
  const turns = summaries.reduce((sum, c) => sum + c.turnCount, 0),
    states = summaries.reduce((sum, c) => sum + c.stateCount, 0);
  expect(turns === 420 && states === 364, 'Frozen research corpus turn/state coverage differs');
  const publicInputReview = summarizePublicInputReviews(cases);
  const catalogue = catalogueProjection.buildResearchCatalogue({ planCases: plan.cases, sourceTasks, cases, taxonomy });
  const index = {
    schemaVersion: 1,
    corpusId: 'research-300',
    evaluatorVersion: evaluation.EVALUATOR_VERSION,
    summary: {
      ...manifest.summary,
      turns,
      states,
      ...(publicInputReview.total ? { publicInputReview } : {}),
    },
    cases: summaries,
    catalogue,
    sources: [...reader.sources.values()].sort((a, b) => a.source.localeCompare(b.source, 'en')),
  };
  return { index, cases, reader };
}
