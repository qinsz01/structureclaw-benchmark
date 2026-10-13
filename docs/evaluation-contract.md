# Engineering evaluation contract / 工程评测契约

The 300-task workbook is a plan, not an accepted executable corpus. `analysis-capabilities.json` records feature evidence and representative planned IDs; it does not award a pass to those tasks. The frozen corpus and its numerical/equilibrium checks remain read-only.

300题表仍是规划。能力清单按特征记录实现证据与示例题号，不能据此把题目标记为已验收。已有冻结标答、独立数值复算和平衡核验保留，不重写历史数据。

## Protocol and historical data / 协议与历史数据

New model boundaries emit **StructureModel 2.1.0**. Python accepts both 2.0.0 and 2.1.0; conversion to 2.1.0 is explicit. Existing V1-to-V2 compatibility migration retains its documented 2.0.0 output, while the new application boundary requests 2.1.0. New defaults do not rewrite old files. Unknown future schema versions are rejected.

2.1增加节点质量（tonne）、质量来源、显式自重/刚域/施工阶段开关及杆件点荷载、局部荷载、支座位移的保真契约。声明一个字段不等于求解器支持它；执行端必须映射或返回有类型的能力拒绝。省略的旧默认值不伪装成用户显式设置；参数缺失不能靠猜测后报正式成功。

Canonical units are m, kN, MPa, kg/m³; masses are tonnes. `position`, `start`, `end` are metres from member i. Existing `piecewise_linear.points[].position` remains a fraction of member length. Global axes are XYZ, Z up; 2D is XZ and global My/Ry has the opposite sign to the OpenSees planar third DOF. Full canonical member actions are N/V2/V3/T/M2/M3. Old planar end M is normalized when read, separately from old global Ry/My normalization.

典型新断言：

```json
{
  "assertions": [
    {"type":"model_matches","groundTruthId":"accepted-model-id","matcherVersion":"physical-v1"},
    {"type":"numerical_matches","groundTruthId":"accepted-model-id","selection":{"kind":"case","id":"D"}},
    {"type":"execution_evidence","selection":{"kind":"case","id":"D"}},
    {"type":"report_numerical_consistency"}
  ]
}
```

Add numerical/evidence assertions for **every required case/combination**; a passing D result does not imply L or ULS passed. `execution_evidence` is explicitly opt-in, and is never injected into frozen tasks. Historical `matcherVersion:"v2"` retains one-to-one matching and its unbound flat result reader; `v1` remains the older archival model matcher. New evaluations default to `physical-v1`. Published results must record the evaluator revision.

## Physical identity and numerical response / 物理模型与数值结果

The new matcher permits renumbering and subdivision of an unchanged straight member. Every new interior node must have degree two, no support and no connection to another original member. Every segment must retain the assigned section/material and bending axes. Gaps, overlapping members, disconnected coincident nodes, changed supports and hidden extra connections fail. Refinement involving releases/offsets remains unreviewed and rejects.

逐工况将节点/杆件荷载转换到同一物理位置和全局轴，对照有符号分量、分段分布及组合系数。不能把D/L混成一个总荷载，也不能用反力总和掩盖荷载位置错误。错误建模与缺工况不能由好看的图补分。

Numerical matching selects the exact identified result; partial/preliminary/error responses fail. OpenSees endpoint forces are transformed through actual local axes, using the first and last solver segments of each physical member. A missing last segment cannot fall back to the first segment. Commercial responses use the target engine's independently reviewed truth. Their signed envelopes cannot yet be reversed/refined without a verified station transform; those mappings fail explicitly. Cross-engine magnitude summaries are **calibration diagnostics**, not the correctness comparator.

## Execution, truth and display / 执行、真值与展示

The new evidence assertion requires a current physical model hash, immutable run ID, actual executed flag, solver version and successful solver return code when supplied. Pending edits, stale geometry/axes, incomplete results and engine labels without execution fail. These fields must come from the trusted execution service; JSON metadata alone is not a cryptographic attestation. Corpus acceptance separately checks original input, actual scripts/native model files, raw outputs, logs and settings/readback against that run.

真实执行与参考真值隔离：被测工具不能读取参考模型/参考数值；参考求解不复用被测建模转换链路。OpenSees题用审定的同引擎模型与解析/独立矩阵/平衡交叉验证。YJK/PKPM题用各自原生模型、设置及结果，不能只拿OpenSees做唯一真值。跨引擎差异先检查建模假设、单位、轴、刚域、自重和组合，不直接扣给agent。

The viewer may display frozen reference values and shared recovered member responses. A viewer plot is not evidence that the agent executed the solver or produced that response. Shared postprocessing must take the selected actual run's mesh, loads, axes and result provenance; expected reference graphics cannot substitute for missing actual data. Requested interior response quantities need accepted station-specific references and dedicated assertions; endpoint matching alone does not certify every span station.

展示层图形不是agent计算证据。计算、跨内恢复、参考数据和展示必须有明确来源；内部点与端点测量不是同一项验收。不能把只验证过端力的题宣布为跨内响应全部通过。

## Acceptance gates / 逐题入库门槛

`planning/capability-coverage-300.json` covers every STD-001…100, INT-001…100 and MM-001…100 from the latest solver-supplemented plan. It preserves the plan's 267 OpenSees / 16 PKPM / 17 YJK assignments and original requirements, with hashes of both source JSON tables and the associated workbook. `scripts/build-capability-coverage.cjs` reproduces this read-only projection.

映射区分三件事：结构/类别直接给出的能力关联、待复核的文本候选关联、真正的逐题执行验收。关键词只提示检查方向，可能出现在“不要启用刚域”等禁止条件中，绝不据此宣称需要或支持该功能。某特征的OpenSees测试也不能当作YJK/PKPM证据。当前300题整体均为未验收，尚未明确拆解的需求保持unknown，原文完整保留供后续审定。

1. Freeze task, explicit physical inputs, required positions/components and cases. 冻结题面、物理参数、结果位置分量及工况。
2. Verify every required feature on the designated adapter, including commercial native settings/readback. 目标引擎实测；能力清单标注或mock测试不能替代。
3. Review same-engine truth independently; retain equilibrium/theory checks and declared tolerances. 标答独立审定；误差需有工程依据。
4. Verify the agent run through the actual boundary, selected case, raw artifacts and current model identity. 验证真实接口路径与结果新鲜度。
5. Check every requested numerical/report quantity and shared recovered station. 所有题定输出必须覆盖，不删除不方便验收的要求。
6. Publish only accepted tasks; report unsupported adapter features separately from agent failures. 缺能力不算模型错误，不以删题掩盖范围缺口。

Known unaccepted features include end releases, nonzero offsets, second-order/construction-stage controls, full-member nonlinear analysis, unverified commercial settings and native result station transforms. The 300-task release is blocked wherever its task requires one of these. No claim of complete 300-task support is made by this change.

## Local verification / 本地检查

### Current requested-output contract / 新版指定输出契约

New `engineering-v2.2` cases require an `execution_evidence` assertion for every
numerically asserted case/combination. `numerical_matches.quantities` accepts
independently frozen records with `id`, exact `selection`, `location`, `component`,
explicit `unit`, reference `value` and absolute/relative `tolerance`. Unit conversion
accepts m/mm, kN/N and kN.m/N.m within their own dimensions; missing historical source
unit metadata uses the established canonical contract, never magnitude guessing.
Member locations include `positionM` and `side`; missing exact stations and
display-only interpolation fail. Node IDs and reviewed member subdivisions use
the same physical matcher. Reversed internal action stations remain rejected
until their axis/sign transformation is independently accepted.

新版逐工况要求真实运行证据。指定构件位置不能用最近绘图点替代，点力两侧必须分别检查。
新增报告数量断言核对正文表格行：`id | case:D | beam@2:left | V3 | 0.25 | kN`；
节点位置只写节点ID。报告中的符号、位置、工况和单位必须逐项一致，隐藏参考值不传给被测工具。

`acceptance/representative-18` is an authored **candidate** acceptance pack, separate
from frozen scenarios/fixtures. It contains 18 case inputs and state snapshots,
tagged drawings/tables, explicit quantities and an independent direct-stiffness
cross-check. Commercial references remain diagnostics until same-engine native
truth is independently accepted. No claim of image recognition or full-300
acceptance follows from deterministic tool execution.

18题候选包与历史题库隔离。独立矩阵参考不导入生产求解与恢复算法，不能替代商业软件原生标答。
输入盲审、真实模型识图及完整交付尚需单独验收；各状态和附件的哈希在候选运行前冻结。

The requirement projection now distinguishes required/forbidden/output clauses.
The 300-case plan does not request full shells, general nonlinear, P-delta or
unlimited rigid arms. All 12,566 original clause references still need case review;
the `unmappedClauses` count means no candidate link, not the complete unknown count.
当前300题不因“不要启用刚臂”等否定句被错误扩成二阶或非线性题；真实弹性短臂、柱脚铰约束与
构件端释放明确区分。能力表中的旧错误示例已移除。

OpenClaw exports tool schemas from the current backend registry on each run.
It exposes edit/undo/model/result queries, case collections and PDF pagination;
PDF vision uses the same injected parser as the web agent. The historical tag
retains its original tool surface; new runner results must record the new revisions.

`npm run test:evaluation --prefix tests/llm-benchmark` exercises physical equivalence, exact signed case results, stale-run rejection, commercial-case selection and evaluator integration without paid model calls. Set `SCLAW_TEST_PYTHON` to an OpenSees-enabled Python to include the real solver-to-evidence positive test (otherwise that test explicitly skips). `node tests/llm-benchmark/lib/validate-corpus.cjs` validates the existing 150 scenario files. Real OpenSees mechanics tests live under each analysis skill's `__tests__`; protocol regression tests additionally cover conversion and minor-version compatibility.
