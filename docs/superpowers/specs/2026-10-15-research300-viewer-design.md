# Research 300 explorer migration

User request: completely handle the benchmark visualization and show only the complete new benchmark. The previous numerical investigation remains authoritative; this work does not claim the two strict discrepancies or pending blind/model evaluations are complete.

## Outcome and scope

The existing local read-only React explorer will display exactly the 300 research-300 cases, all 420 turns and all 364 physical states. Its catalogue will have search, family, language and actual engine filters; detail routes use STD/INT/MM identifiers. Legacy scenarios and fixtures remain unchanged in the repository but never appear in generated explorer output, navigation, figures, or the default catalogue.

Each turn shows its exact public instruction, scheduled attachments, and public response contract. Clarification turns have no reference geometry or numerical panel. Reference and evaluation panels are explicitly benchmark-owner review views, distinct from the public input; this local static explorer must not be used as an evaluated-model input endpoint.

The exporter uses the existing corpus provider and response scoping, the frozen manifest, active independent-reference scoring quantities, native qualification receipts, native reference metadata, and active numerical comparison diagnostics. It validates all used source hashes and fails on stale/missing bindings. It never falls back to legacy fixtures or another engine. It exports raw scoring reference rows with signed values/units/tolerances, derived values, state and selection identities, current-turn requested-unit conversion, and trace/provenance. The same-engine native reference is distinguished from the scoring/independent diagnostic where appropriate.

Geometry uses the actual model-state file. Reuse the existing Three.js scene, static fallback, thumbnail and DXF widgets. Requested responses get a dedicated vector diagram supporting node components and member station components N/V2/V3/T/M2/M3; missing values are gray/absent, with exact station/side/axis metadata. Deformation is available only from complete compatible displacement vectors and is labelled as discrete-node display. No invented continuous beam or stress contours, Euler–Bernoulli assumption for Timoshenko cases, or replacement commercial data.

Show authored, reference-ready, native-verified, input-reviewed, accepted, and agent-not-run as separate facts. Show v3 frozen strict tolerance and engineering-only diagnostics separately, including STD-089's two distinct failures. Source-plan historical descriptions do not override current statuses.

Fix the architectural-DXF checker to allow the exact validated new commercial convention attachment while preserving all modality, attachment and negative controls. Recheck current image/DXF/source bindings without rewriting historical reviews or claiming blind reconstruction.

## Shared data interface (viewer/src/research-types.ts)

`ResearchIndex`: schemaVersion=1, corpusId='research-300', evaluatorVersion, summary (manifest summary plus turns, states), cases: ResearchCaseSummary[], sources: SourceFile[].

`ResearchCaseSummary`: id, description, family, locale ('zh'|'en'), engine ('OpenSees'|'PKPM'|'YJK'), structure, modality, turnCount, stateCount, sourceHash, status (manifest stage booleans), strictComparison ('pass'|'difference'|'not-available').

`ResearchCaseDetail`: schemaVersion, corpusId, id, description, family, locale, engine, sourceHash, status, turns: ResearchTurn[], states: ResearchState[], acceptance (raw), diagnostics (raw or null), sources: SourceFile[], contract (raw). Original contract is available only in explicit reviewer/source disclosure.

`ResearchTurn`: id, state:number|null, expectation, instruction, attachments: ResearchAttachment[], responseContract (raw), quantities: ResearchQuantity[], derived: ResearchDerived[], requiredOutputs (raw[]), unresolvedFields (unknown[]). quantities and derived are restricted to the current public response contract, with turn-specific requested units; sourceValue/sourceUnit retain frozen values. No clarify turn quantities or state references.

`ResearchAttachment`: name, path (relative generated data URL), source (repo-relative), sha256, bytes, mimeType.

`ResearchState`: state:number, modelPath (models/ID-sN.json), modelSha256, reference:{source,sha256,kind,solver}, quantities (all original frozen), derived (all original frozen), selections:{kind,id}[], receipts (raw[]), nativeReference (source descriptor or null). Models JSON: {caseId,state,model:<unchanged Model>,source,sha256}.

`ResearchQuantity`: id, selection:{kind:'case'|'combination',id}, location:{kind:'node'|'member',id,positionM?,side?}, component, value, unit, tolerance:{absolute,relative}, sourceValue?,sourceUnit?, rawTrace?,engineeringPrecision?. Extra frozen properties preserved.

`ResearchDerived`: id, value, unit, operation, operands?, tolerance?, governingOperand?, governingSelection?, sourceValue?,sourceUnit?; preserve all frozen metadata.

`SourceFile`: source (repo-relative), sha256, path? (optional exported source URL), role?. Status: authored,referenceReady,nativeVerified,inputReviewed,accepted,agentNotRun booleans.

`thumbnails.json`: map of ID-sN to unchanged Geometry. `cases/ID.json` contains ResearchCaseDetail. No legacy models or case IDs in generated output.

## UI/component contract

New main entry renders `ResearchApp` from research-app.tsx. App/detail/data tabs are owned by the UI task. It reuses existing scene.tsx/drawing.tsx/thumbnail.tsx and existing global CSS. New research.css is UI-owned.

Root supplies `ResearchResults` from research-results.tsx with props `{model: Model, quantities: ResearchQuantity[], derived: ResearchDerived[], locale: Locale, caseId: string, state: number, engine: string}`. This component owns selection and component controls, exact quantity/derived tables, vector diagrams, provenance and SVG/PNG/JSON exports. It only receives the current-turn quantities.

## Validation

Data tests cover every case/turn/state, exact raw attachments and references, state/turn isolation, unit conversions, provenance freshness, legacy exclusion, all engines and STD-089 diagnostic distinction. Browser tests visit all 300 cases and 420 turns and exercise images, DXF layers, geometry, response diagrams, downloads, clarify-to-analyze transitions, different states/units, filters, deep links, mobile and no-WebGL fallback. Visual screenshots are inspected. Original corpus/manifest/receipt hashes must remain byte-identical. Build and static subdirectory serving must pass. Local only, no push/publish, no remote numerical runs or model requests.
