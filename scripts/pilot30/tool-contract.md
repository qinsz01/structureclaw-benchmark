# Public solver protocol / 公共分析接口

Read this document, the current task.json, delivery.md and supplied attachments.
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
Reported displacements in this pilot are relative to the uniformly excited base.

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
output figures are optional and unscored in this pilot. Later interaction turns
are patches: retain previous inputs unless explicitly changed. Schema/default
errors and backend failures return an error without a successful job; inspect
and correct your own inputs before retrying.
