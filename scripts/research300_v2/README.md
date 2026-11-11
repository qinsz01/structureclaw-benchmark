# Research300 v2: complete 300-task authoring edition

This separate edition contains 300 tasks and 540 turns. The original/default
corpus, its frozen evaluator and historical candidate scores are unchanged.
The [Chinese review](../../docs/implementation/reviews/research300-v2-full-20261028/README.md)
records actual verification results and remaining experiment requirements.

Only the current turn's `public/` packet and installed generic tools may be
given to a candidate. The edition's `private/` records, `legacy-source/`, full
manifest, catalogue, future turns, authoring code and broker work directories
are maintainer material. This package does not provide an accepted candidate
sandbox/turn runner. `run_oracle.py` is explicitly a maintainer program that
submits known models; its results are not Codex or StructureClaw task scores.

## Design and scope

STD/MM/INT each contain 100 tasks, with L1/L2/L3/L4 = 20/40/30/10 per family.
The levels are designed difficulty, pending empirical calibration. The edition
uses 210 original tasks, 60 adaptations from 10 documented projects, and 30
reorganized commercial tasks with unchanged qualified native model kernels.
OpenSees/PKPM/YJK counts are 270/15/15. There are 20 modal, 10 linear transient,
25 finite-scheme and 15 model-audit tasks; categories can have additional
interaction, reconstruction and source load-transfer requirements.

All new physics stays within the pinned SUT's linear member-model support.
Engineering adaptations are declared subproblems with explicit assumptions,
not reproductions or safety certifications of complete buildings. Dynamic
tasks use explicit X-direction nodal mass and authored excitation, not a
recorded earthquake. Scheme constraints are issued analysis criteria, not
complete code design. Output figures are optional and unscored.

Topology fingerprints ignore names, scale and properties, and suppress
unrestrained collinear degree-two subdivisions. The actual edition has 229
fingerprints. Seven groups exceed the earlier target of three tasks per graph,
with a maximum of seven. Source facts and qualified commercial kernels are
retained rather than altering physical models merely to meet that target.
The input audit records this exception, same-model groups and split checks.

## Build and inspect

The checked Python is `/home/openclaw/.structureclaw/.venv/bin/python` with
NumPy, Pillow and pydantic v2; Node.js is needed for qualification.
The installed generic tools include [native input conventions](native-input-notes.md),
including natural stories and sloping-roof offsets. Supply the same complete
tool installation to both candidates. These notes contain no case IDs or answers.

```sh
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /home/openclaw/.structureclaw/.venv/bin/python scripts/research300_v2/build.py \
  --output NEW_EDITION

/home/openclaw/.structureclaw/.venv/bin/python scripts/research300_v2/setup_public.py \
  --base NEW_TOOL_INSTALL --sut .worktrees/structureclaw-pkpm-shear-fix-20261027

python3 scripts/research300_v2/audit.py --edition NEW_EDITION --output NEW_AUDIT.json \
  --schema-root NEW_TOOL_INSTALL/public-tools \
  --schema-python /home/openclaw/.structureclaw/.venv/bin/python
```

The authoring command requires a fresh output directory and preserves failed
attempts. Commercial seeds are read from the published edition's
`legacy-source/`; set `RESEARCH300_LEGACY_ROOT` to an extracted copy when
regenerating elsewhere. The original authoring also supported the retained
section-diversity working directory. Seeds include exact contracts, models and
native reference values. OpenSees references use independent stiffness,
mass-condensation and Newmark implementations, not the production solver.

The audit distinguishes mandatory input/schema/split checks from the unmet
graph-multiplicity target. Its overall `allPassed` remains false while that
explicit exception exists; consult `allMandatoryChecksPassed` and the details.
Source-guided reconstruction is not external blind review.

Run mathematical, authoring, public-input and archive tests with
`python -m unittest discover -s scripts/research300_v2 -p 'test_*.py'`.
Run evaluator regressions with `node --test scripts/research300_v2/test_evaluation.cjs`.
The latter uses protected native fixtures: set `SCLAW_V2_ORACLE_FIXTURE` and
`SCLAW_V2_PILOT_EDITION` for the retained pilot, and `SCLAW_V2_TORSION_WORK` /
`SCLAW_V2_TORSION_EDITION` for the full edition, including extracted archives.
Missing native fixtures are explicitly skipped; skipped checks are not evidence
that native equivalence passed. The recorded run uses all fixtures with no skips.

## Actual backend preflight and qualification

SUT commit: `db3c0b1da44fe668a6037a6c2e7f068d14354539`. The production worktree
must stay clean. Commercial execution requires the verified remote installation
records in WORK; reverify their source hashes before starting. Never copy old
captures into a fresh run. Local and commercial batches may run independently;
commercial jobs are serialized across batches by a host-level file lease.

```sh
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /home/openclaw/.structureclaw/.venv/bin/python scripts/research300_v2/run_oracle.py \
  --edition EDITION --work LOCAL_WORK --base NEW_LOCAL_SESSIONS \
  --sut .worktrees/structureclaw-pkpm-shear-fix-20261027 --engine OpenSees --local-workers 4

OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /home/openclaw/.structureclaw/.venv/bin/python scripts/research300_v2/run_oracle.py \
  --edition EDITION --work COMMERCIAL_WORK --base NEW_COMMERCIAL_SESSIONS \
  --sut .worktrees/structureclaw-pkpm-shear-fix-20261027 --engine PKPM --engine YJK

node scripts/research300_v2/qualify.cjs --edition EDITION \
  --work LOCAL_WORK,COMMERCIAL_WORK --output NEW_QUALIFICATION
```

Use `--cases` for an explicit subset or `--plan-only` before execution.
`--resume` only accepts the same frozen edition and implementation binding;
failed requests and numerical evidence remain. Query turns reuse prior jobs.
When a completed batch contains a failed case, a separate complete retry batch
may provide that case. Qualification retains the original closed attempt,
requires one complete successful provider for every selected case, rejects
duplicate complete providers and records recovery using stable batch IDs.
Do not rewrite an old failure as success or copy its captures into the retry.
Qualification requires complete selected-turn captures and checks protected
job identity, actual physical inputs/results, reported values/units, signed
governors, modal shapes, peak times and all scheme alternatives. It also runs
deliberately wrong and equivalent controls, separating full-evaluator tests
from physical-comparator-only checks.

The original maintainer coordinator omitted the legacy inactive natural-story
representation for one YJK roof task. The scoped `oracle_models.py` restores
that already qualified representation only with inactive bare-frame controls;
node coordinates and mechanics remain identical. It is not called by the public
broker. Original coordinator bytes are retained with the original batches;
the retry binds its new implementation separately.

## Offline evidence

`archive.py` accepts `--edition`, comma-separated `--work`, `--qualification`,
`--sut`, fresh `--output`, and optional repeated `--attempt` / `--review-file`.
It binds every retained file and writes ZIP byte volumes under 90 MiB each.
Sensitive installation settings are excluded and listed. Native outputs,
failed attempts and the scoring dependency closure remain available.

```sh
python3 scripts/research300_v2/verify_archive.py --review EVIDENCE_DIRECTORY --replay
```

Replay uses archived evaluator bytes, verifies all checksums and compares every
qualification output byte for byte. It does not rerun solvers or candidates.

Formal candidate isolation, equal Codex/Sclaw budgets, empirical difficulty
calibration and external blind input review remain separate acceptance work.
