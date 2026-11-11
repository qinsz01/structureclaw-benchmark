# Research 300 benchmark

`research-300` is the current 300-task benchmark, with 420 conversation turns. It is the only public runner corpus; frozen legacy helper code is retained only for internal compatibility.

| Corpus family | Cases | Chinese / English |
| --- | ---: | ---: |
| STD — standard workflow | 100 | 50 / 50 |
| INT — interactive robustness | 100 | 50 / 50 |
| MM — multimodal reconstruction | 100 | 50 / 50 |

The engine allocation is 267 OpenSees, 16 PKPM and 17 YJK. The delivery has 300 authored/reference-ready cases and 300 cases with independently reviewed native evidence, including all 33 commercial references. Input blind review and model trials remain pending. See the [delivery record](implementation/research-300-delivery.md) and [manifest](../corpora/research-300/manifest.json) for evidence. The current `planning/benchmark-plan.json` verifies all source hashes; the original approved plan is retained as an immutable historical record. Its only difference from the current projection is the capability-registry digest.

INT-079 and INT-089 use independently qualified zero reactions at proven native free rotations, with original end-equilibrium residuals retained. The evaluator uses the original frozen tolerances for every default score; the 120 certificate-bound STD-089 recovery-scale allowances are diagnostic only. STD-089 retains two strict differences against each independent solver: 3,620 of 3,622 commercial comparisons pass. Captured native stiffness, loads and double displacements now support an independently verified float32 recovery replay matching all 504 member-end components bit for bit, including both differences. The engineering diagnostic passes all comparisons but does not determine scores or prove a general vendor arithmetic bound. Input blind review and candidate trials remain pending. See the root-cause investigation and strict-default correction; the earlier precision revision is retained unchanged as history. Run `npm run check:commercial-diagnostics -- --output /tmp/commercial-comparison.json` for separate `evidenceValid`, `strictPass`, and `engineeringPass` results. Exit 0 means strict agreement, 1 means strict numerical disagreement, and 2 means invalid evidence or inputs.

The 2026-10-26 readiness audit
records fresh evaluator, corpus and reference checks. The repaired StructureClaw
PKPM integration passes all 19 native states against the designated scoring
reference at unchanged tolerances. Those checks are separate from the two
retained STD-089 cross-engine diagnostic differences above. Reference readiness
does not grant input blind review, model-trial acceptance or a new system freeze.

The backend and Codex precheck
adds 264 passing backend suites (3,806 tests and 57 snapshots), four passing Windows
process checks, and a 12-case Codex input reconstruction precheck. Its six passed,
five failed and one invalid submissions remain diagnostic and do not grant formal
corpus acceptance or engineering-task scores.

New independent MM input reviews use [public-input review v2](public-input-review-protocol-v2.md)
(`npm run review:inputs -- ...`). Physical facts, protocol conformance, clarification and
source observations are separate mandatory dimensions. Legacy packets can be replayed
for diagnosis, but cannot become fresh v2 reviews without a new bound dispatch.

## Get the tasks

```sh
npm ci
npm run export:research300 -- --output /tmp/structureclaw-benchmark
```

The standalone export contains only `index.json`, case instructions, and scheduled
input files. Each of the 105 multimodal turns delivers one PNG or DXF containing
the necessary drawings, properties, loads, and notes. Standard and interactive
turns provide at most one readable input table. Follow the turn order; do not give
future clarification files to the model early.

The task package has no reference answers, internal bindings, checksums, review
records, or evaluation tolerances. The repository and reference viewer retain
those separately for benchmark maintenance. The viewer displays tasks and
reference results; its maintainer mode adds detailed audit records. Neither view
is a source of input for a blind agent trial.

## Inspect and validate locally

Install the pinned Node dependencies with `npm ci`. The research entry point works without a StructureClaw checkout or model credentials:

```sh
node runner.cjs --corpus research-300
node runner.cjs --corpus research-300 --scenario STD-001 --turn 1
node runner.cjs --corpus research-300 --execution validate
```

`--execution inspect` is the default. Turn numbers on the CLI start at 1. An explicit `--output FILE` writes the result; otherwise the result is printed. These modes do not prepare the SUT runtime, build its backend or initialize its database. Artifact evaluation is a separate offline mode; it consumes candidate execution artifacts and never runs a paid model trial.

## Independent numerical checks

Use an isolated Python environment for reference generation:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-research300.txt
.venv/bin/python scripts/research300/reference_cli.py \
  --cases-root corpora/research-300/cases --output-root results/independent
```

The generator writes to the explicit output directory and refuses to overwrite existing artifacts. The pinned Python environment was validated on Linux x86_64 with Python 3.10; activate it before running the npm Python-test wrappers. Its direct-stiffness solution is separate from the SUT conversion and result-processing code. The native OpenSees runner retains a separate executable input/result trail. Commercial cases now use reviewed PKPM/YJK scoring references; their saved matrix and OpenSees references remain diagnostics. Commercial evidence and replay instructions describe the qualified scope and retained differences.

## Task inputs and private reference data

Each directory under `corpora/research-300/cases/<ID>/` contains an authored contract, prompts, public attachments, hidden physical model states and reference requests. The corpus provider releases only the attachments scheduled for the requested turn. Later clarification data, hidden model states, reference values and scoring instructions are not model input. Each public turn also includes a versioned response contract with its requested quantity selectors and reporting units, so report formatting and identifiers are disclosed before evaluation.

STD tasks provide explicit geometry, properties and loading. INT tasks retain the source turn sequence and bind each analysis or query to its applicable state. Clarification turns retain unresolved inputs until their scheduled disclosure. MM tasks retain the required visual/DXF modality; a machine-readable coordinate table must not bypass geometry intended to be read from an image.

There is one current public input set at `corpora/research-300/public-inputs/`.
Instructions are concise; MM uses one drawing per turn, and STD/INT consolidate
public data in a single readable appendix. Historical input directories are
removed. Their archived review records do not certify the current inputs.
The [public input contract](public-inputs.md) documents regeneration and validation.
Local Python 3 and the pinned Node renderer are required to rebuild the inputs.

`planning/sources/` archives the original task table, model table and workbook. Their hashes bind the authored corpus to the original plan. `sourcePlan` retains the source requirements; `requirementCoverage` records where each requirement is addressed. A coverage entry does not itself prove successful execution or independent review.

## Evaluation standard

New tasks use model protocol `2.2.0` and profile `engineering-v2.3`. The normative implementation boundaries are in [the shared contract](implementation/research-300-contract.md); historical profiles remain documented in [the evaluation contract](evaluation-contract.md).

A successful numerical comparison requires the expected physical model, designated actual engine, exact load case or combination, current execution evidence, and every requested quantity. Signed values, units, member position and left/right side at a discontinuity are part of the quantity identity. Matching a reaction sum or a prior load case cannot replace missing outputs. Derived extrema retain the controlling operand and its sign. Requested figures and interaction behavior have separate requirements.

Execution evidence binds the current model and selection to a run, solver version and retained artifact hashes. Labels in candidate JSON are not sufficient proof of a native run. Independent matrix results cross-check mechanics; they do not substitute for a task's designated engine. Commercial qualification binds the reviewed native candidate, full raw evidence, current source and exact scoring values. An unreviewed exporter output remains diagnostic; installing an explicitly qualified reference does not grant input blind review or candidate-model acceptance.

## Acceptance stages

Report these stages separately for each case:

- **Authored:** complete source-linked input, states, outputs and valid files.
- **Input reviewed:** an independent reviewer reconstructed the task from public inputs before checking the hidden model; source-guided author checks do not grant this stage.
- **Reference validated:** independently computed quantities and engineering checks have passed.
- **Native verified:** the designated engine's retained model, settings and results have been checked.
- **Agent evaluated:** an actual model trial has produced the required current evidence and outputs.

An authored candidate can be inspected before later stages pass. Missing native truth must remain pending; it cannot become a zero-error reference or an agent failure. This implementation does not claim full LLM end-to-end evaluation. Use the generated manifest and per-case evidence for actual acceptance counts.

## Solver workspace boundary

Authoring and evaluation remain in the benchmark workspace. Optional Windows jobs carry numeric solver inputs under random job IDs in isolated job directories. Prompts, images, expected answers and grading rules stay local. The native broker must use pinned independent drivers, reject busy shared resources and collect verified artifacts before removing its own temporary files. It must not modify the active StructureClaw checkout or shared solver settings.

## Direct Codex and StructureClaw evaluation

```sh
npm run prepare:evaluation -- --case STD-001 --output /tmp/task
npm run evaluate -- --input /tmp/answer.json --context /tmp/task/capture-context.json --output /tmp/report.json
```

Preparation releases only the first turn by default. For a later turn, use
`--turn t2` with a new output directory and the case's exact public turn ID; the
packet contains history through that turn and excludes future prompts and files.
Deliver only `/tmp/task/agent-input` to the agent, and keep future packets,
capture context and reference data outside its accessible environment. The full
corpus export is coordinator storage, not a directory to mount into an agent.
Codex JSONL, final messages and
structured results, plus StructureClaw state snapshots, SSE and run archives,
use the same evaluator. See [result adapters](result-adapters.md) for state
sidecars, original solver evidence capture, format detection and limitations.
A plain final answer remains evaluable but cannot satisfy missing model or
solver evidence. Reports record whether current inputs were bound through a
prepared context or explicitly declared by the operator.

## Captured-run evaluation and semantic review

Evaluate retained execution evidence without invoking a model:

```sh
node runner.cjs --corpus research-300 --execution evaluate-artifacts \
  --artifacts results/captured-runs.json --artifact-root results/evidence \
  --assessments reviews/interaction-assessments.json \
  --output results/offline-evaluation.json
```

The capture envelope is `{schemaVersion:1,corpus:"research-300",runs:[{caseId,runId,turns:[{turnId,state,artifacts,figures?,toolEvents?,assistantEvents?}]}]}`. Each `state` is the cumulative agent snapshot. `toolEvents` retains tool activity, including adapter envelopes around original snapshot messages with explicit current or unverified scope. These envelopes are retained evidence, not invented native tool calls. Codex `assistantEvents` retains all completed visible assistant messages, including intermediate commentary; only the final message is used for numerical report extraction. `artifacts` maps immutable analysis run IDs to receipt artifact names and relative paths. Figures identify their output ID, model state, selected run and actual image file. The runner confines paths to the supplied artifact root and checks decoded bytes and execution context. It does not treat candidate-supplied evidence flags as trusted receipts.

For every current case, the capture harness and independent assessments retain the exact inspected `inputBinding` outside the model-facing task. Missing or stale bindings are rejected before evaluation. See the [input API and hash definition](public-inputs.md).

`--assessments` is optional when no semantic review is needed. When required, it must be a separately supplied benchmark-owned file outside the candidate artifact root: `{schemaVersion:1,corpus:"research-300",assessments:[{caseId,turnId,outputId,state,sourceHash,inputBinding,currentResponseSha256,activitySha256,pass,reason,reviewerId,reviewedAt,figureSha256?}]}`. Review requests contain the required bindings and the evidence to inspect. Missing review produces `review_pending` (exit 3); a negative review is an agent failure. Operators must control these files; filesystem separation is not cryptographic reviewer authentication.

Every evaluated turn emits both digests. The exported `currentResponseSha256(messages,messageStartIndex)` helper hashes a canonical JSON envelope containing only the current assistant messages. `currentActivitySha256(messages,messageStartIndex,toolEvents,assistantEvents)` hashes `{schemaVersion:1,messages:<current-turn state messages>,toolEvents:<current-turn raw tool events>,assistantEvents:<current-turn visible assistant events>}`. Missing event arrays default to `[]`. Both helpers sort object keys and preserve array order. Review requests include these messages and events. Every assessment must match the answer, activity, input, source and output; an old response-only assessment cannot certify a changed tool trace or intermediate answer.

Clarification answers require semantic review even when they contain the expected question or field names. Uncertain tool activity on a turn that forbids analysis requests review under `benchmark:should-not-analyze`; an explicit analysis attempt fails and cannot be overridden by review. Clarification uses the contract's interaction output ID, or `benchmark:clarification` when there is none. Figure checks require both valid file/run bindings and a content assessment with `figureSha256` matching the decoded image's original bytes. Successful decoding alone does not establish that a plot satisfies the task. Figure review requests include the actual file path, digest, dimensions, model and analysis result for inspection.

The public response contract documents numerical Markdown rows and current-message derived JSON/rows. Persisted reports from prior turns cannot satisfy a new answer. For explicitly permitted extrema ties, select one co-governing location and report its own signed value and exact selection; an opposite sign with the same named member fails.

## Reproduce retained reference checks

Generate fresh native OpenSees evidence into an empty output directory, compare it
with the independent matrix references, and audit the raw model and responses:

```sh
for case_dir in corpora/research-300/cases/*; do
  .venv/bin/python scripts/research300/opensees_native.py \
    --case-dir "$case_dir" --output-root results/native || exit 1
done
node scripts/check-research300-references.cjs --root . \
  --independent-root results/independent --native-root results/native \
  --output results/reference-check.json
.venv/bin/python scripts/research300/audit_native_evidence.py --root . \
  --independent-root results/independent --native-root results/native \
  --output results/native-audit.json
```

The native audit reads the installed OpenSees shared library to check its byte
hash; it does not import or execute that library. An explicitly located library
can be supplied with `--native-binary PATH`. All three commands retain diagnostics
for commercial cases without certifying YJK or PKPM truth. A passing comparison or
audit never writes acceptance automatically. Frozen references, source hashes,
raw evidence and separate review decisions are tracked in the corpus. Inspection
and evaluation reports also record actual provider/evaluator versions, Node
version and loaded local implementation hashes, independently of authored input
hashes.

Use matching generator sources when auditing retained receipts: the 267 original
OpenSees bundles bind the pre-convention generator from commit `b9de0f91`, while
the 33 commercial diagnostic bundles bind the newer finite-shear generator.
Auditing all those historical receipts against one current generator correctly
fails its source-hash check. The commands above generate fresh evidence with the
current sources; they do not overwrite installed scoring references. The auditor
independently checks the explicit commercial Timoshenko convention, its shear
areas and native uniform loads, as well as the Euler-Bernoulli path.

With the Python environment active, `npm run test:references`,
`npm run test:native-audit`, `npm run test:native-jobs`,
`npm run test:evaluation` and `npm run test:research300` exercise numerical,
physical-evidence and evaluation boundaries. `npm run validate` checks the current 300-case corpus.
