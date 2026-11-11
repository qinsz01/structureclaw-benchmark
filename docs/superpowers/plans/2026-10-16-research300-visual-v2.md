# Research-300 visual-v2 and independent input reconstruction

User-approved continuation of the remaining drawing, modality and blind-review work (steps 4–6). This follows the completed 2026-10-16 inputs/deformation plan.

## Scope and constraints

- Reorganize all100 MM cases using only original public input and the unchanged concise-v1 edition. Preserve physical meaning, architectural CAD distractors, response contracts, and five delayed clarification sequences.
- Produce a new visual-v2 edition with canonical PNG drawings and original DXF where applicable. Remove duplicate delivered SVG, consolidate repeated general/load notes once per release turn, retain all required view geometry and local labels.
- Preserve frozen corpus/model/reference/native evidence/acceptance and concise-v1 bytes. New authoring/checker assets have separate source identity. No remote SUT/model calls or StructureClaw changes.
- Actual independent reviewers receive only the exact public packets and reconstruct facts before a separate grader reads hidden models. Author checks do not constitute blind review. Any incomplete or failed reconstruction remains reported honestly.
- Current-edition review status is separate from frozen acceptance and actual benchmark model trials. Do not promote historical accepted counts.
- Continue in an isolated shared worktree with exclusive ownership. Local integration and preview refresh are already authorized by the user; no push or external publication.

## Task 1: Public-only visual authoring

Implement scripts/research300/public_input_visual.py and tests; build corpora/research-300/public-inputs/visual-v2. Closed schema matches concise-v1. Deterministic --check validates all source/attachment/release correspondence and raster contents with tamper tests. Reflow/crop readable sheets, consolidate duplicate tables, preserve unique values, ambiguous initial views, dimension/axis/roll/end orientation. All100 case decisions recorded in visual-inventory. Output report carries page/text counts, validation, limits.

## Task 2: Canonical provider and viewer

Extend provider options frozen/concise-v1/visual-v2; newest present edition selected, broken present edition fails closed. Checker/source bytes bind actual input hashes. Viewer consumes same attachments, matching provenance and version label. Preserve runner assessment binding. Add edition and release/tampering regression tests. No changes to solved deformation/results.

## Task 3: Blind workflow tools

Export public-only hash-bound packets, staged by turn. Define explicit reconstructive submission schema and tested physical comparison. Seal submissions before hidden comparison, validate current edition+packet+submission+grader evidence. Missing/incomplete/ambiguous facts must remain visible. No fake reviewer identity or author audit promotion. Expose independent edition-review metadata separately.

## Task 4: Independent reconstruction and quality review

After final assets exist, fresh context agents reconstruct public PNG/DXF/text packets. Initial ambiguous turns are reviewed before their corrections are disclosed. Store actual submissions, sealed receipt and comparison results per case. Repair genuine public-input defects and rereview changed packets. Independently review implementation and visual legibility; root handles integration.

## Task 5: Validation and local integration

Run meaningful edition, provider, runner, review, full research300, Python correspondence and viewer tests. Build final static export, browser-check current inputs/modalities/clarifications and deformation. Compare frozen/concise-v1 file identities against2ea324c. Commit only owned changes, integrate local work/research-next, refresh4173preview, final smoke. Report actual review coverage and remaining trial/acceptance limits.
