# Research-300 deformation and concise MM inputs implementation plan

> **For agentic workers:** Use subagent-driven-development with independent scoped tasks; root coordinates integration. The user approved steps 1–3 in chat on 2026-10-16. Continue implementation without another approval round.

**Goal:** Restore full trustworthy node deformation, inventory every MM task, and serve concise yet physically equivalent public textual inputs for all 100 MM cases.

**Architecture:** Full native node translations are a display evidence field independent of scoring samples. Concise MM inputs form an explicit versioned presentation bound to the frozen case/source and original public inputs; historical numerical evidence retains its original hashes. The provider and viewer use the same current edition, while original manifest checks use an explicit frozen accessor.

**Tech Stack:** Existing Node/CommonJS provider and evaluator, Python authoring tools, React/TypeScript viewer, Playwright.

**Spec:** The accepted in-chat six-part proposal, limited by the user's instruction “先完成1-3部分把”. Implementation scope and task interfaces are recorded below.

## Global constraints

- Work locally; no model calls, remote solver execution, external publication or StructureClaw changes.
- Frozen cases, hidden models, reference requests, reference values, tolerances, original assets and evidence remain byte-identical.
- No image redraw, modality substitution, blind input-review claim, or agent trial in this phase.
- Every current public packet includes all necessary assumptions, units, signs and reporting definitions. Delayed clarification attachments stay delayed.
- Native deformation uses the designated engine/state/selection with exact evidence lineage. Missing unconstrained displacement values never become zero.
- All-zero responses, 2D inactive DOFs, PKPM missing-value sentinels, reused physical states, and commercial equivalence conventions are explicit.

## Review focus

- Full shape must be based on all native nodes, even when this turn requests one scalar.
- Commercial frozen evidence contains OpenSees diagnostics as well as true commercial outputs; wrong-engine substitution must reject.
- Five MM tasks release information in two turns; textual simplification must preserve genuine first-turn ambiguity.
- Compact tables must retain every original public fact and exact numeric property/assignment/load value.
- Revised prompts must have an edition binding in actual provider delivery and captured-run evaluation, while old native receipts remain immutable.

### Task 1: Native deformation and viewer

**Owner:** complete_deformation. **Files:** focused new viewer/scripts/native-displacements.mjs; viewer source result adapter/types/UI; state export hook and tests.

- [x] Reproduce and test missing full vectors with actual planar and spatial fixtures.
- [x] Bind complete native OpenSees/PKPM/YJK fields to engine, state, source model and selection.
- [x] Render automatic/manual scale, undeformed shape, coverage and evidence; export all supporting vectors.
- [x] Verify exact current-turn scoring subsets remain unchanged, malformed sources reject and all eligible state/selection coverage is audited.

### Task 2: Individual MM audit and concise content

**Owner:** mm_editorial. **Files:** scripts/research300/public_input_*; corpora/research-300/public-inputs/concise-v1/; docs/implementation/reviews/mm-inputs-20261016/.

- [x] Inspect public content and inventory all 100 tasks individually.
- [x] Generate short instructions preserving every requested output and intentional ambiguity.
- [x] Compact TXT and JSON appendices into readable lossless tables; preserve physics, units, local axes, analysis conditions and commercial conventions.
- [x] Retain all original visual attachments and per-turn release times.
- [x] Verify structured table roundtrip, textual fact preservation, deterministic edition, all-case coverage and before/after volume.

### Task 3: Actual provider delivery and edition binding

**Owner:** input_editions. **Files:** lib/public-input-edition.cjs; lib/corpus-provider.cjs; scripts/run-research300.cjs; tests.

- [x] Implement getFrozenPublicTurnInput (and frozen option) alongside default current MM inputs.
- [x] Validate current input bundle against original source/public hash, turn inventory, attachment paths/hashes/safety, and release times.
- [x] Publish inputEdition/publicInputSha256/inputBinding without private values; keep responseContract unchanged.
- [x] Reject stale or unbound captured inputs for revised cases while preserving frozen fixture behavior.

**Bundle contract:** concise-v1/manifest.json has schemaVersion, edition, cases with id/baseSourceHash/basePublicSha256/path/sha256. Each input.json has schemaVersion/edition/caseId/baseSourceHash and turns with id/instruction/attachments. Attachment source is frozen or edition, with name/path/sha256; additional public transformation binding records may be added by agreement of owners.

### Task 4: Integration and verification

**Owner:** root, after task owners release shared viewer files.

- [x] Verify original viewer manifest using frozen provider inputs, then project and copy the current input edition and its provenance.
- [x] Render concise textual tables readably, retaining original downloadable bytes and readable public response requirements.
- [x] Run provider/evaluator/runner, viewer unit/build and browser regression suites on the integrated worktree.
- [x] Review task changes and all-case content/visual coverage, then resolve material findings.
- [x] Verify frozen-corpus immutability and record evidence, commits and remaining work.
- [x] Integrate locally into work/research-next and refresh the existing loopback preview only after checks pass.
