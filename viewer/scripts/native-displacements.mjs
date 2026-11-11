import { isDeepStrictEqual } from 'node:util';

const require = (condition, message) => {
  if (!condition) throw Error(`Native deformation: ${message}`);
};
const equal = (a, b, message) => require(isDeepStrictEqual(a, b), message);
const finite = (value) => typeof value === 'number' && Number.isFinite(value);
const same = (a, b) => a?.kind === b?.kind && a?.id === b?.id;
const pointer = (value) => String(value).replace(/~/g, '~0').replace(/\//g, '~1');
const xyz = (node) => ['x', 'y', 'z'].map((k) => node[k]);
const close = (a, b, tolerance = 1e-10) =>
  Array.isArray(a) &&
  a.length === 3 &&
  a.every((v, i) => finite(v) && Math.abs(v - b[i]) <= tolerance);
function factors(model, selection) {
  if (selection.kind === 'case') {
    require(model.load_cases.filter((c) => c.id === selection.id).length ===
      1, 'unknown case selection');
    return { [selection.id]: 1 };
  }
  require(selection.kind === 'combination', 'unknown selection kind');
  const rows = model.load_combinations.filter((c) => c.id === selection.id);
  require(rows.length === 1 &&
    Object.values(rows[0].factors).every(finite), 'unknown combination selection');
  return rows[0].factors;
}

/** Called only after readResearchCase verifies the frozen inventory, qualification and receipts.
 * This second binding check prevents callers from mixing a model, engine, state or selection.
 * No solver is run and no requested scoring row is used as a full displacement field.
 */
export function readNativeDisplacementFields(context) {
  const {
    reader,
    base,
    caseId,
    engine,
    sourceHash,
    state,
    model,
    modelSource,
    selections,
    receipts,
  } = context;
  equal(
    reader.json(modelSource.source, modelSource.sha256, 'deformation-model'),
    model,
    'model binding differs',
  );
  return selections.map((selection) => {
    const matches = receipts.filter((r) => r.state === state && same(r.selection, selection));
    require(matches.length === 1, 'missing or duplicate receipt selection binding');
    const receipt = matches[0],
      sources = new Map([[modelSource.source, modelSource]]);
    const body = reader.json(receipt.source, receipt.sha256, 'deformation-native-receipt');
    require(body.engine === engine &&
      body.state === state &&
      same(body.selection, selection) &&
      body.modelSha256 === modelSource.sha256 &&
      body.status === 'succeeded' &&
      body.runId &&
      body.engineVersion, 'receipt engine/state/model/selection binding differs');
    if (body.sourceHash !== undefined)
      require(body.sourceHash === sourceHash, 'receipt sourceHash binding differs');
    sources.set(receipt.source, reader.sources.get(receipt.source));
    const artifacts = new Map();
    for (const a of body.artifacts) {
      require(!artifacts.has(a.path), 'duplicate receipt artifact binding');
      artifacts.set(a.path, a);
    }
    const bytes = (name, expectedHash) => {
      const a = artifacts.get(name);
      require(a &&
        (!expectedHash || a.sha256 === expectedHash), `unbound receipt artifact: ${name}`);
      const result = reader.bytes(`${base}/${name}`, a.sha256, 'native-deformation-evidence');
      sources.set(result.descriptor.source, result.descriptor);
      return result;
    };
    const read = (name, expectedHash) => {
      const result = bytes(name, expectedHash);
      return {
        data: JSON.parse(result.bytes.toString('utf8').replace(/^\uFEFF/, '')),
        source: result.descriptor,
      };
    };
    const quantities = [],
      unavailable = [];
    const add = (node, j, value, origin, rawTrace) => {
      const component = ['ux', 'uy', 'uz'][j];
      if (!finite(value)) {
        unavailable.push({ nodeId: node.id, component, reason: 'native component unavailable' });
        return;
      }
      quantities.push({
        id: `native-s${state}-${selection.kind}-${selection.id}-${node.id}-${component}`,
        selection,
        location: { kind: 'node', id: node.id },
        component,
        value,
        unit: 'm',
        origin,
        rawTrace,
      });
    };
    const sourceFactors = factors(model, selection);
    if (engine === 'OpenSees') {
      const { data: raw, source } = read('native-raw-responses.json');
      require(raw.id === caseId, 'OpenSees case binding differs');
      const runs = raw.runs
        .map((run, index) => ({ run, index }))
        .filter(({ run }) => run.state === state && same(run.selection, selection));
      require(runs.length === 1, 'OpenSees state/selection binding differs');
      const { run, index } = runs[0],
        response = run.responses;
      equal(run.factors, sourceFactors, 'OpenSees source selection factors differ');
      require(response.runtime?.module === 'openseespy.opensees' &&
        response.runtime.version === body.engineVersion &&
        response.analysisReturnCode === 0, 'OpenSees execution binding differs');
      require(response.nativeInput?.nativeNdm === 3 &&
        response.nativeInput.nativeNdf === 6, 'OpenSees translation slot mapping differs');
      for (const node of model.nodes) {
        const input = response.nativeInput.nodes[node.id],
          result = response.nodes[node.id];
        require(input?.authored &&
          close(input.xyz, xyz(node)), `OpenSees node mapping differs: ${node.id}`);
        if (result) require(result.tag === input.tag, `OpenSees node tag differs: ${node.id}`);
        for (let j = 0; j < 3; j++)
          add(node, j, result?.displacement?.[j], 'native-recorded', {
            source,
            jsonPointer: `/runs/${index}/responses/nodes/${pointer(node.id)}/displacement/${j}`,
            nativeNode: input.tag,
            nativeUnit: 'm',
          });
      }
    } else {
      require(['PKPM', 'YJK'].includes(engine), 'unsupported engine binding');
      const { data: candidate, source: candidateSource } = read('native-commercial/candidate.json');
      require(candidate.id === caseId &&
        candidate.sourceHash === sourceHash &&
        candidate.referenceKind ===
          `native-${engine.toLowerCase()}-candidate`, 'commercial candidate engine/case/source binding differs');
      const candidates = candidate.states.filter((s) => s.state === state);
      require(candidates.length === 1, 'commercial state binding differs');
      const native = candidates[0];
      require((native.sourceModelSha256 || native.originalModelSha256) === modelSource.sha256 &&
        `${base}/${native.model}` === modelSource.source &&
        candidate.inputHashes[native.model] ===
          modelSource.sha256, 'commercial model binding differs');
      const evidenceName = (name) => `native-commercial/evidence/${name}`;
      if (engine === 'PKPM') {
        require(candidate.solver?.product === 'PKPM' &&
          body.runId.endsWith('/' + native.nativeRun), 'PKPM native run binding differs');
        const execution = native.selectionExecutions.filter((e) => same(e.selection, selection));
        require(execution.length === 1, 'PKPM selection execution binding differs');
        equal(execution[0].sourceFactors, sourceFactors, 'PKPM source factors differ');
        equal(body.sourceFactors, sourceFactors, 'PKPM receipt factors differ');
        equal(
          body.nativeBasicFactors,
          execution[0].nativeBasicFactors,
          'PKPM native case factors differ',
        );
        const nativeFactors = execution[0].nativeBasicFactors;
        require(Object.keys(nativeFactors).length &&
          Object.values(nativeFactors).every(finite), 'invalid PKPM native factors');
        const bound = candidate.nativeArtifacts[native.nativeRun];
        const artifact = (name) => {
          require(bound?.[name], `PKPM missing artifact ${name}`);
          return read(evidenceName(bound[name].path), bound[name].sha256);
        };
        const sdk = artifact('sdk-results.json'),
          packet = artifact('physical-input.json'),
          inputReceipt = artifact('frame-input-receipt.json');
        require(inputReceipt.data.inputSha256 ===
          packet.source.sha256, 'PKPM native input hash binding differs');
        require(native.nativeStageReceipts.some(
          (s) => s.stage === 'analysis',
        ), 'PKPM analysis receipt missing');
        for (const stage of native.nativeStageReceipts) {
          const r = read(evidenceName(stage.receiptPath), stage.receiptSha256).data;
          require(r.status === 'completed' &&
            r.returncode === 0 &&
            r.executableSha256 === stage.executableSha256, 'PKPM native stage binding differs');
        }
        if (packet.data.selection.kind === 'basic-cases') {
          const expected = Object.fromEntries(
            Object.entries(sourceFactors).map(([id, factor]) => [
              packet.data.selection.nativeCases[id]?.name,
              factor,
            ]),
          );
          equal(nativeFactors, expected, 'PKPM basic case mapping differs');
        } else {
          require(same(
            packet.data.selection,
            selection,
          ), 'PKPM physical selection binding differs');
          equal(
            packet.data.selection.factors,
            sourceFactors,
            'PKPM physical selection factors differ',
          );
          equal(nativeFactors, { DL: 1 }, 'PKPM physical native case mapping differs');
        }
        const used = new Set();
        for (const [ni, node] of model.nodes.entries()) {
          const found = sdk.data.nodes
            .map((n, index) => ({ n, index }))
            .filter(({ n }) =>
              close(
                n.coordinates?.map((v) => v / 1000),
                xyz(node),
                1e-6,
              ),
            );
          require(found.length === 1 &&
            !used.has(found[0].index), `PKPM node mapping differs: ${node.id}`);
          const { n, index } = found[0];
          used.add(index);
          const pi = packet.data.nodes.findIndex((n) => n.id === node.id),
            physical = packet.data.nodes[pi];
          require(physical &&
            close(xyz(physical), xyz(node)), 'PKPM physical node mapping differs');
          equal(physical.restraints, node.restraints, 'PKPM physical restraints differ');
          const column = model.elements.find((e) => e.type === 'column' && e.nodes[0] === node.id);
          const ri = inputReceipt.data.members.findIndex((m) => m.sourceId === column?.id),
            readback = inputReceipt.data.members[ri];
          const fixed =
            node.restraints?.length === 6 &&
            node.restraints.every((v) => v === true) &&
            n.floor === 0 &&
            readback?.kind === 'column' &&
            readback.floor === 1 &&
            readback.specialReadback?.IDSp_Constrain_Support === 0 &&
            !inputReceipt.data.constraints?.some((c) => c.sourceNodeId === node.id);
          for (let j = 0; j < 3; j++) {
            const terms = Object.entries(nativeFactors)
              .filter(([, f]) => f !== 0)
              .map(([nativeCase, factor]) => ({
                nativeCase,
                factor,
                rawValue: n.cases[nativeCase]?.[j],
                jsonPointer: `/nodes/${index}/cases/${pointer(nativeCase)}/${j}`,
              }));
            const missing = terms.some((t) => !finite(t.rawValue) || t.rawValue === -99999);
            const sentinelOnly =
              terms.every((t) => finite(t.rawValue)) && terms.some((t) => t.rawValue === -99999);
            const derived = missing && sentinelOnly && fixed;
            const value = missing
              ? derived
                ? 0
                : NaN
              : terms.map((t) => t.factor * t.rawValue).reduce((a, b) => a + b);
            add(node, j, value, derived ? 'explicit-constraint-zero' : 'native-recorded', {
              source: sdk.source,
              terms,
              nativeUnit: 'm',
              coordinatesMm: n.coordinates,
              sourceFactors,
              nativeBasicFactors: nativeFactors,
              ...(derived
                ? {
                    reason:
                      'SDK sentinel unavailable; zero derived from explicitly fixed model and verified native default-fixed base support',
                    constraintSources: [
                      { ...modelSource, jsonPointer: `/nodes/${ni}/restraints/${j}` },
                      { ...packet.source, jsonPointer: `/nodes/${pi}/restraints/${j}` },
                      {
                        ...inputReceipt.source,
                        jsonPointer: `/members/${ri}/specialReadback/IDSp_Constrain_Support`,
                      },
                    ],
                  }
                : {}),
            });
          }
        }
      } else {
        const descriptors = native.evidenceArtifacts;
        const artifact = (suffix) => {
          const matches = descriptors.filter((a) => a.path.endsWith('/' + suffix));
          require(matches.length === 1, `YJK artifact binding missing or ambiguous: ${suffix}`);
          return read(evidenceName(matches[0].path), matches[0].sha256);
        };
        const sdk = artifact('read-results.json'),
          mapping = artifact('mapping.json');
        const feDescriptor = descriptors.find((a) => a.path.endsWith('/fea.dat'));
        require(feDescriptor, 'YJK native FE input missing');
        const fe = bytes(evidenceName(feDescriptor.path), feDescriptor.sha256),
          coordinates = new Map();
        let section = '';
        for (const line of fe.bytes.toString('utf8').split(/\r?\n/)) {
          const trimmed = line.trim();
          if (trimmed.startsWith('*')) section = trimmed.split(/\s/)[0];
          if (section === '*NODE') {
            const m = trimmed.match(/^(\d+)\s+.*\bC=([^\s&]+)/);
            if (m) coordinates.set(Number(m[1]), m[2].split(',').map(Number));
          }
        }
        const audits = descriptors.filter((a) => /\/audit-\d+\.json$/.test(a.path));
        require(audits.length, 'YJK native input audit missing');
        for (const a of audits) {
          const audit = read(evidenceName(a.path), a.sha256).data;
          require(audit.case === caseId &&
            audit.state === state &&
            audit.source_sha256 === modelSource.sha256 &&
            (audit.native_input_sha256 || audit.native_fe_sha256) === feDescriptor.sha256 &&
            audit.native_result_sha256 === sdk.source.sha256 &&
            !audit.representation_failures?.length, 'YJK native audit binding differs');
          equal(
            audit.source_node_map || audit.node_map,
            native.sourceNodeMap,
            'YJK audited node mapping differs',
          );
        }
        require(new Set(Object.values(native.sourceNodeMap)).size ===
          Object.keys(native.sourceNodeMap).length, 'YJK duplicate native node mapping');
        const nativeCases = Object.entries(sourceFactors)
          .filter(([, f]) => f !== 0)
          .map(([id, factor]) => {
            const matches = mapping.data.load_cases.filter((c) => c.source_case === id);
            require(matches.length === 1, 'YJK source case mapping differs');
            const matchesNative = sdk.data.cases
              .map((c, index) => ({ c, index }))
              .filter(
                ({ c }) =>
                  c.name === matches[0].native_name && c.analysis_case === matches[0].native_kind,
              );
            require(matchesNative.length === 1, 'YJK native case mapping differs');
            return { ...matchesNative[0], factor, sourceCase: id };
          });
        for (const node of model.nodes) {
          const tag = native.sourceNodeMap[node.id];
          require(close(
            coordinates.get(tag),
            xyz(node),
          ), `YJK native coordinate mapping differs: ${node.id}`);
          for (let j = 0; j < 3; j++) {
            const terms = nativeCases.map(({ c, index, factor, sourceCase }) => ({
              sourceCase,
              nativeCase: c.name,
              nativeDesignCase: c.id,
              nativeAnalysisCase: c.analysis_case,
              factor,
              rawValue: c.nodes[String(tag)]?.displacement?.[j],
              jsonPointer: `/cases/${index}/nodes/${tag}/displacement/${j}`,
            }));
            const value = terms.every((t) => finite(t.rawValue))
              ? terms.map((t) => t.factor * t.rawValue).reduce((a, b) => a + b)
              : NaN;
            add(node, j, value, 'native-recorded', {
              source: sdk.source,
              terms,
              nativeNode: tag,
              nativeUnit: 'm',
              mappingSource: candidateSource,
              mappingPointer: `/states/${candidate.states.indexOf(native)}/sourceNodeMap/${pointer(node.id)}`,
              sourceFactors,
            });
          }
        }
      }
    }
    const complete = new Set(
      model.nodes
        .filter((n) => quantities.filter((q) => q.location.id === n.id).length === 3)
        .map((n) => n.id),
    );
    return {
      schemaVersion: 1,
      purpose: 'native-node-deformation-only',
      caseId,
      engine,
      state,
      selection,
      sourceHash,
      modelSha256: modelSource.sha256,
      receipt: {
        source: receipt.source,
        sha256: receipt.sha256,
        runId: body.runId,
        engineVersion: body.engineVersion,
      },
      sources: [...sources.values()],
      quantities,
      coverage: {
        totalNodes: model.nodes.length,
        completeNodes: complete.size,
        totalElements: model.elements.length,
        completeElements: model.elements.filter((e) => e.nodes.every((id) => complete.has(id)))
          .length,
        missingNodeIds: model.nodes.filter((n) => !complete.has(n.id)).map((n) => n.id),
        missingComponents: unavailable,
        nativeComponents: quantities.filter((q) => q.origin === 'native-recorded').length,
        constraintComponents: quantities.filter((q) => q.origin === 'explicit-constraint-zero')
          .length,
      },
    };
  });
}
