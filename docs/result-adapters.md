# 直接评估 Codex 与 StructureClaw 的结果

题库只有一套当前公开输入。统一入口读取被测系统保存的输出，转换成相同的评估记录，再执行相同的模型、数值、交互、报告和图像检查。导入器不运行语言模型，也不补写没有发生的求解、回答或图像交付。

## 准备与评估

先导出本题输入和采集上下文：

```bash
npm run prepare:evaluation -- --case STD-001 --output /tmp/bench-STD-001
```

准备命令默认只释放第一轮。输出目录中的 `agent-input` 是本轮可见的公开输入；`capture-context.json` 供采集器与评估器核对题目和本次输入绑定，不交给被测系统。多轮题按顺序执行，每一轮保存当时的输出与完整状态。到达下一轮时，再生成独立目录，例如：

```bash
npm run prepare:evaluation -- --case MM-007 --turn t2 --output /tmp/bench-MM-007-t2
```

`--turn` 使用题目中的精确轮次 ID。目录只包含截至该轮的历史、提示和附件，后续轮次不会写入该目录；运行器只发送当前轮的新提示与附件，并保留已有对话。完整题库导出包供运行器管理，不能直接挂载给多轮被测系统。准备目录本身不提供操作系统级隔离：运行器还须确保被测进程不能读取未来输入包、采集上下文、隐藏参考或含答案的可视化界面。

评估 StructureClaw 保存的状态：

```bash
npm run evaluate -- \
  --input /tmp/agent-state.json \
  --case STD-001 --format structureclaw \
  --context /tmp/bench-STD-001/capture-context.json \
  --output /tmp/assessment.json
```

评估 Codex 的 `exec --json` 事件记录，并关联其写出的结果文件：

```bash
npm run evaluate -- \
  --input /tmp/codex.jsonl \
  --state /tmp/state.json \
  --case STD-001 --format codex \
  --context /tmp/bench-STD-001/capture-context.json \
  --output /tmp/assessment.json
```

也可用 `--format auto` 自动识别，或用 `--format capture` 评估已有的统一采集包。`--states FILE` 用于多轮状态文件。模型报告中的数值必须属于相应轮次，末轮状态不能代替前面各轮的结果。Codex 的原始工具活动必须一并保留；最终回答中的澄清句不能抹去之前执行过的求解。

没有 `--context` 时，`--case` 表示操作者声明这些结果对应当前题目输入。报告明确记录这种来源；该声明不能证明模型运行前确实收到了这份输入。有上下文时，评估器严格核对当前输入绑定，不接受过期上下文。

`--assessments FILE` 可提供独立的交互、澄清和图像内容审阅记录。该文件应由评估方控制，放在候选结果的 `--artifact-root` 之外。评审同时绑定当前回答摘要 `currentResponseSha256` 和本轮消息、工具事件及可见助手事件的摘要 `activitySha256`；图像评审还绑定实际文件字节的 `figureSha256`。修改工具轨迹、中间助手输出或图片后不能沿用旧评审。缺少必要审阅时报告 `review_pending`，不能将其自动变成通过；记录字段见[评审协议](research-300.md#captured-run-evaluation-and-semantic-review)。

## 支持的输出

| 来源 | 可导入内容 | 需要补充的内容 |
|---|---|---|
| Codex `exec --json` JSONL | 已完成的助手消息、原始工具活动；关联的结果文件及其中的 `artifacts` / `figures` | 完整物理模型、求解结果和原始证据应在实际结果文件中；文字中的“已完成”不建立求解证据 |
| StructureClaw `runFull()` 的完整 `AgentState`，或 `{state: ...}` | `model`、`analysisResult`、`analysisRuns`、`report`、`resultQuantities`、`messages` | 原生求解回执对应的文件字节；题目要求的实际图像 |
| StructureClaw `GET /api/v1/chat/conversation/:id` | `session.model`、消息、`snapshots.latestResult.analysis/report` | 当前状态中没有的归档与原始证据；会话运行状态已失效时不会恢复旧缓存结果 |
| StructureClaw chat SSE | `artifact_payload_sync`、`result`、最终助手文本；结果失效事件会清除旧结果 | 单轮流以外的历史状态；求解原始证据与实际图像 |
| StructureClaw `GET /runs/:id` 或 `run.json` / `run.json.gz` | 不可变分析运行、模型快照、全部工况及组合 | 对应的助手回答；单独分析归档不能证明用户要求的回答或报告已经交付 |
| 统一采集包 | `{schemaVersion:1,corpus:"research-300",runs:[...]}` | 缺失的独立审阅或回执文件 |

StructureClaw SSE 必须保留本轮完整的完成或合法等待状态。导入器拒绝失败事件和静默截断；HTTP 层的 `[DONE]` 不能单独证明 agent 成功。明确请求用户输入、需要恢复执行的中断可作为等待状态导入，问题、选项和工具活动保留供评估。原始完整状态对象没有生命周期字段时，只代表操作者提供了一份快照，不能据此证明整段 agent 流程已正常结束。

当前聊天流还支持 `artifactId` / `artifactReferences` 去重引用。引用必须指向本次流中实际保存的最新模型、分析或报告；缺少前序事件、引用已失效、重复 ID 或同时提供冲突实体都会拒绝导入。分析失效时，其报告引用也一起失效。

新版聊天分析中的 `artifactReference`、`selectedDataReference` 与 `run-member-sample` 是归档定位信息。使用 `--runs-root` 提供同一运行 ID 的完整归档后，适配器恢复被聊天投影省略的原生审计字段与采样来源，并逐项核对保留的数值、工况、元数据和物理模型；不允许用归档覆盖被修改的聊天结果。缺少归档时保留投影并明确提示证据不完整，不据此补写成功执行。

Codex JSONL 按完整轮次导入。CLI 在重连时也可能输出 `type: "error"`：明确标为可重试的错误或已识别的 `Reconnecting...` 提示，只有在同一轮最终出现 `turn.completed` 时才允许继续导入，并保留重连诊断。终止错误、`turn.failed` 和未完成的事件流仍会被拒绝；成功导入文字不会补出缺失的工程证据。

Codex 的最终助手消息用于数值报告提取；本轮所有已完成的可见助手消息另存为 `assistantEvents`，与工具记录一起参与活动哈希和语义评审，避免最终回答掩盖先前的不当假设。

关联状态中的消息也不会被最终回答抹去：适配器用 `toolEvents` 内的 `snapshot_messages` 封装保留这些原始消息，并标明当前轮或轮次不确定的范围。这个封装是评估端记录格式，不是伪造的 Codex 原生事件；无法确定轮次的活动进入独立评审。

`POST /api/v1/agent/run` 的返回摘要在所检查的上游提交中通常没有完整的模型和分析结果。需要数值评估时，优先保存 `runFull()` 状态、chat 流中的完整输出，或者关联运行归档。

前端的 `modelSnapshot` / `resultSnapshot` 可能是用于显示的 `VisualizationSnapshot`：节点使用 `position`，结果是绘图用的 `cases`。这些缓存没有完整的材料、荷载和求解回执，不能替代物理模型。导入器不会从画图缓存猜测缺失输入。

物理模型使用 StructureClaw 的 `schema_version: "2.2.0"` 协议、SI 单位与 Z 向上的坐标约定；二维结构位于 XZ 平面。协议版本属于数据格式，与题库发行版本无关。LangChain 的 `AIMessage` / `HumanMessage` / `ToolMessage` 序列化消息及普通 `role/content` 消息均可读取。

## 归档与原生证据

用 `--runs-root` 指定 StructureClaw 数据目录下的 `runs` 文件夹：

```bash
npm run evaluate -- \
  --input /tmp/conversation.json --case STD-001 --format structureclaw \
  --runs-root /path/to/structureclaw-data/runs \
  --capture-root /tmp/sclaw-worker-captures \
  --artifact-root /tmp/candidate-files \
  --output /tmp/assessment.json
```

归档按输出中已有的运行 UUID 查找，读取 `<UUID>/run.json.gz`，并兼容 `run.json`。同一目录同时存在两份归档、模型指纹不符、结果运行身份不符或文件越出指定目录时会拒绝导入。导入器不会选择“最近一次运行”来补齐未知来源的结果。

求解回执与采集封装分开保存：

```json
{
  "artifacts": {
    "<analysis-run-id>": {
      "capture": {
        "normalizedInput": "capture/input.json",
        "solverResponse": "capture/response.json"
      },
      "selections": {
        "case:D": {
          "normalizedInput": "native/input.json",
          "settings": "native/settings.json",
          "solverResponse": "native/response.json"
        }
      }
    }
  }
}
```

采集封装中的输入包含实际 `model` 与 `selections`，响应包含完整的结果与采集上下文。原生 `selections` 文件保存求解器回执所指的规范字节。不同工况在同一个运行 ID 下可能有不同哈希，不能混用。

OpenSees 回执使用 Python 的排序键、紧凑 UTF-8 JSON，并分别记录 `normalizedInputSha256`、`settingsSha256`、`solverResponseSha256`。上游 JavaScript 写入归档时可能丢失 `0.0` 与 `0`、`-0.0` 与 `0.0` 的序列化区别。因此，仅有 `run.json.gz` 时不一定能恢复原回执字节。

评估适配器可以尝试重建字节，并且只接受与原 SHA256 完全一致的结果。可通过 `--structureclaw-root CHECKOUT --python PYTHON` 使用上游同层 Pydantic 模型规范化。失败时明确报告缺失证据，保留原哈希。提供运行时采集目录 `--capture-root` 可以避免该信息损失。

哈希匹配之后还会检查内容绑定：原生输入必须对应当前物理模型，原生设置必须对应指定工况或组合，当前节点结果、端力、求解网格及有效荷载必须与原始响应一致。OpenSees 的 `memberResponses` 由上游后处理生成，原生回执通常未直接覆盖这些字段；评估器根据已验证的分段端力、端位移、有效荷载和刚度独立恢复并逐点核对，拒绝只保留旧回执却修改曲线数值的输出。单位覆盖、混入商业站点数据以及删除回执格式字段也不能绕过该检查。尚未验证的摘要、包络等派生字段不能作为数值依据。

## 在运行时保存 Python 原始字节

仓库提供 [capture_structureclaw_worker.py](../scripts/research300/capture_structureclaw_worker.py)。它执行原始 StructureClaw Python worker，同时保存请求、标准输出、标准错误和求解回执对应的规范字节。它不改写上游源码、模型输入、求解结果或回执哈希。

在支持可执行 Python 脚本的系统上，把本次被测实例的 `analysis.pythonBin` 设为该脚本的绝对路径，并在启动该实例时指定：

```bash
export SCLAW_BENCH_PYTHON=/path/to/original/structureclaw/python
export SCLAW_BENCH_CAPTURE_ROOT=/tmp/sclaw-worker-captures
```

`SCLAW_BENCH_PYTHON` 是该实例原来使用的 Python 解释器，须具有原来的求解器依赖。非分析类 Python worker 会直接交给该解释器执行。这里只配置本次评估实例；不需要修改上游实现。

也可以由外部采集器显式调用包装器；这适用于不能直接执行 `.py` 文件的平台：

```bash
/path/to/original/python scripts/research300/capture_structureclaw_worker.py \
  /path/to/structureclaw/backend/src/agent-skills/analysis/runtime/worker.py \
  < actual-worker-request.json > actual-worker-response.json
```

每个调用生成一个独立目录，其中有 `request.json`、`stdout.json`、`stderr.log`、`capture.json` 和 `canonical/*.json`。评估器核对请求模型、已有请求 ID 和各项哈希后使用其中的字节。采集失败、请求不符或文件改变时不接受该证据。

包装器适用于新增的真实运行；它不能恢复已经丢失的历史字节，也不能将补跑结果伪装成原来的模型试验。采集目录可能包含实际题目输入和输出，应和本次实验记录一起保存。

文件哈希和内容绑定证明的是这些记录相互一致。真实执行仍依赖评估方控制的采集器、固定 worker 和原始采集目录；当前 CLI 不会自动建立不同用户或容器的写入隔离。如果候选进程能任意改写整套采集文件及哈希，仅通过离线校验不能独立证明原生求解器确实运行过。

## 商业求解器、报告和图像

所检查的上游 PKPM / YJK 输出主要在 `nativeContext` 中保存原生文件与物理映射证据。它们没有统一的 OpenSees 风格 `execution.executed / solverVersion / analysisReturnCode` 回执。适配器可以导入模型和结果，但不会凭 `nativeContext` 自动补写一次成功求解。严格执行证据评估还需要采集器保存真实原生进程状态、实际软件版本与原始文件哈希；缺失时报告相应限制。

报告读取实际的 `{summary,json,markdown}` 输出和运行绑定。`memberResponses` 等绘图数据不能证明图像已经交付。图像类要求需要采集包中的 `figures` 描述与实际 PNG/SVG 等文件；评估器读取并解码文件、核对运行来源。成功解码只证明文件可读；图像内容是否满足题意，需要独立评审实际图片、模型和结果，不能仅凭描述字段或一张空白图通过。

澄清回答同样需要评审其实际含义，不能只匹配问题或字段关键词。明确调用 `run_analysis` 等求解工具会直接违反本轮禁止分析的要求；独立评审不能覆盖这一失败。仅凭命令文本无法确定用途的工具活动进入待审，并提供完整事件供核查。

## 上游核对基线与验证范围

2026-10-26 重新核对了用户指定的 [`qinsz01/structureclaw` 的 `work/research-next`](https://github.com/qinsz01/structureclaw/tree/work/research-next)，当前固定提交为 [`00ecd812a315a75b7714d5fc030ec3652bfaf869`](https://github.com/qinsz01/structureclaw/commit/00ecd812a315a75b7714d5fc030ec3652bfaf869)，比原基线 `f83258b284cc2a083635925c3aeebb378ee96884` 新 110 个提交。这记录兼容性检查基线，不代表所有导入文件都由该提交生成，也不替代被测系统自身的实验冻结记录。

本机 Codex CLI 为 `0.164.0`。按该版本[官方 JSONL 事件定义](https://github.com/openai/codex/blob/rust-v0.164.0/codex-rs/exec/src/exec_events.rs)检查了轮次、助手消息、命令、MCP、协作工具和 usage 字段；新增回归保留 MCP 的 `_meta`、协作状态与被拒绝的命令活动，不把工具返回文字当作助手交付或求解证明。

本次适配器 83 项、工程评价 148 项、Research 300 回归 556 项全部通过，无跳过项。工程评价通过 `SCLAW_TEST_ROOT` 指向上述上游提交、`SCLAW_TEST_PYTHON` 指向具有上游依赖的解释器，实际执行 OpenSees 正向证据测试。

补充集成检查按上游固定的 `openseespy/openseespylinux==3.7.1.2`、`numpy==1.26.4`、`pydantic==2.11.5` 环境，运行其真实 Python worker、原始字节采集包装器和构件响应恢复代码。STD-001 的输出经上游实际聊天投影和流去重函数处理，再用 SSE 加运行归档与 Codex 事件加关联状态两种方式进入统一 CLI；两份评估均为 `passed`。这里的模型来自测试夹具、回答表格来自实际求解输出，验证接口和工程评价兼容性；未调用 Codex 模型，不是自主建模或 300 题盲测成绩。

同日通过 `codex_qsz` 在 `<native-host>` 的独立目录补验商业适配器，执行的 212 份上游源文件在前后均与上述提交一致。YJK 8.0.0 实际完成 STD-081 的 D 工况，原生 M0 求解进程退出码为 0；174 项请求数值按冻结严格容差全部一致。采集器保留真实进程回执、原生设置、完整适配器输出和 M0 日志，显式提供执行声明及文件哈希后，两种统一 CLI 入口均通过，包括 36 项派生量。上游实际聊天投影省略的 `nativeContext` 也可从同一运行归档恢复，并通过完整评价。仅提供未补充执行回执的原始 `nativeContext` 时，CLI 仍正确返回 `artifact_error`。原生日志保留活荷不利分组警告及各阶段返回记录，此检查只认证题定 D 工况，不宣称全部原生阶段均成功。

首次使用上述未修改的上游提交验证时，PKPM 在该机存在版本兼容问题：安装为 2027R1.0.1，`native_materials.py` 假定材料 DLL 与 `APIPyInterface.pyd` 同目录，实际分别位于 `Ribbon/PM` 与 `Ribbon/PythonEnv`，STD-091 在 JWS 生成阶段失败，未执行 SATWE。初次尝试的测试进程 DLL 搜索路径问题修正后仍复现此失败；两份记录均保留。该提交后续材料 ABI 和数值截面求解器检查还绑定 2025 指纹；首次验证没有跳过检查或修改上游。评估器拒绝该失败记录，没有生成成功评分。以下为用户随后授权修复后的独立记录。

PKPM 2027 兼容修复已在本地 StructureClaw 提交 `c16ca6fb397ca1d511f7ce2e5eff96134814eed2` 完成，基于上述上游提交，尚未推送。修复覆盖 SDK/DLL 路径、两套已校准二进制指纹、2027 空标准层工程的逐层保存、描述性弹性材料名称、`general` 数值截面及真实软件版本回报。未知版本、明确但不支持的牌号及未验收的 2027 规范设计配置仍拒绝，不修改历史冻结、题库输入、标答或容差。

最终修复源码的 213 份执行文件在 246 前后逐文件一致；全部 16 个 PKPM 案例、19 个模型状态均实际完成建模、四阶段运行和结果回读。257 项回归及 7 项子测试、分析接口契约检查通过。按原冻结严格容差核对 1672 项数值，1657 项一致；14/19 个状态全部数值一致，另 5 个状态有 15 项差异，涉及 STD-091、STD-089、INT-079 和 INT-089，均保留为失败，不能写成全题通过。116 项派生量核对通过。STD-080 的真实结果通过 StructureClaw 与 Codex 两个统一 CLI 入口；实际聊天投影也可通过同一运行归档恢复原生证据。这些仍是确定性工程夹具检查，未调用候选语言模型。修复补丁、数值明细、原始证据和清理记录见PKPM 2027 修复记录。

随后已定位并修复上述 15 项差异：SDK 根据矩形尺寸重算 A/I/J，实际输入与显式属性直接舍入值存在 1–3 ULP 差异；另有自由支座方向的端力闭合残差被当作支座反力矩。只修复输入的对照试验使 STD-089/STD-091 的 12 项超差消失；再按原生零转动刚度、无耦合证明恢复自由反力矩，同时保留原残差及既有拒绝限值。最终重新实跑 19/19 状态，1672/1672 项数值与 116/116 项派生量全部通过原严格容差；5560 项实际 DATA/SDATA 属性与显式输入和参考原生记录一致，没有放宽容差或修改标答。最终本地 StructureClaw 代码为 `f5a9d4e`，268 项回归及 7 项子测试通过。STD-080 两入口和实际聊天投影恢复通过；STD-091 整体仍待独立交互评审，其数值已通过。本次仍属于工程集成检查，详情见数值原因与修复证据。

商业原始证据已归档并逐文件校验；三项自有测试任务已移除，无残留商业进程，PKPM 共享目录配置哈希保持不变。版本、回执、CLI 结果、原始归档摘要与清理记录见首次验证记录；后续修复的任务清理另见对应记录。

验证包括完整状态、LangChain 消息、会话缓存、SSE 失效事件、压缩归档绑定、路径边界、原始负零字节与被修改采集文件。适配过程中还用相同后端实现的真实 OpenSees worker 执行了一个 6 m 梁中点荷载算例：Python 原始输出的三种回执均可验证；经 JavaScript 序列化后的输出通过透明采集恢复三种原始字节。

工程集成检查还直接读取 STD-001 的冻结模型，运行同一真实 worker 和上游构件响应恢复代码，再分别通过 StructureClaw 状态入口、Codex JSONL 加关联状态入口执行统一 CLI：两者的 7 项数值、模型、报告和执行证据检查均通过。保留原始回执但将构件弯矩改大 1 kN.m 后，评估器拒绝该输出。此处的模型和回答由测试夹具提供，验证的是适配与防篡改链路，不是模型自主完成题目的盲测，也不是 300 题的实测成绩。

最新提交的补充检查还覆盖 STD-040 空间桁架（246 个构件样本）和 STD-079 空间梁柱（1296 个构件样本）；两者的三类原生证据与逐样本绑定均通过。它们同样属于工程适配检查，未计入模型实测成绩。

## 用于两系统比较的条件

当前 MM 输入重建审查使用 [v2 协议](public-input-review-protocol-v2.md)，入口为
`npm run review:inputs -- export|seal|grade|verify ...`。物理正确、协议合规、澄清与来源观察分项报告，
总通过仍要求各必需项通过；工程任务的 `engineering-v2.3` 数值评分与容差不变。
旧输入包的新版诊断不能替代新协议下的独立审查，旧评分器和原始判定保留重放。

后续已补齐后端完整 Jest：264 套件、3806 项测试和 57 个快照通过，Windows 的 4 项补测通过。
完整回归需要的 Node 堆资源已在本地测试命令中配置为 8192 MiB；生产求解代码与容差未改。
Codex 的 12 道公开输入重建预检为 6 通过、5 失败、1 提交无效，不计为正式任务成绩，详见
补充检查记录。

2026-10-26 的全量就绪复核
重新通过了 787 项适配/评分/题库回归，并修复通用原生审计器遗漏商业 Timoshenko 梁与均布荷载的问题。
当前脚本重新生成的 300 题、475 组原生记录通过物理审计，8187 项参考比较通过原严格容差。
正式实验仍需当前输入独立盲审、两系统真实模型预试验和新的系统冻结。

统一入口是离线结果评估器，不是自动完成两套系统部署、逐轮调度与独立评审的实验运行器。可导入的文字也不等于完整工程交付；模型、实际求解结果、原始回执和图像应由两边的采集器按相同公开契约提供。不能向其中一方提供隐藏模型、答案或更宽松的证据要求。

正式比较前应先固定题目范围、输入绑定、两套系统的代码与模型版本、求解器版本、工具权限、时间或 token 预算、重试规则和评审口径。若比较整个系统，应说明各自的模型和工具配置；若要归因于 agent 编排，应控制基础模型与可用工具等条件。报告应分别列出成功、任务失败、基础设施或采集失败、未运行及待评审数量，不能只在成功或已审样本上计算一个通过率。

正式比较的行为评审需要评估方采集完整逐轮轨迹，包括失败或未完成的工具尝试、中间可见回答和最终状态。只有最终 Markdown 或缺少工具历史的快照时，空事件列表不能证明此前没有执行求解；这种材料可检查交付内容，不能据此认证“澄清前未分析”等行为要求。

当前 300 题的参考准备与原生证据核验不等于当前公开输入已通过独立盲审，也不等于候选 agent 已完成任务。正式比较仍需完成当前输入的独立审查，并让两系统分别用公开输入完成 STD、INT、MM 的小规模全链路预试验，核对逐轮可见文件、实际工具活动、求解证据、回答及图像。预试验单独记录，不计入正式成绩。PKPM/YJK 还需要可用的商业软件环境和真实执行采集；仅验证 OpenSees 链路时，应明确限定比较范围。


2026-10-26 的真实 Codex CLI 试跑补齐了启动 advisory 与 resume 后重复启动提示的导入兼容，原始事件仍保留，真正错误和越界活动仍拒绝。具体自主建模、原生执行和评分证据见真实试跑记录；不计为全量 300 题成绩。
