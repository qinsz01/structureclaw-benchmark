# Public solver protocol / 公共分析接口

Read this document, the current task.json, runner delivery instructions and supplied attachments.
The runner supplies SESSION, TOOLS and SCRATCH paths. Future turns and private
references must not be made available to a candidate. The engine is assigned by
the task; the client cannot choose a different engine.

`TOOLS/structure_protocol/structure_model_v2.py` documents the pinned
StructureModelV2 schema 2.2.0. The accompanying generic schema dependencies are
also supplied, so local validation is possible when pydantic 2 is installed.
They contain no task-specific models. Use m, kN, MPa, rad; explicit elastic
section properties use m²/m⁴, density kg/m³, nodal mass tonne. Shape dimensions
in `shape`, when used, are mm. Restraint order is ux,uy,uz,rx,ry,rz.

Write your own request JSON, then execute:

```sh
python3 TOOLS/analyze.py --request SCRATCH/request.json --session SESSION --output SCRATCH/reply.json
```

A static request has this structure (identifiers are placeholders):

```json
{"model":{},"analysis":"static","selection":{"kind":"case","id":"YOUR_CASE"}}
```

Replace model with your complete schema-valid model. For a combination use
`{"kind":"combination","id":"YOUR_COMBINATION"}`. Execute every required
selection; do not add self-weight or unrelated automatic controls by default.
The service validates the model and runs the existing designated backend. It
does not repair models, read references, generate answers or plot figures.

Modal/transient requests use `analysis:"modal"` or `analysis:"transient"`,
omit selection, and include `parameters`. Modal parameters include
`analysisType:"modal"`, `numModes`, `direction:"x"`. For time history use
`analysisType:"time_history"`, `timeStep`, `duration`, `dampingRatio`,
`direction`, `groundMotion`, `groundMotionUnit` (g or m/s2) and the supplied
monitor node/element/support IDs. Convert a supplied excitation CSV to a numeric
array, in row order. Sample zero is at t=0; output begins at timeStep. The
acceleration between samples is linearly interpolated by the existing solver.
Use the task's explicit record, units, nodal mass source and mass directions.
Reported displacements in this edition are relative to the uniformly excited base.

The reply is `{ok,jobId,state}`. Preserve the UUID jobId and inspect the actual
state. For static analysis, each reply contains the executed selection at
`state.analysisResult.results["case:ID" or "combination:ID"].data`:

- `displacements[node]`: global ux,uy,uz,rx,ry,rz;
- `reactions[node]`: global lowercase fx,fy,fz,mx,my,mz (public requests use
  Fx,Fy,Fz,Mx,My,Mz);
- `memberResponses`: physical member samples including position x (m), side,
  signed N,V2,V3,T,M2,M3. Use the requested station/side and the recovered
  physical section actions; raw end resisting vectors have a different sign
  convention at some ends. Axial force N is positive in tension.

Dynamic replies contain `state.dynamicResult.data`. Modal `modes` contain period,
frequency, effectiveMass, modeShape (global six-component arrays). Time-history
rows contain time and monitored nodes; follow the public request path.
`operation:"max_abs"` selects the entry with the greatest absolute magnitude
and **retains its sign**; an exact tie selects the first chronological sample.

Save the current answer at the location designated by the runner, using:

```json
{"jobIds":["ACTUAL_JOB_UUID"],"quantities":[{"id":"PUBLIC_REQUEST_ID","value":0.0,"unit":"m"}],"derived":[],"clarifications":[]}
```

Zero is a format example, not a result. `quantities` covers exactly the current
`reportIds`, which may be a subset of the supporting `requests`. Copy public
request IDs even when your internal model uses other legal identifiers.
Compatible m/mm, rad/mrad, kN/N, kN.m/N.m/kN.mm/N.mm, tonne/kg conversions are
accepted; seconds and Hz are supported. Keep at least 8 significant digits.
A time-history signed peak additionally requires `time` in seconds. Do not
replace a signed peak with an unsigned maximum.

For each public derived definition report id,value,unit,governingOperand and
governingSelection. The governor is the winning operand request ID and its
public `{kind,id}` selection. Arithmetic expressions without a governor use
null for both. Use the definition's operand order and tiePolicy (default first;
any permits co-governing values). For nested expressions, the immediate winning
derived operand is also a valid governor. Do not substitute a generic envelope
whose scope differs from the requested operand list.

For scheme questions, additionally give `selectedScheme` (null if none feasible)
and `schemes:[{id,jobIds,maximum,volume,feasible}]` for **every supplied scheme**.
maximum is the greatest absolute requested displacement over all listed
combinations and constraint nodes, in m. volume is the sum of A×actual member
length over all members, in m³. Only substitute the declared scheme section;
retain other members, loads and controls. Minimize volume among feasible schemes.

Where requested, give
`modeShapes:[{modeNumber:1,values:{PUBLIC_NODE_ID:0.0}}]`, with each requested
mode and node. A common nonzero scale and sign change of a mode is accepted.

If an essential physical field is unknown, ask a targeted question and give no
jobIds or numerical quantities until it is resolved. Clarifications are
`[{field,question}]`; use a JSON pointer to the public concept, e.g.
`/geometry/ySpan` or `/requestedOutputs/maximumAxialForce/scope`.
Dynamic parameter fields use `parameters:FIELD_NAME`, e.g.
`parameters:groundMotionUnit`. A query ambiguity may require clarification while
already determined ordinary outputs are still computed, as specified in task.json.
An explicit query-only turn reuses previous jobIds without a new analysis.

The structured answer is authoritative. A short body summary is sufficient;
output figures are optional and unscored. Later interaction turns
are patches: retain previous inputs unless explicitly changed. Schema/default
errors and backend failures return an error without a successful job; inspect
and correct your own inputs before retrying.


## Issued documents and review tasks / 新版资料与模型审查

The case-local task.json and this contract define the required delivery.
`reportIds` is the public list of quantities that must be reported. Supporting
requests may additionally define the operands of derived outputs. No expected
numerical value, tolerance, winning scheme or required issue identity is provided.

Reconstruct the initial model from model-convention.json, member/material/section
schedules, the issued geometry, loads, combinations and analysis controls.
materials.json preserves full material records; materials.csv gives the main
values with explicit units. node-extra.json, element-extra.json and
model-extra.json, when present, carry additional issued attributes. metadata.json
contains explicit local reference vectors and other issued model conventions.
For MM tasks, the complete node coordinate and six-restraint schedules are issued
as PNG sheets or DXF rather than a coordinate CSV/JSON. Source-adapted tasks also
provide project facts and declared assumptions, which may state dimensions,
heights or support conditions: these are source-assisted multimodal tasks, not
claims that all geometry can only be learned visually. Story schedules are on
the sheets or the DXF STORY layer. Never infer a joint merely from a crossing in a
projection. members.csv defines endpoints by node IDs. A large geometry overview
may abbreviate overlapping labels; exact node-table sheets are authoritative.

When load-recipe.json is present, construct load_cases from its `cases` list.
A `surface-on-members` term supplies pressureKNM2, tributaryWidthM, the member
IDs and globalUnitVector. Multiply pressure by tributary width once, then by
each global component to obtain wx/wy/wz in kN/m, per actual member length. Do
not add the same area pressure again. A `nodal` term directly specifies node
and force/moment components in the stated SI units. Later load modifications
operate on these already constructed mechanical load cases.

If model-to-review.json or review-excerpt.json is supplied, treat it as the
model/properties to inspect against the authoritative issued schedules. Identify
and correct the actual discrepancies, run the corrected model, and additionally
report:

```json
{"issues":[{"path":"/materials/0/E","reason":"Explain the discrepancy and correction."}]}
```

Paths are JSON Pointers to fields of the supplied faulty model, with zero-based
array indices in the issued order. A review excerpt keeps the corresponding
root field and array order of that model. JSON pointer escaping is `~0` for `~`
and `~1` for `/` inside an object key. Correct field identities
and a nonempty explanation are required. Concise Chinese or English is accepted;
there is no English word-count threshold. Merely naming an issue cannot replace
correct physical inputs and actual analysis evidence. Do not invent additional
issues in fields consistent with the issued information. MM review excerpts
contain no complete geometry model; reconstruct geometry using the issued
drawings together with any declared project facts.

## Change orders / 后续轮次变更

Subsequent turns release task.json and change-order.json, plus explicitly
replaced excitation inputs when needed. They do not supply a complete current
model. Retain the last confirmed state and apply only the issued operations, in
order. The ordinary semantic format is:

```json
{"schemaVersion":1,"operations":[{"op":"scale-load-case","caseId":"Q","factor":1.2}]}
```

- `scale-load-case`: multiply only the specified case's force, moment and line
  load components by factor, including supported endpoint values or piecewise
  intensities. Do not multiply coordinates, member/load positions, interval
  endpoints, units or prescribed support displacements.
- `restore-load-case`: replace only caseId with its initial t1 mechanical load
  case (`fromTurn:"t1"`). Retain all current section/material/mass changes.
- `resize-section`: multiply the rectangular width B by widthFactor and depth H
  by depthFactor, then update shape dimensions and explicit elastic constants.
  Shape B/H are mm; convert to metres for A=B*H, Iy=B*H^3/12 and Iz=H*B^3/12.
  The authored rectangular torsion convention is J=l*s^3*(1/3-0.21*(s/l)*
  (1-s^4/(12*l^4))), where l=max(B,H), s=min(B,H), both in metres. For an
  explicitly unshaped section, propertiesFactor instead multiplies all supplied
  independent elastic section constants. Apply the case's explicit convention.
- `scale-nodal-masses`: multiply only explicit nodal mass values by factor.
  Do not add density-derived mass or change the declared mass source.
- `restore-nodal-masses`: restore the initial t1 nodal mass assignments and
  values (`fromTurn:"t1"`) while retaining other current model changes.
- `set-constraint-limit`: replace the task's absoluteLimit; it changes the
  response constraint, not geometry, loads, sections or mass.

For migrated cases, `schema:"json-patch"` marks ordinary JSON Patch operations
`replace`, `add` and `remove`, with path and value. Paths in this format resolve
against the current full model JSON, including zero-based array indices, not
against a hidden future model. Apply the patch in order and retain other fields.
Do not apply an update a second time because it is also described in prose.

A newly supplied analysis-parameters.json/excitation.csv replaces that analysis
input for the current turn. Unchanged earlier parameters remain in force when no
replacement is issued. source-basis.json separates source facts from authored
idealizations; authoringBasis in task.json describes any further adaptation.
A source-based subproblem is not a claim to reproduce the original full project.
