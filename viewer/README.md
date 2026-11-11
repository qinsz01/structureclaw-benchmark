# StructureClaw Research 300 Explorer

本地只读基准审阅工具，展示完整 **research-300：300 个案例、420 轮对话、364 个物理状态**。公开输入、冻结参考与核验来源分别查看。案例仅使用 `STD-`、`INT-`、`MM-` 编号；仓库中的旧案例不进入此站点。

A local, read-only review tool for **research-300: 300 cases, 420 turns, and 364 physical states**. Public inputs, frozen references, and review evidence have separate views. The generated site contains only the `STD-`, `INT-`, and `MM-` research cases.

## Run locally

Requires Node.js 20.19+ or 22.12+ and local Python 3 for public-input correspondence checks. From `viewer/`:

```sh
npm ci
npm run dev
```

Open **http://127.0.0.1:4173/**. The server binds to localhost and uses a fixed port. `npm run dev -- --port 4174` selects another port.

```sh
npm run build
npm run preview
```

The production build uses relative asset URLs and can be reviewed under a static subdirectory such as `/explorer/`. There are no model calls, solver runs, or external runtime services. Build output is a benchmark-owner review artifact containing answers; it must not be provided to an evaluated model as a public-input endpoint.

## Explore the corpus

- Search the full catalogue and filter by family, original input language, and actual target engine. Filters and pagination are preserved in the catalogue link.
- Turn links use the exact turn ID: `#/case/INT-097?turn=t2&state=1&tab=reference`. The turn determines the physical state. Reusing a model state does not reuse another turn's requested outputs or units.
- Public input is the default view. It shows the concise current instruction and its scheduled input file. All 300 cases use the same canonical public-input directory; every MM turn has one PNG or DXF, with properties and notes inside the drawing. STD/INT turns have at most one readable appendix. PNG can be enlarged; DXF supports zoom, pan, layers, and downloads. Public input JSON downloads omit internal bindings and source paths. The catalogue also downloads the standalone task package.
- Clarification turns have no model or numerical reference panel. A URL cannot select a future state while retaining a clarification turn.
- The reference view shows the exact model, with Three.js navigation, loads, supports, dimensions, object properties, raw model JSON, and PNG export. A static model preview remains available when WebGL is unavailable.
- Response figures display recorded node components and member stations with signed values, units, position, side, and selection metadata. Discrete node deformation uses complete native translations from the designated engine, separately from the requested scoring samples. Automatic and manual magnification show the original and displaced nodes with straight member connections; node/member coverage and source evidence are disclosed. Proven PKPM fixed-base constraint zeros are labeled separately from native recorded values. No continuous beam or stress field is inferred.
- SVG, PNG, and JSON response exports retain case, turn, state, target engine, reference source hashes, and the full displayed deformation evidence. The exact-value table also exposes the current turn's complete frozen reference and derived quantities.

切换中英文界面不会翻译原始题目。图中荷载箭头是示意；材料、截面、局部轴与荷载单位须以原始字段为准。

Changing the UI language does not translate the original task. Load arrows are schematic. Interpret model units using the original material, section, axis, and load fields.

Maintainer mode is opt-in in the global toolbar. It reveals response contracts, bindings, receipt provenance, acceptance stages, and review diagnostics; these do not appear on the default task surface.

## Codex trial results

The existing catalogue now includes the sealed **300-case / 420-turn Codex trial**: 282 cases and 402 turns passed. Use the Codex result filter, or select **Codex answer & evaluation** on a case to inspect the question actually received, the original answer, generated figures/files and per-turn evaluation gates. Answer tables keep signed values and units. Original answer text and JSON are downloadable. The viewer reads the committed, hash-verified archive parts; it does not depend on local solver scratch directories or run any models.

Historical scores remain unchanged. INT-056 has a separate version selector for its fresh three-turn trial after the public wording amendment; the selected version is retained in the URL. STD-080 shows the separate PKPM adapter regression (396 quantities passed), rather than claiming a new candidate answer score. These Codex validations do not change the manifest's formal StructureClaw trial or final acceptance status. Interaction reviews are by the evaluator author; no external blinded acceptance is claimed.

目录新增 Codex 结果筛选；案例内的「Codex 作答与评测」按轮展示当时题面、原始作答、生成图件和评分依据。历史 282/300 成绩与后续修复验证分开保留，查看版本可随链接分享。页面仍仅在本地运行，不推送仓库或发布网站。

## Status and numerical evidence

Authored, reference-ready, native-verified, input-reviewed, accepted, and model-trial status are separate facts from the current manifest. The current corpus has **300 native-verified cases, 0 input-reviewed cases, 0 accepted cases, and 300 model trials not run**. Historical source-plan wording is retained only in explicit reviewer disclosures and does not override the current manifest.

The scoring source is identified for each state. OpenSees cases use their frozen independent matrix scoring reference and separate native verification evidence. Commercial cases use their own PKPM or YJK native scoring reference. No result is substituted from another engine.

Review diagnostics distinguish the original strict tolerances from the engineering precision policy. **STD-089 retains two distinct M3 strict differences**; engineering diagnostic agreement does not establish a strict pass or final acceptance. Exact native values, tolerances, and source records remain available for inspection.

## Data and checks

`npm run data` regenerates ignored `public/data/` from the research corpus provider, response contracts, current manifest, bound reference files, and review evidence. Source bytes and hashes are verified, attachments are copied unchanged, and stale or missing source bindings stop export. The exporter owns only the generated data directory; original corpus files and legacy repository scenarios remain intact.

Frozen numerical evidence keeps its original source binding. Current inputs have a separate [public-input binding](../docs/public-inputs.md); the exporter validates both. The individual MM inventory records retained facts and remaining drawing work. `node scripts/audit-deformation.mjs /tmp/deformation-coverage.json` reproduces the complete native coverage audit without running solvers. `BENCH_VIEWER_PORT=4180 npm run test:browser` selects an isolated browser-test preview port.

```sh
npm test
npm run build
npx playwright install chromium
npm run test:browser
```

Data tests verify all cases, states, turns, attachments, units, scope, provenance, and research-only output. Browser tests visit all 300 cases and 420 turns and exercise clarification isolation, state changes, query units, commercial precision, image/DXF attachments, exports, mobile layout, WebGL fallback, and a static subdirectory. Screenshots and downloaded verification artifacts are written to ignored `test-results/`.
