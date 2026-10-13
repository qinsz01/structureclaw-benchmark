# Representative acceptance candidates / 代表验收候选包

`representative-18/manifest.json` freezes 18 candidates from the existing 300-task
plan: six STD, six INT and six MM, including 12 OpenSees, three PKPM and three YJK.
The full plan remains 267 / 16 / 17; no historical scenario, fixture, paper truth or
result was changed. This directory is separate from the released 150-case corpus.

这里是工具链验收候选，不是已发布的新题库。18题通过也不代表300题通过。

| Group | OpenSees | PKPM | YJK |
|---|---|---|---|
| STD | 008, 026, 036, 063 | 086 | 088 |
| INT | 001, 008, 019, 074 | 079 | 084 |
| MM | 004, 058, 070, 100 | 081 | 085 |

Each case includes user instructions, explicit material/section/axis/load data,
geometry tables or tagged drawings, complete hidden model states, and independently
computed quantities with exact cases, stations, sides, units and tolerances.
`contract.json` identifies user attachments and individual turns. Hidden
`model-state-*.json` and `independent-reference.json` must never be attached to an
agent's input. The deterministic tool harness reads the hidden physical model only
to test engineering services; it does **not** evaluate language or image recognition.

每题独立模型，逐轮模型快照、工况/组合及输出位置均显式记录。MM-058首轮不给柱脚，
INT-079首轮不给Y跨度和由此计算的线载；需要补全后才能计算。英文题提供英文用户指令。
图像题不把隐藏坐标模型作为用户附件。

The independent oracle is a separate NumPy direct-stiffness implementation with
consistent nodal loading and explicitly subdivided response stations. It imports
neither OpenSees nor any production converter or postprocessor. Closed-form checks
cover a uniformly loaded simple beam, a point-load shear jump and a spatial
cantilever. Force/moment balance and free-DOF residuals are retained per state/case.
Commercial numerical values are **diagnostics only** until native independently
reviewed YJK/PKPM projects, settings and signed result readback are supplied.

独立参考采用弹性梁柱/轴力杆的一阶小变形假设；A/I/J/E/G明确输入，不用于非线性、
二阶或墙壳评测。冻结容差为绝对1e-8加相对1e-6（按各分量声明单位），未因候选失败放宽。
还需工程盲审输入完整性、同引擎审定参考及最终题目输出；图形交付和自然语言解释不由
数值表验收代替。商业题不能拿OpenSees或本矩阵参考当作唯一标答。

Run from the Bench directory with an OpenSees-enabled Python runtime and a built SUT:

```powershell
$env:SCLAW_DATA_DIR='G:\StructureClaw-All\sclaw_data'
$env:SCLAW_TEST_PYTHON='G:\StructureClaw-All\sclaw_data\.venv\Scripts\python.exe'
npm run test:evaluation
npm run test:openclaw
& $env:SCLAW_TEST_PYTHON scripts/test-independent-reference.py
node scripts/check-representative-pack.mjs --output=G:\StructureClaw-All\sclaw_data\work\bench18-tools.json
```

The tool check runs `run_analysis`, `edit_model`, `undo_model`, exact
`query_results` and `generate_report` through the current registry, applies the
application's own state reducers, and checks model identity, current execution
evidence, signed quantities and the report's visible table. It makes no paid model
calls. Native commercial cases remain pending in this harness. Output includes run
IDs, source identity and hashes; adjacent `*-artifacts` retain actual model/result/
report payloads. References are hashed before and after execution.

Authoring corrections on 2026-10-13 added explicit initial combination coefficients,
English individual-turn instructions, text-task geometry tables and DXF node/support
labels. MM-085 Y-beams were corrected from generic B2 to the source plan's B1 before
any commercial candidate execution. Previously exercised OpenSees models, reference
values and numerical tolerances were byte-checked unchanged. Input hashes were
refrozen after these documented corrections; old candidate run records retain their
original manifest hash.

Do not run `build-representative-pack.py` during evaluation. It is an authoring tool:
it regenerates references and the manifest, so changes require explicit engineering
review and a new freeze. Regenerate drawing PNGs with Sharp when SVG geometry changes.
The current DXF exporter includes native UUID/time metadata; regenerating it changes
its file hash even if its geometry is identical.

## Recorded check / 本次记录

`records/tool-mechanics-2026-10-13.json` records 12 OpenSees cases, 19 model states,
37 selected case/combination results and 3,240 signed quantity comparisons. All
3,240 report-body rows match the independently frozen values. This run exercised
add/undo, load interval movement, independent combination edits, section roll/undo,
unconnected crossed trusses, frame/truss mixing, inclined columns and spatial
elastic arms. Six commercial cases remain `native-reference-required` in this pack.
Image recognition, clarification conversation quality and model/result figure
correctness were not assessed by this deterministic tool run.

评测回归45条、OpenClaw配置/实际schema/reducer检查15条、独立参考解析校核3条全部通过；
历史150题校验通过。实际OpenClaw 2026.6.33 dry-run完成配置和插件载入校验，14个工具均注册；
未发出付费模型请求。结果记录对应冻结manifest
`245dc8b655caff319d5debc751e6c0da10304d3c3ac58e0ac61356e0d708c92a`。

The final replay against SUT `bded4a2a14693c1df47ef46f58b23d17f8bafd43` is retained
separately in `records/tool-mechanics-2026-10-13-bded4a2.json`. It again passed all
19 states, 37 selections and 3,240 numerical/report quantities with unchanged input
and reference hashes. Production mechanics and compiled tool hashes were identical
before and after the replay. The 15 OpenClaw contract tests also passed against this
build, including the actual exported `review_input.resolutions[].modelField` schema.
The earlier `230ac7d` record remains available as history; neither record certifies
image understanding or native commercial case truth.

最终版本回放单独保存，原记录不覆盖。模型、标答与容差均未改动，未调用付费模型。
