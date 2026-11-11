# Research 300 Explorer Implementation Plan

> **For agentic workers:** Use subagent-driven-development for independent tasks, with source/scoring fidelity review and final browser/integration checks.

**Goal:** Show only the complete current 300-case benchmark with correct turn/state/engine data and review status.

**Architecture:** New data export contract and dedicated research UI reuse existing geometry/DXF primitives. Frozen quantities drive explicit discrete response plots. Source data is immutable; generated site is local and ignored by Git.

**Tech Stack:** Existing Node 22, React 19, TypeScript, Vite, Three.js, Playwright; Python existing MM checks. No new runtime dependencies.

**Spec:** docs/superpowers/specs/2026-10-15-research300-viewer-design.md

## Global Constraints

- Exactly 300 research cases; legacy inputs remain in repository but excluded from generated site.
- No changes to corpus cases, references, tolerances, manifest, receipts or historical reviews.
- Respect provider turn scope, null clarification state and requested units.
- Strict diagnostics and engineering allowances remain distinct; pending acceptance/trials stay pending.
- Local only; no remote models, solver runs, deploy or push.

## Review Focus

- Same case has reused state with different requested outputs/units: exporter + browser turn tests.
- Partial displacements, interior stations and duplicated side positions: response tests reject invented values/curves.
- Missing/stale native bindings: exporter refuses, never substitutes other engine.
- DXF source modality and unseen extra attachments: checker retains negative controls.
- Stale files survive previous export or static cache: exporter cleans only owned output and browser verifies no legacy routes.

### Task 1: Verified research-only export and types

Owned files: viewer/scripts/export-data.mjs; viewer/scripts/research-data.mjs if needed; viewer/src/research-types.ts; viewer/tests/data.test.mjs.

- [x] Write and run failing tests asserting corpusId research-300, exactly 300 IDs and no old files.
- [x] Implement the shared contract in the spec using loadCorpus/loadCase/getPublicTurnInput/getResponseContract and active manifests.
- [x] Verify every attachment byte/SHA, all model and reference bindings, current-turn scope and converted values.
- [x] Add fail-closed tests for stale/missing references, path traversal, old-output cleanup, engine substitution and STD-089 diagnostic status.
- [x] Run data tests and report red/green evidence; no commit until integration review.

### Task 2: Research catalogue/detail UI and browser coverage

Owned files: viewer/src/main.tsx; viewer/src/research-app.tsx; viewer/src/research-detail.tsx; viewer/src/research.css; viewer/tests/browser/*.spec.ts; viewer/README.md; viewer/index.html.

- [x] Replace old browser expectations with research-only catalogue and current-turn/state checks.
- [x] Implement search/filter/pagination/deep links and geometry thumbnails from the shared export contract.
- [x] Implement exact instruction/attachment panels, clarification handling, geometry selection, status/diagnostics/provenance, and ResearchResults integration.
- [x] Ensure all scheduled attachments readable/downloadable, SVG/PNG inspectable, DXF interactive, no future-turn reference shown.
- [x] Cover all 300 routes/420 turns plus native commercial, units, state changes, mobile, exports, static subpath and WebGL fallback.
- [x] Run build/browser checks with root-provided dependencies; address visual failures.

### Task 3: MM architectural-checker compatibility

Owned files: scripts/research300/mm_b_architectural_checks.py and focused tests; current recheck receipt under new docs/implementation/reviews path if useful.

- [x] Capture six current failures and add regression tests for the exact commercial v2 convention attachment.
- [x] Permit only correctly declared/validated commercial convention, keep forbidden clean structural geometry and arbitrary extra files rejected.
- [x] Run all relevant architectural/visual checks and negative controls; no authored-file edits or blind-review promotion.

### Task 4: Frozen response visualization and integration (root)

Owned files: viewer/src/research-results.tsx; viewer/src/research-response.ts; viewer/tests/research-response.test.mjs; dependency/test configuration and legacy unit fixture helper if needed.

- [x] Test signed values, component units, node/member scope, station sides, partial vectors, missing values and non-mutating output.
- [x] Implement canonical selection, node/discrete-station diagram, qualified deformation and source-labelled SVG/PNG/JSON exports using shared types.
- [x] Preserve useful pure legacy math regression tests without using legacy generated site data.
- [x] Run all Node/Python/build/browser tests, inspect screenshots, audit original hashes and generated coverage.
- [x] Independent final code/data review, fix findings, local commit and integrate into current user branch without push.

## Execution ledger

- User explicitly requested complete handling and research-only display after the concrete gap report. Routine design and implementation proceed autonomously under that authorization.
- Baseline dfb8cb3; current source corpus has 300 cases, 420 turns, 364 states, 300 nativeVerified, 0 accepted/inputReviewed, and two distinct strict differences in STD-089.
- Existing viewer data-only check passes for old150, proving the migration starts from a legacy exporter. MM-B visual check fails six whitelist/coverage checks on MM-082/MM-086.
- Isolated worktree: .worktrees/research300-viewer, branch bench300/viewer-v3. Parallel tasks have disjoint file ownership; root coordinates interfaces and final verification.

- Research exporter: 300 cases / 420 turns / 364 states / 10,080 verified sources; data review found no defects. Signed zero is preserved in source models, frozen values and downloads.
- Viewer suite: 37 Node tests passed; focused MM checker 13 tests, full MM-B visual 50 cases/158 PNG-SVG pairs/6 DXFs/3 negative controls, and architectural 6 cases/28 negative controls/6 actual provider turns passed.
- All 10,638 tracked files under corpora, scenarios and fixtures (395,420,619 bytes) match baseline Git objects. No frozen corpus changes.
- Independent visualization review found and resolved coincident marker overlap, missing deformation export inputs, missing local-axis export context, and React SVG title children. Dense markers are bounded inside the figure; current-turn units are preserved.
- Geometry audit expanded Task 4: restored 20 nodal moments, four partial distributed-load intervals, and removed 1,434 support symbols caused only by inactive-DOF suppression. Scene, thumbnails and response figures share physical support classification. Original restraint flags remain inspectable.
- Full local production build passed; final browser suite passed 16/16, including all 300 cases / 420 turns and rejection of all 150 legacy routes. Desktop/mobile, DXF, support/load and result screenshots inspected. No remote models or numerical engines invoked.

- Integrated locally on 2026-10-16: feature commit `fcc3a1b` fast-forwarded into `work/research-next`. Main workspace generated data and served runtime hashes match the tested build. Main TypeScript check, 21 focused tests, and 3 browser smoke tests passed; local preview serves research-300 at `http://127.0.0.1:4173/`. No push.
