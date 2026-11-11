# Public inputs

Research 300 has one public-input directory: `corpora/research-300/public-inputs/`.
It contains a manifest and one folder for each of the 300 cases. Every MM turn
delivers exactly one PNG or DXF; STD and INT turns deliver at most one readable
Markdown input table. Later turns release only their scheduled information.
The provider, task export, evaluator and viewer consume this same directory.
Missing, invalid or stale input fails validation. There is no version selector or
fallback to historical inputs.

## Model-facing task package

```sh
npm run export:research300 -- --output /tmp/structureclaw-benchmark
```

The export contains `index.json`, ordered `cases/<id>/task.json` instructions and
relative attachment files. The package omits answers, response contracts, hashes
and internal review metadata. Its README defines the signed result table and
derived-result reporting format. The viewer contains reference answers and must
be kept separate from model-facing task delivery.

## Internal API and bindings

```js
getPublicTurnInput(record, turnIndex);
```

The returned object contains `id`, `turnId`, `instruction`, `attachments` and the
original `responseContract`. An attachment contains `name`, `relPath`, absolute
local `path`, `source: "edition"` and `sha256`; consumers read its verified `path`.
The compatibility labels `edition` and `inputEdition` are fixed to `current` in
internal records. They do not select an input version or appear in task exports.

Each case has one `inputBinding`, shared across its turns:

```json
{
  "schemaVersion": 1,
  "caseId": "MM-001",
  "inputEdition": "current",
  "publicInputSha256": "<current delivered content digest>",
  "baseSourceHash": "<original authored source digest>",
  "basePublicSha256": "<original public source digest>",
  "editionManifestSha256": "<public-inputs/manifest.json digest>",
  "editionBundleSha256": "<public-inputs/MM-001/input.json digest>",
  "editorialValidatorSha256": "<current generator digest>",
  "validatorSources": [{"path": "<checker dependency>", "sha256": "<digest>"}],
  "authorAuditSha256": "<per-case authoring audit digest>"
}
```

`publicInputSha256` hashes compact UTF-8 JSON with recursively sorted object keys
and original array order. Its payload is
`{schemaVersion,caseId,inputEdition,baseSourceHash,basePublicSha256,turns}`.
Each turn contains `{id,instruction,attachments,responseContract}` and each
attachment contains `{name,source,path,sha256}` with a relative path. Absolute
machine paths never enter that digest.

The provider verifies closed schemas, case and turn coverage, original source
bindings, attachment byte hashes, safe paths, absence of private data, and
scheduled release boundaries. It then checks deterministic regeneration from
original public instructions and attachments. A successful check is cached only
by freshly verified content and all checker dependencies; timestamps are not a
substitute for content identity.

`getFrozenPublicTurnInput` and `getFrozenPublicBinding` remain internal provenance
helpers for checking original source identities. Current delivery does not call
these helpers as an input fallback. Original model, reference and native receipt
hashes retain their own meanings; a public-input digest cannot replace a native
receipt's `sourceHash`.

Capture and independent assessment records retain the exact `inputBinding`
outside model-visible content. Missing or stale candidate bindings fail before
scoring. A binding identifies the delivered inputs; execution evidence separately
establishes which model and engine produced the results.

## Regeneration and validation

```sh
python3 scripts/research300/public_input_clean.py --root .
python3 scripts/research300/public_input_clean.py --check --root .
```

The generator preserves physical facts and release boundaries from the original
public instructions, tables and drawings. PNGs contain the necessary public
properties and notes; DXFs retain original geometry and architectural distractors
and append the required public annotations. Authoring SVGs and correspondence
audits are internal maintenance files, excluded from the model-facing export.
Rendering uses the local Node/Sharp installation and Python 3.

When an original MM appendix omitted construction-stage policy, the delivered
input explicitly says not to model construction stages. The audit records this
as an authored policy clarification. It does not claim the statement appeared in
the original source.

## Independent input review

Deterministic correspondence validates the transformation from public sources.
Independent reconstruction requires a fresh reviewer to read only a sealed
public packet, submit observed engineering facts, and seal that submission before
comparison with the hidden reference model. Initial clarification turns must be
reviewed before later corrections are supplied.

The current packet, seal, grade and replay workflow supports MM cases. Reports
live under `corpora/research-300/input-reviews/<id>/review.json`. STD and INT input
review remains pending until a supported independent workflow produces its own
evidence. Historical reviews do not transfer to current inputs; missing, partial,
failed or stale evidence cannot establish acceptance or an end-to-end model run.
See the [independent review protocol](public-input-review-protocol.md).

Commercial analysis conventions embedded in the current drawing are recovered by
the grader from their original, hash-bound public source files after the provider
has validated deterministic correspondence. Only sources released through the
reviewed turn are used, and their byte hashes are retained in the grading evidence.
