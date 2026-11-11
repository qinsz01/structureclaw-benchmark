# Research300 v2 development pilot

This is a separate 30-case/52-turn edition, not the default corpus or a scored
Codex/Sclaw trial. See the [Chinese review](../../docs/implementation/reviews/research300-v2-pilot30-20261028/README.md)
for results, limitations and retained failed maintainer attempts.

The edition is [corpora/research300-v2-pilot30-v1](../../corpora/research300-v2-pilot30-v1/).
Only a turn's `public` directory and the generic installed tools may be exposed
to a candidate. The private references, authoring files, oracle models, future
turns and broker work directory are maintainer-only. This pilot does not yet
provide an accepted candidate sandbox/turn runner; `run_oracle.py` is explicitly
a maintainer program. Never point Codex or Sclaw at this repository as its task
workspace and call that a blind evaluation.

## Source layout

- `build.py`, `cases.py`: author a new immutable edition; never overwrite one.
- `independent.py`: independently assembled planar reference, mass condensation
  and linear Newmark solution; no production solver imports.
- `oracle_models.py`: scoped maintainer representations; not broker repairs.
- `analyze.py`, `service.py`: generic public numeric client and private broker.
- `setup_public.py`, `tool-contract.md`: allowlisted generic public documentation
  and source installation, including schema dependencies.
- `evaluate.cjs`, `qualify.cjs`: protected-job scoring and maintainer positive /
  counterexample controls. Some controls test only the physical comparator;
  they are explicitly marked and are not extra native solver executions.
- `review_inputs.py`, `audit.py`, `test_physics.py`: local source-guided input
  reconstruction, static package/legacy-integrity review and independent theory.
- `amendment.cjs`: audit delivery-only publication changes without relabeling
  the original numerical execution manifest.
- `archive.py`, `verify_archive.py`: retain immutable evidence and replay offline.

## Reproduce local checks

The checked interpreter is `/home/openclaw/.structureclaw/.venv/bin/python`
(NumPy and pydantic installed). Node is also required. Commands below run from
the repository root; choose fresh output names.

```sh
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /home/openclaw/.structureclaw/.venv/bin/python scripts/pilot30/test_physics.py -v

python3 scripts/pilot30/verify_archive.py \
  --review docs/implementation/reviews/research300-v2-pilot30-20261028 --replay
```

The archive verifier checks all bytes, source bindings, 30 cases/52 turns,
77 actual solver jobs and the absence of candidate calls, then optionally
recomputes the final positive/negative qualification exactly. It does not call
models or native solvers again. The archive includes the SUT source used and
production generated recovery JS, plus the unchanged legacy evaluator closure.

## Actual maintainer executions

Pinned SUT: `db3c0b1da44fe668a6037a6c2e7f068d14354539` at
`.worktrees/structureclaw-pkpm-shear-fix-20261027`. Commercial jobs require the
already provisioned and source-hash-verified remote installation. Before a
fresh run, place its `remote-setup.json` and `remote-source-manifest.json` in the
fresh WORK directory and verify the installation still matches the pinned
sources. Do not copy old solver jobs or captures. Local and remote production
workers must remain unchanged. Merely pointing to an arbitrary Windows root
does not verify commercial software or licenses.

```sh
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /home/openclaw/.structureclaw/.venv/bin/python scripts/pilot30/run_oracle.py \
    --edition corpora/research300-v2-pilot30-v1 \
    --work WORK --base PUBLIC_ORACLE_SESSIONS \
    --sut .worktrees/structureclaw-pkpm-shear-fix-20261027

node scripts/pilot30/qualify.cjs \
  --edition corpora/research300-v2-pilot30-v1 --work WORK --output NEW_QUALIFICATION
```

This maintainer runner can read references to submit known physical inputs. It
uses exactly the same generic public client bytes as those installed for future
candidates. Its base directory contains every oracle turn, so it is **not** a
candidate isolation environment. Failed native jobs and requests remain on disk;
`--resume` continues only an identical frozen edition and retains prior records.

The retained final run executed the R3 input manifest and then received a
delivery-only amendment. To replay that exact history, pass
`--execution-edition EXECUTED_R3_EDITION` to `qualify.cjs`. It checks both complete
file manifests, identical case metadata, identical private references and
numerical inputs, and permits only delivery.md edits plus the one literal source
filename correction. The qualification reports both hashes; captures are never
rewritten to claim a new backend run.

## Scope still to qualify

Output figures are unscored. Current modal tasks have distinct eigenvalues;
repeated-mode subspace comparison is not claimed. Current transient questions
use one direction, explicit nodal mass, fixed time step and relative displacement.
Spatial embedding equivalence is accepted only for the previously reviewed
closed planar domain, canonical axes, fully restrained inactive DOFs and no
releases/offsets; changed loads, axes or freed DOFs still fail. This is not a
general arbitrary-rotation stiffness projection.

Candidate process isolation, candidate commercial coordinator integration,
budget fairness and actual Codex/Sclaw task completion remain to be exercised
before a scored comparison. No full-300 readiness claim follows from this pilot.
