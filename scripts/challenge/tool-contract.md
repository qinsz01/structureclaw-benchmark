# Tool and delivery contract / 工具与交付约定

This is a documented-tool structural engineering task. Read task.json and the supplied issued documents. Later turns are released only when they occur. Use @SCRATCH@ for your files. The designated engine is OpenSees.

The public model schema is @TOOLS@/structure_model_v2.py. It describes StructureModelV2, schema 2.2.0, SI (metres, kN, MPa, radians; section properties m²/m⁴). Source documents can use different explicitly labelled units. The schema is documentation, not a case model.

Submit your own model through the actual solver client:

```sh
python3 @TOOLS@/analyze.py --model YOUR_MODEL.json --selection case:ID --session @SESSION@ --output-state @SCRATCH@/state-@TURN@.json
```

Use `combination:ID` for a combination. The client returns actual numeric engine output for your submitted model, including a run identifier. It supplies no answer, corrected model, plot or expected response. Multiple selections can be accumulated in the same state file only for the same physical model. Preserve the returned execution metadata. Query-only requests can copy an unchanged previous actual state to the current state file.

Save the current response as **@SCRATCH@/answer-@TURN@.json**. For computed results use:

```json
{"quantities":[{"id":"PUBLIC_REQUEST_ID","selection":{"kind":"case","id":"PUBLIC_CASE_ID"},"location":{"kind":"node","id":"PUBLIC_NODE_ID"},"component":"PUBLIC_COMPONENT","value":0.0,"unit":"PUBLIC_OR_EQUIVALENT_UNIT"}]}
```

The zero above is a format example, not an engineering answer. Include all current public requests with signed finite numbers. Use their public selection/location identities even if your internal model uses different identifiers. Compatible physical unit conversions are accepted. Member locations, where requested, contain `kind`, `id`, `positionM` and `side`.

When essential information is unresolved, ask a specific question instead of issuing a calculation. Use `{"clarifications":[{"field":"FIELD_ID","question":"Your specific question"}]}`. FIELD_ID is `node:<public node>:<dof>` for a boundary issue or `member:<public member>:<property>` for a member issue. Supported orientation property name: `rotation_angle`. No numerical quantities are required until the issue is resolved.

本任务提供可查阅的通用接口文档。请自行理解资料、建模、决定当前是否足以求解，并交付当前轮的结果。接口知识无需预先掌握。不同候选系统应获得同等的文档和求解服务；隐藏参考、未来资料和评分反馈不提供给候选。
