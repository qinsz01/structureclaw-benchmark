# StructureClaw Benchmark

[中文](README_CN.md)

Run records, raw model sessions and native solver evidence are archived outside this repository and are not version-controlled.

The Research300 v3 engineering edition
contains 300 tasks and 560 turns, with a 30/60/120/90 designed difficulty distribution
and 90 coupled engineering decision tasks. Its isolated Codex development calibration,
native qualification and remaining formal-experiment requirements are recorded separately.

The complete Codex validation
now contains all 300 fresh case conversations and 560 delivered turns. Reviewed grading
passes 483 turns and 263 complete cases; 57 evaluator false rejections were corrected
without changing answers or numerical tolerances. The original grade, remaining input
errors, raw answers and Excel review are retained. This run consumes the original holdout.

The separate Research300 v2 edition
reorganizes all 300 tasks into 540 turns, including 60 project-based adaptations
and a 60/120/90/30 designed difficulty distribution. Its inputs, references,
qualification and remaining candidate-trial requirements are recorded separately.
The default commands and historical scores below still refer to the original edition.

300 structural engineering tasks in Chinese and English: 100 standard workflows,
100 interactive tasks, and 100 multimodal reconstruction tasks. The benchmark has
420 conversation turns and uses OpenSees, PKPM, and YJK.

All 300 cases are reference-ready with verified native evidence. Independent
blind review of the current inputs and candidate model trials remain pending;
the current StructureClaw also needs a new experiment freeze. See the
current readiness audit
for checks, known cross-engine differences and remaining experiment requirements.
The backend and Codex input precheck
adds the full backend regression, Windows process tests and 12 public-input reconstruction cases.
New input reviews use [the v2 protocol](docs/public-input-review-protocol-v2.md) through
`npm run review:inputs -- export|seal|grade|verify ...`; the v1 CLI remains available for historical replay.
The v2.1 stress-test follow-up
records further fixes and adversarial regression checks while retaining the v2 packet contract.

The isolated [section-diversity candidate edition](docs/section-diversity.md) supplies
300 new input bundles, varying author-completed sections in 267 cases and retaining
33 dimension-constrained or special-section controls. It has separate source bindings
and numerical checks; the default corpus and historical Codex scores still refer to the original edition.

## Task inputs

Export the current tasks to a standalone directory:

```sh
npm ci
npm run export:research300 -- --output /tmp/structureclaw-benchmark
```

The export contains a case index, each task's ordered instructions, and its input
files. Each multimodal turn provides **one drawing: PNG or DXF**. Materials,
sections, loads, and necessary notes are included in that drawing. Standard and
interactive tasks use at most one readable input table per turn. Later turns
release only their scheduled information.

The task package contains no answers, scoring records, checksums, or internal
review metadata. Use it when supplying inputs to a model.

## Preview

```sh
cd viewer
npm ci
npm run build
npm run preview
```

Open <http://127.0.0.1:4173/>. The viewer shows tasks and reference results.
Maintainer mode exposes validation and provenance when needed. The viewer
contains answers and is separate from the task package.

## Evaluation

Evaluation checks physical model fidelity, execution with the designated engine,
requested signed quantities and units, interaction behavior, and figures.
Use the same entry point for Codex event logs and StructureClaw saved results:

```sh
npm run prepare:evaluation -- --case STD-001 --output /tmp/bench-STD-001
npm run evaluate -- --input /path/to/result.json --case STD-001 \
  --context /tmp/bench-STD-001/capture-context.json --output /tmp/assessment.json
```

Preparation releases the first turn by default. For a later turn, prepare a new
directory with `--turn t2` (using the case's exact turn ID); it contains only
history through that turn. Give only its `agent-input/` to the evaluated system
and keep future packets, capture context and reference data inaccessible.
Codex JSONL can be paired with its actual model and solver state using `--state`.
See [supported result formats and capture instructions](docs/result-adapters.md)
for Codex, StructureClaw states, conversations, SSE and run archives. The
[Research 300 guide](docs/research-300.md) explains reference qualification and
evaluation evidence.

All exports, evaluation and preview use the same [current public inputs](docs/public-inputs.md)
under `corpora/research-300/public-inputs/`. Inputs have no selectable editions;
missing or invalid files stop delivery. Original sources and audit evidence remain
available for provenance and historical reproduction.
The [classification guide](docs/research300-classification.md), [current workbook](planning/releases/StructureClaw_Benchmark_300题_当前版.xlsx),
and [catalogue JSON](planning/releases/research300-catalogue.json) share the same classification and counting rules as the preview.
Run `npm run catalogue:research300` to refresh the current release, or `npm run check:catalogue` to detect stale exports.
The workbook in `planning/sources/` remains the original planning archive.
The legacy scoring contract is documented in [SPEC.md](SPEC.md).

## License

MIT
