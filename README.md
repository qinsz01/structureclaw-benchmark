# structureclaw-benchmark

LLM agent benchmark suite for [StructureClaw](https://github.com/structureclaw/structureclaw).

This repo is consumed by the main `structureclaw` repo as a git submodule under
`tests/llm-benchmark/`, but it can also be cloned and run standalone against any
StructureClaw checkout.

## What it does

Runs the LangGraph ReAct agent end-to-end across a corpus of structural-engineering
scenarios (text, multimodal images, DXF reverse-engineering, architectural plans/elevations)
and evaluates them with a compact task taxonomy:

| Task family | Count | Purpose |
| --- | ---: | --- |
| `standard_workflow` | 50 | Clear text request → skill selection → model → analysis |
| `interactive_robustness` | 50 | Missing, invalid, ambiguous, conflicting, or multi-turn inputs |
| `multimodal_reverse_engineering` | 50 | Image, drawing, DXF, and plan reverse-engineering |

These correspond to the A/B/C design split: A = standard workflow,
B = interactive robustness, C = multimodal reverse-engineering. Directory names
use the explicit `taskFamily` values so the JSON metadata and file layout stay
aligned.

Each task family is bilingual-balanced: 25 Chinese scenarios and 25 English
scenarios. `npm run validate:scenarios` enforces the 25/25 split, rejects English
prompts that still contain CJK text, and checks for duplicate normalized prompts
within the same task family, benchmark structure type, and input modality.

Task families describe what the user is asking the agent to do. Evaluation
dimensions stay separate and are expressed as typed assertions:

- `structureType` — runtime structure/skill type (`frame` is the steel-frame skill ID)
- `benchmarkStructureType` — reporting taxonomy (`steel-frame`, `concrete-frame`, `continuous-beam`, ...)
- `structural_type` — inferred runtime structure type (beam / frame / truss / ...)
- `has_model` — produced a computable StructureModel
- `has_analysis` — ran analysis
- `engine_match` — ran analysis with the requested analysis skill/engine
- `has_report` — generated a report
- `skill_match` — routed to the expected skill
- `model_matches` — one-to-one engineering-model fidelity: coordinates, topology,
  restraints, assigned material/section properties, and load type/direction/location/magnitude
- `numerical_matches` — solver responses match frozen ground truth from the requested engine
- `has_interaction_questions` — asked for clarification when input is incomplete
- `should_not_analyze` — did not run analysis for unsafe or under-specified input
- `no_bad_model` — did not create a computable model for unsafe or under-specified input
- `natural_language` — LLM-as-Judge semantic check

Standard steel-frame and concrete-frame scenarios may also request a specific
analysis backend. Use `analysisSkillTarget` for the skill ID and
`analysisEngineTarget` for the runtime engine ID:

| Skill target | Engine target |
| --- | --- |
| `opensees-static` | `builtin-opensees` |
| `pkpm-static` | `builtin-pkpm` |
| `yjk-static` | `builtin-yjk` |

Every scenario uses `maxRetries: 0`, so each scenario is attempted once.
Repeated trials should be represented by running the full experiment multiple
times and aggregating those independent runs.

Each scenario run also has a wall-clock timeout shared by all turns and retries.
The default is 900000 ms (15 minutes) and can be overridden with
`defaults.caseTimeoutMs` in `experiments/llm-experiments.local.json`,
`--case-timeout-ms <milliseconds>`, or `LLM_BENCHMARK_CASE_TIMEOUT_MS`. A
timeout records the run as an execution failure; it does not change scoring
thresholds for normal tool usage.

The experiment wrapper runs cases in supervised mode by default. In supervised
mode each scenario uses a separate child process, so a timed-out case is
isolated from later cases even if an in-flight model request keeps running.
The supervising parent gives the child process an additional grace window after
the case timeout so the child can write its failure result before being killed.
Use `--no-supervise` only for single-process debugging.

- `Pass@1` — passed on the single scenario attempt
- `averageToolCalls` — average agent tool calls per scenario run; this is an
  efficiency signal only, with no pass/fail threshold
- `averageDurationMs` — average wall-clock duration per scenario run

The standard executable workflow split is balanced by `benchmarkStructureType`:

| Benchmark structure type | Count |
| --- | ---: |
| `beam` | 9 |
| `steel-frame` | 12 |
| `concrete-frame` | 6 |
| `truss` | 8 |
| `portal-frame` | 6 |
| `continuous-beam` | 5 |
| `column` | 3 |
| `generic` | 1 |

## Skill modes

The default run uses the real system behavior:

- `auto` — the agent routes and selects skills normally.

For experiment tables, the runner can also expand into controlled skill modes:

- `oracle-specialist` — scopes the run to the scenario's `skillTarget` plus the requested static-analysis skill.
- `generic-only` — scopes the run to the generic structure skill plus the requested static-analysis skill.

These produce the comparison columns used for specialist lift and routing gap:

```text
Specialist Lift = oracle-specialist - generic-only
Routing Gap     = oracle-specialist - auto
```

## Layout

```
fixtures/            # Generated ground-truth models, PNG images, DXF drawings
  ground-truth-models.json
  opensees-ground-truth.json  # present only after strict OpenSees generation
  drawings/          # Rendered PNG + DXF (regenerated by fixtures/*-generator.mjs)
lib/                 # evaluate.cjs, judge.cjs, report.cjs, skill-trace.cjs
scenarios/           # One JSON file per scenario, grouped by task family
  standard_workflow/
  interactive_robustness/
  multimodal_reverse_engineering/
runner.cjs           # Entry point
scripts/             # Experiment runners and helper scripts
```

## Running

### As a submodule (from main structureclaw repo)

```bash
node tests/runner.mjs llm-benchmark                          # all scenarios
node tests/runner.mjs llm-benchmark --scenario beam-simple   # one scenario
node tests/runner.mjs llm-benchmark --mode all                # auto + oracle + generic modes where enabled
node tests/runner.mjs llm-benchmark --family standard_workflow
```

### Standalone

```bash
# 1. Point at a structureclaw checkout (must be built: backend/dist exists)
export SCLAW_ROOT=/path/to/structureclaw
export LLM_API_KEY=sk-...

# 2. Run
node runner.cjs
node runner.cjs --scenario beam-simple --output results.json
node runner.cjs --mode all --output results.json
npm run validate:scenarios
```

## Engineering and numerical ground truth

`model_matches` uses a one-to-one geometric node mapping and evaluates node,
element, and load precision/recall. Extra entities therefore do not pass merely
because their counts exceed a lower bound. Element connectivity/type, support
DOFs, schema and unit contracts, assigned materials, section properties and
parametric geometry, plus releases/offsets/rotation are checked separately. Each
load's mapped target, reference frame, direction, and magnitude are also checked.
Entity IDs may differ when the engineering relationships are preserved. The optional
`matcherVersion: "v1"` switch exists only to reproduce archived arXiv-v1 scoring;
strict matching is the default. Current strict assertions use a 0.05 m coordinate
tolerance and a 5% load-magnitude tolerance throughout the benchmark. Canonical
`stories.floor_loads` and legacy `floorLoad` fields are compared by engineering
meaning; solver-derived loads marked `story_floor_loads` are not counted twice.

Numerical values must never be entered manually. Generation requires the exact
OpenSeesPy package version pinned by StructureClaw and runs every one of the 59
ground-truth models in at least two fresh Python processes. The second run also
reorders model entities and loads, changing OpenSees tag assignment while keeping
the engineering model unchanged, and switches from `BandGeneral/Plain` to
`FullGeneral/RCM` with a different OpenSees solution algorithm. The output file is
written only after every model succeeds, all values are finite, solver identities
agree, and the complete result trees agree within `1e-10` absolute or relative
tolerance. Each fixture's sole declared load combination is selected explicitly;
its ID and factors are recorded beside the result. Every independent run must
also satisfy global force and moment equilibrium before it can be committed.
The manifest records the wrapper package, platform runtime package
(`openseespywin`/`openseespylinux`), and native OpenSees engine versions separately.
Canonical simply supported and cantilever beam fixtures are additionally checked
against closed-form Euler–Bernoulli reactions, bending moments, and displacements.
All 53 canonical 2-D fixtures are also solved by the independent Euler–Bernoulli
frame/truss direct-stiffness implementation in `lib/independent-linear-solver.cjs`.
Generation fails unless its full signed response agrees with OpenSees, and the
independent input/output hashes and comparison errors are stored per fixture.
OpenSees numerical assertions compare the full node displacement, reaction, and
member-response trees at 1% tolerance. Signed member forces are compared after
normalizing reversed member orientation, rather than by absolute magnitude alone.
For numerical report scenarios, `report_numerical_consistency` additionally
requires the structured report to embed the current analysis artifact exactly;
report length alone is not treated as numerical faithfulness.

```bash
# Explicit interpreter is recommended.
npm run truth:generate -- --python /path/to/opensees/venv/bin/python --runs 2

# Two-path smoke calculation without writing the canonical truth file.
npm run truth:generate -- --python /path/to/python --model beam-simple-6m --model truss-simple-tri

# Add explicit numerical_matches assertions after the complete truth set exists.
npm run truth:wire

# Recompute in fresh processes and compare with the committed truth without rewriting it.
npm run truth:verify -- --python /path/to/opensees/venv/bin/python --runs 2
npm run truth:wire:check
```

Generation attempts all 59 models even when an individual model fails. Pass
`--audit-output <path>` to retain a failure inventory; this audit never contains
or replaces a partially generated truth set. The canonical truth file is written
only when the full set passes.

### Three-engine external validation

`fixtures/cross-engine-ground-truth-validation.json` is a separate external-validation
layer; it does not average solver outputs or replace the OpenSees-plus-analytical
canonical truth above. The three engines receive the same regular 3-D geometry,
material/section definitions, story gravity loads, and member self-weight. Results
are reduced to the same dead-load case and compared pairwise. The record contains
source/input hashes, executable/API hashes, normalized metrics, tolerances,
exclusions, and every pairwise difference. Every engine is run twice in isolated
work directories. PKPM and YJK must reproduce their complete normalized response
within 0.01%; both response hashes and comparison diagnostics are stored.

For scenarios that explicitly request PKPM or YJK, `numerical_matches` compares
the runtime result directly with the frozen ground truth produced by that same
engine. PKPM compares every available non-base-node displacement and member-force
component; YJK additionally compares every node reaction. Entity coverage must be
exact and every frozen response value uses a 1% tolerance. OpenSees remains an
independent cross-engine validation reference; its values are not substituted for
an engine's own numerical ground truth. The current benchmark has 107 analyzable
model targets and all 107 carry `numerical_matches`. Seven planar requests that
cannot be represented losslessly by the current 3-D PKPM/YJK adapters are explicit
adapter-boundary cases: they require clarification and safe non-execution, and are
not included in the numerical denominator.

Validation is deliberately tiered. `equilibrium` covers total vertical action and
the bottom-column axial sum. `response` additionally covers load distribution,
column moments, and displacement. PKPM construction-stage vertical displacement is
excluded until that option is aligned. Beam moment remains a recorded diagnostic,
not a pass criterion, because OpenSees currently exposes member-end values while
PKPM/YJK expose maxima across member stations.

Eligibility is derived from the complete ground-truth file rather than a handpicked
case list. Of the current 59 fixtures, 53 are canonical 2-D models that cannot be
extruded into commercial 3-D standard floors without inventing geometry. All six
3-D fixtures declare physical section dimensions and are cross-validated. In the
current frozen record all six pass equilibrium validation; two also pass every
declared cross-platform response threshold, while four retain explicit response
differences rather than weakening the thresholds. PKPM
copied-standard-floor IDs are refreshed after SATWE execution, so different story
loads remain exactly traceable to the source model. The generated support audit
records every inclusion and exclusion, and a regression test fails if any eligible
fixture is absent from the validation results. Story loads are taken from each
source fixture, with explicit derived beam loads removed before all three engines
perform their own floor-load transfer.

```bash
PKPM_CYCLE_PATH=/path/to/JWSCYCLE.exe \
YJKS_ROOT=/path/to/YJKS_8_0_0 \
npm run truth:cross-engine -- --python /path/to/python

npm run truth:cross-engine:verify -- --python /path/to/python
```

On Windows, pass the corresponding `python.exe`. If OpenSeesPy is missing or its
package version differs from the pinned requirement, generation fails before any
truth file is written.

The runner reads LLM config (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`) from the
SUT's regression context — see `tests/regression/shared.js` in the main repo.

## Experiment LLM configuration

Use the experiment wrapper when comparing multiple model roles. For normal use,
edit only these three selectors in `experiments/llm-experiments.local.json`:

```json
{
  "testModel": "glm-5-turbo",
  "multimodalModel": "glm-4.5V",
  "judgeModel": "DeepSeek-V4-Pro"
}
```

- `test` — the main agent model used by standard, interactive, and multimodal suites.
- `multimodal` — the vision parser used only before image/drawing scenarios. Its
  output is injected as an attachment summary, then the `test` model runs the
  normal StructureClaw agent/tool workflow. This role maps to `LLM_VISION_MODEL`,
  `LLM_VISION_BASE_URL`, and `LLM_VISION_API_KEY`. Model-specific `extraEnv` may
  also set `LLM_VISION_TEMPERATURE` for providers that require a fixed vision
  request temperature. Vision parsing uses the scenario case timeout; it does
  not apply a separate shorter request timeout.
- `judge` — the LLM-as-Judge model, mapped to `LLM_JUDGE_MODEL`,
  `LLM_JUDGE_BASE_URL`, and `LLM_JUDGE_API_KEY`.

The template config stores model names, base URLs, and the environment variable
that holds each API key. It does not store secrets.

Image scenarios use an explicit, non-overlapping input contract. The drawing is
the sole source of topology, dimensions, supports, and load magnitudes; a
separate `engineeringSpecification` supplies materials, sections, and analysis
settings. Task prompts contain no case-specific numeric parameters, attachment
names are neutral, and the vision parser receives neither the task nor the file
identity. Complete drawings use consecutive coordinate dimension chains rather
than total spans or assumed symmetry, and 3-D drawings state the base restraint
DOFs explicitly. Load annotations consistently use `P` for point loads, `q` for
distributed line loads, and `p` for area loads. Three robustness cases
deliberately withhold critical image evidence and the engineering specification
so that safe clarification, rather than model construction, is the expected
outcome.

```bash
npm run experiment:init

export ZHIPU_API_KEY=...
export PARATERA_API_KEY=...
export OPENAI_API_KEY=...

npm run experiment:list
npm run experiment -- --suite smoke-text --dry-run
npm run experiment -- --suite smoke-text
npm run experiment -- --suite smoke-multimodal --multimodal-model glm-4.5V --judge-model DeepSeek-V4-Pro
npm run experiment -- --suite standard --test-model glm-5-turbo --judge-model DeepSeek-V4-Pro
npm run experiment -- --suite multimodal --multimodal-model glm-4.5V --judge-model DeepSeek-V4-Pro
```

Available suite names in the example config are `smoke-text`,
`smoke-multimodal`, `standard`, `interactive`, `core`, `multimodal`,
`all-auto`, and `all-modes`. Suites containing image tasks use the `multimodal`
role only for pre-agent vision parsing. Additional runner filters can be appended, for
example:

```bash
npm run experiment -- --suite standard --scenario std-beam-4m-point-mid --mode all
```

Results are written under `results/` by default, with the suite, primary model,
judge model, and timestamp in the file name. Use `--output <file>` to override
the path.

For sequential multi-model comparisons, use the batch wrapper. It expands
`models × modes`, calls the normal experiment wrapper for each pair, writes one
UTF-8 log, and updates a summary JSON after each pair completes:

```bash
npm run experiment:batch -- --suite standard \
  --models glm-5-turbo,glm-5.2,DeepSeek-V4-Pro \
  --modes auto,generic-only \
  --case-timeout-ms 900000 \
  --name standard-domestic-text-all
```

## Regenerating fixtures

Ground-truth models and rendered drawings are committed for reproducibility.
To regenerate after editing the model factory or renderers:

```bash
npm run regen-fixtures
```

## License

MIT
