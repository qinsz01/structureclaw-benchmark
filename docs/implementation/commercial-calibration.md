# Commercial engine calibration

Research-300 requires independent benchmark adapters for PKPM and YJK. The data
factory's shear-wall API does not define their scope. StructureClaw source is
useful integration evidence; its model converter and result parser must not
serve as the sole correctness oracle for the benchmark that evaluates it.

All 16 PKPM and 17 YJK cases now have independently qualified same-engine
references. Their 39 physical states cover 3,199 primitive and 423 derived
requests. Native case evidence and replay
records the qualification, source bindings, raw runs and limitations. Input
blind review and candidate-model trials remain pending.

## Required scope

Generate the requirement inventory from bound authored files:

```sh
npm run inventory:commercial -- --output results/commercial-inventory.json
npm run test:commercial-calibration
```

The output path must be new. This command does not contact a solver, change
acceptance or read generated reference answers. Each state retains its model
hash, selections, material constants, section-property names, support patterns,
analysis controls and requested result components. Public bending conventions
are identified separately from the hidden reference implementation. The report
is an inventory, not proof that an adapter supports these requirements. Materials
and analysis controls come from bound hidden model states; the inventory does
not perform a blind reconstruction of those states from public inputs.

At the current authored revision:

| Engine | Cases | Model states | State/selection pairs | Primitive quantities | Derived quantities |
| --- | ---: | ---: | ---: | ---: | ---: |
| PKPM | 16 | 19 | 20 | 1,672 | 116 |
| YJK | 17 | 20 | 33 | 1,527 | 307 |

All 33 commercial cases now explicitly use `commercial-linear-static-v2`:
first-order elastic Timoshenko beams/columns with prescribed local shear areas
`Asy = Asz = 5*A/6`. This is a public benchmark idealization for every section,
including generalized numerical sections, rather than a deduction from a
section name. Each first turn releases a generic appendix in its own language;
the formula applies to subsequently supplied or changed sections without
disclosing their future values. Axial-only truss behavior is unchanged.

The source convention review
established that the original plan specifies neither bending theory. The earlier
authors added an Euler–Bernoulli clause to 22 STD/INT cases and left 11 MM cases
unspecified; both independent diagnostic implementations nevertheless used
Euler–Bernoulli for all 33. The uniform public correction preserves the exact
source requirements, numerical models, geometry, material/section constants,
loads, requested outputs, frozen tolerances, drawings and turn release schedule.
No candidate-agent trial preceded this revision.

The [revision manifest](../../corpora/research-300/evidence/commercial-convention-revision.json)
binds old and new source hashes and unchanged files. The [historical archive](../../corpora/research-300/evidence/history/commercial-linear-static-v1/README.md)
preserves the original public contracts and diagnostic result bytes. Fresh matrix
and real OpenSees finite-shear diagnostics supersede the old diagnostics;
all 3,622 commercial primitive/derived comparisons pass the original tolerances.
This is cross-engine diagnostic agreement, not commercial truth acceptance.

The public revision permits an explicitly documented native representation of
the six elastic stiffnesses while retaining the supplied physical definitions.
Actual native material fields, section fields, modifiers and serialization
differences must remain visible. Equivalent elastic stiffness does not establish
identical literal material fields, stress recovery or design capacity. Native
input qualification and same-engine reference review remain separate gates.

## Controls and comparison

`scripts/research300/commercial/calibration_math.py` supplies independent
closed-form cantilever responses for explicit material/section constants and
six signed tip-force/moment components. Its coordinate system has local x from
the fixed end to the tip, with right-handed y/z axes. Moduli use kN/m², lengths
use m, forces kN and moments kN·m. This differs from the corpus material input
unit MPa; native adapters must account for that factor explicitly.

The Euler–Bernoulli and Timoshenko functions are distinct. The latter requires
explicit effective shear areas in both directions; it never infers 5A/6 or
treats a missing/zero shear area as permission to choose a theory. Native
coordinate transforms and result units must be calibrated separately.

Useful controls separate axial response, torsion, both bending planes and pure
tip moments. Changing member length distinguishes cubic bending translation
from linear shear translation. Unequal section inertias and signed loads expose
axis swaps and sign errors. Tests include hand-integrated numerical expectations,
force/moment equilibrium and dimensional scaling.

For a native control, retain the submitted geometry, constraints, applied
loads, actual native material and section values, effective stiffness, command
and binary identity, raw responses and process receipt. An SDK setter's return
or a successfully saved model is not numerical validation. A completed control
only supports the features actually exercised; it does not certify all 53
state/selection pairs or arbitrary stations and combinations.

When native finite-shear results differ from an Euler–Bernoulli diagnostic,
identify the physical difference before assessing numerical error. Do not
raise frozen tolerances, substitute diagnostic answers, or use very large
finite shear stiffness as evidence of exact Euler–Bernoulli behavior. A missing
native result is unavailable evidence, not a zero response or an agent failure.

For multi-member diagnostics, `reference_solver.solve` and `solve_many` also
accept the keyword `effective_shear_areas={member_id: {"Asy": ..., "Asz": ...}}`.
Values are positive finite m² in each member's authored local axes, and the
map must cover every frame member exactly (excluding trusses). This explicitly
selects Timoshenko stiffness; omitting the keyword retains the existing
Euler–Bernoulli solver and metadata. No area is inferred from a section name or
geometry. Returned checks retain a separate copy of the supplied areas.

This audit mode supports nodal/point forces and moments and piecewise-constant
distributed loads. Observation stations and load boundaries are actual mesh
nodes, so uniform-load particular displacements and point-load jumps are
included. Varying distributed intensities are rejected because the existing
Hermite consistent-load formula is not generally valid for that shear model.
The mode is diagnostic only: it does not modify authored models, references,
tolerances, native evidence or acceptance. Tests include independently
integrated solutions and a real OpenSees `ElasticTimoshenkoBeam` spatial frame
with unequal areas, a rolled inclined beam, uniform loading and signed cases.
Its [official API](https://openseespydoc.readthedocs.io/en/latest/src/ElasticTimoshenkoBeam.html)
requires explicit shear areas in both local directions.

`reference_cli.py` selects this mode only for the exact commercial v2 contract
with its bound, first-turn public appendix. `opensees_native.py` independently
uses the real `ElasticTimoshenkoBeam` element, native uniform element loads and
actual nodes at load boundaries or requested stations. Both retain explicit
per-member areas and theory metadata. Default undeclared cases keep their
Euler–Bernoulli path. The validator and reference comparison reject mismatched
convention metadata; they do not infer revised physics from old result values.

The earlier `audit_native_evidence.py` constitutive audit is specific to the
Euler–Bernoulli driver whose source hash is in its receipts. Its historical
300-case report is not a new constitutive audit of the revised 33 cases. Replaying
it requires the recorded old source bytes; neither source hash checks nor its
constitutive equations are relaxed to accept the new driver. The 267 unchanged
OpenSees cases retain their original bound native reviews.

## Execution boundary

Authorized calibration uses Windows <native-host> through `codex_qsz`, with new
randomly named directories under `D:\bench-native`. Only numerical control
inputs and fixed probe code are needed there. Corpus prompts, answers and
scoring rules remain local and are never sent to remote models.

PKPM runs against explicit newly created projects using its installed SDK and
per-project native stages. It must not select projects using the shared
`DirectorySet.conf`, import wrappers attached to the current GUI project or
terminate existing PKPM processes. YJK uses an owned runtime/host and explicit
project paths. Windows Job Objects contain new processes; a temporary task for
an interactive session, if required, has a unique name and is removed after
its owned run finishes. Retain failed attempts as failed evidence.

The current broker has no enabled commercial driver. Experimental calibration
does not change that registry or grant `nativeVerified`/`accepted`. Qualification
requires reviewed mapping and native evidence for the actual case, state and
selection, followed by the existing acceptance workflow.

## Recorded attempts

The first 246 calibration attempt
preserves both engines' native authorization failures, selected raw evidence,
the process audit and the user's subsequent restoration report. It produced
no numerical responses or benchmark acceptance. Restored authorization must be
tested in a new attempt without replacing these historical observations.

The second PKPM attempt
still failed before solving. The user then confirmed that the restored
PKPM2027 installation requires its launcher to remain open. A subsequent new
attempt observed an already-running launcher and successfully reached native
analysis. The failed receipts remain historical failures; they are not
rewritten as successful solves.

The restored-license numerical controls
retain actual solver inputs, raw results, SDK extractions, independent reviews
and exact-byte manifests. Four YJK controls establish the tested static
finite-shear behavior and corrected local-axis/force mapping while preserving
the auxiliary floor-stiffness failure and measured input precision limits.
These control results are not acceptance evidence for an untested corpus case.
The PKPM package additionally preserves successful custom-material readback and
numeric-section controls. Its finite-shear comparisons explicitly retain the
unverified effective-shear-area hypothesis; standard C30 is not substituted
for a task's specified elastic constants.

The subsequent case qualification
adds full state and requested-output review to those controls. Native scoring
values now occupy `independent-reference.json`; the finite-shear matrix stays in
`independent-reference-matrix-diagnostic.json`. PKPM's scalar As readback remains
unavailable, so its qualification explicitly covers the observed behavioral
domain, supported by the controls and complete state checks. The 58 fixed-base
SDK omissions use a separately bound prescribed-boundary derivation; raw missing
values and finite pin stiffness are retained. The final native comparison retains
four failures out of 3,622 comparisons against each of the matrix and OpenSees
diagnostics: two STD-089 M3 differences and INT-079 / INT-089 state-1 pin support
My residuals. The latter are `1.9073486328125e-6` and
`4.76837158203125e-7 kN.m`, above the frozen near-zero `1e-8 kN.m` tolerance.
The independent addendum
confirms the raw end-force mapping and zero rotational restraint stiffness.
These residuals are not physical hinge restraint moments. A mechanically
correct zero can fail the current comparison; full acceptance therefore needs
a separate scoring-precision decision. Raw values and tolerances are unchanged.
