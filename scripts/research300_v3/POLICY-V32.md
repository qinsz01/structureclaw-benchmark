# v3.2 接入修订草案

此入口供后续接入使用，已补充本地离线回归，尚未取得实际原生采集环境的运行验收记录。默认入口、冻结 v3/v3.1、300题题面、私有数值、数值容差、Codex 原始答案和历史成绩保持不变。

当前没有 StructureClaw 正式300题成绩。历史 Codex 的483/560轮、263/300题属于旧输入协议的开发复核，不能作为新协议下的对照成绩。

## 比较规则

`audit-metadata-v32.cjs` 在一次性克隆上处理三维梁柱实际使用的截面。二维/纯轴力仍按冻结 v3.1 的投影规则处理。已识别、符合结构约定的 `extra.provenance`、`evidence`、`rules`、`derived_properties`、`confirmation`、`source`、已丢弃属性记录和已知诊断可从比较视图消去。原始状态、原生结果、回执、哈希和答案均保留。

该投影只区分来源记录与物理参数。它不认证来源声明为真，不重新生成属性，也不授予原生执行资格。刚度、截面属性、荷载、质量、支承、坐标、偏心与活动控制继续交由原比较器检查，数值响应容差不变。未知扩展字段保留；结构不符合约定的已知审计字段保留并标记。后者是唯一失败原因时，结果为 `needs_review`：只在诊断副本中移除这些标签、全部其余检查通过后确认。仍存在物理、响应、报告或身份错误时保留 `candidate_failure`；诊断副本不能授予通过。

规则检查仅核对记录结构、源截面/字段、维度以及记录中的比例算式。真实用户文本与附件来源的核验仍属于 Sclaw 模型边界；比较器不会替候选补充来源证据。派生缓存标签不覆盖实际数值，所有实际属性照常进入原物理比较。

## 输入协议 `verbatim-public-v3.2`

`prepare_readiness_v32.py` 只整理文件和静态条件，不导入评估器或 SUT、不运行候选/求解器/测试。

- 保留原 `task.json`、附件原字节、图片、后续变更顺序和同一题对话历史。
- L4 首轮在真实 `user` 消息中逐字附上 `design-catalog.json`、`engineering-brief.md`、`primary/section-families.json`、`upper/section-families.json`。这些是既有公开资料，没有增加计算结果。
- 保留原始 PNG 附件；不添加 OCR、坐标表、换算荷载、派生属性、最优选项或私有参考。
- 每个候选包只含该题当前及已签发的轮次；不复制控制端清单、评估源码、其他题或未来轮次。文件包本身不建立沙箱权限，正式投放仍须由现有隔离运行器执行访问控制。
- 逐轮只发送该轮 `user-message.txt`，并上传该轮原附件；上一轮保持会话。不能将该文本仅作为另一个普通附件，否则比例规则不一定进入 Sclaw 的 `userTexts`。
- 新输入协议应同等用于比较双方。旧 Codex 记录不追认成新协议结果。

生成器检查原公开文件的冻结哈希，完整控制清单不可放入候选可读目录。它不改变原题目录。准备示例：

```sh
python3 scripts/research300_v3/prepare_readiness_v32.py \
  --edition /path/to/frozen-edition \
  --configuration /path/to/operator-run-configuration.json \
  --output /path/to/new-controller-preparation
```

可追加 `--packet-case V3-INT-071 --packet-turn t2 --packet-output /path/to/new-case-packet`，只准备该题截至 t2 的公开文件。程序不会调用模型、应用服务或求解器。

## 运行前提

配置模板明确使用个人 fork 的远端 `work/research-next@00ecd812`。本地 `0a17bfdc` 的7个未上传修复、历史 Codex 的 `db3c0b1d` 必须显式选择，不会被静默当成远端能力。

配置中的模型、视觉模型、原生引擎版本、编程开关及预算尚待填写。工具调用上限遵守当前 Sclaw 的200次，不会自动提高。是否使用已有 Sclaw shell 单独声明；选用时同时声明 `allowShell` 和命令清单。原生调用须经指定入口，编程内嵌调用也须进入统一作业计数。声明配置不等于配置已生效，运行前提还要求控制端采集的应用配置回执。

原生环境以实际采集回执为准，历史记录不能冒充当前可用性。发布代码与已记录 PKPM 2027 安装不匹配，6题材料命名及2题 `general` 映射条件仍明确列出。15道 PKPM 题还有一项 Agent 输入边界风险：通用来源层生成的 `evidence/rules/propertyFields` 并非都被 PKPM 的窄截面契约接受，纯数值截面尤其拒绝非空 `extra`。本地7个修复没有整体解除这一条件；比较器消去来源标签也不能让原生入口接受它。后续采集器验收必须覆盖真实截面输入边界。

`readiness.json` 对300题逐题列出 `ready/conditional/blocked` 及原因。未经确认的视觉、预算、环境、采集器或评分规则不会被默认为就绪。该文件由控制端保管，评分时还必须提供它的外部固定 SHA256。

## 受控运行证据

`controlled-evidence-v32.cjs` 是受控索引的**读取与核验器**。后续已加入独立 worker 采集脚本、Windows 启动器源码与 `publish_capture_v32.cjs` 离线封存器，见[原生环境交付说明](NATIVE-HANDOFF-V32.md)。实际会话登记、运行采集和验收尚未执行，本轮没有制作可用的执行证书。

索引、回执和证据保存在候选不可写的控制目录，索引 SHA256 从目录之外由操作者固定。候选给出的 UUID、自建回执或原生结果摘要均不能认证执行。信任边界在独立受控采集器；读取器不把候选提供的任意 JSON 当成采集器证明，也不靠文件哈希本身推断求解器运行过。

索引的必要字段：

```json
{
  "schemaVersion": 1,
  "kind": "research300-v3-controlled-evidence-index",
  "editionManifestSha256": "<冻结 manifest SHA256>",
  "sutCommit": "<实际 SUT commit>",
  "inputProtocol": "verbatim-public-v3.2",
  "executionSpecificationSha256": "<准备文件中的执行配置 SHA256>",
  "turns": [],
  "entries": []
}
```

`turns` 每项含 `caseId/turnId/captureComplete/environmentStatus/candidateStatus/currentJobIds`；有交付时附 `answer:{path,sha256}`，保留原始结构化作答。`currentJobIds` 为采集器对本轮**全部原生尝试**分配的唯一32位十六进制编号，包括失败和未被答案引用的调用。只查询轮次不能靠漏报新作业绕过复用规则。已成功发布的 `entries` 必须出现在对应轮次的尝试清单中。

`environmentStatus` 为 `ready/blocked`，`candidateStatus` 为 `completed/candidate_failed/service_blocked/interrupted`。采集器须基于原始日志区分环境或服务故障与候选错误；缺失和中断不自动计作模型失败。

`entries` 每项含 `caseId/turnId/evidenceId/engine/origin/files`；`origin` 为 `broker/structureclaw`。`files` 的各值均为 `{path,sha256}`，只允许受控目录中的普通相对路径，不允许软链接、跨目录或文件哈希变化。

- 两种来源都需要原始 `receipt/state/model`。回执须为成功的 `candidate` 角色，同题同引擎，并绑定原状态 SHA。模型与受保护状态逐值一致，仅正负零视为相同。
- broker 另需原 `request`，与回执的 `requestSha256` 相符。
- Sclaw 另需原 `archive`、原 `runId` 及 `executionProof`。运行归档中的模型哈希、设置哈希、全部记录的 run/model/settings 绑定均按既有归档解析器核验。原始静力结果集合或动力数据必须与受保护状态逐值一致。
- `executionProof` 由独立采集器从真实 worker/商业原生执行产物发布，含 `kind:research300-native-execution-proof`、题号、runId、SUT、引擎、原模型文件 SHA、`workerExitCode:0`、`executed:true`、原生版本及非空的原始产物描述符 `artifacts`。回执另绑定 `executionProofSha256/archiveSha256`。动力还以 `parameters` 绑定实际设置。仅列一批无关文件不能满足采集器验收；实际输入、规范化设置、原生输出与归档的关联属于其必须核验的职责。

原 runId 只映射到采集器分配的 evidenceId，不改变任何数值。接受 `runIds/runIdsByModel/runIdsByScenario` 作为相应 `jobIds` 字段的互斥别名。同题可引用已签发旧轮次，跨题、未来轮次、未知引用、双重身份或 oracle 回执均拒绝。既有 jobIds 形式继续支持。

## 失败归因与资格

结果分为五类：

| 状态 | 含义 |
| --- | --- |
| `passed` | 实际证据、数值、身份和报告通过当前规则 |
| `candidate_failure` | 完整采集且前提满足后，候选缺交付、非法引用、错误模型/结果/决策等 |
| `blocked_configuration` | 环境、配置、输入协议或采集器前提不满足 |
| `ungradable_evidence` | 原件缺失、哈希冲突、采集不完整或接入异常 |
| `needs_review` | 新评分策略尚未验收，或审计字段尚无明确等价处理 |

分母固定为签发的全部560轮，不删除阻塞轮次以抬高通过率。有阻塞、证据异常或待复核时，`qualifiedPassRate` 为 null，`formalComparisonScore` 为 false。`--provisional` 只允许在其他条件满足时离线检查保存的证据，输出永远不标为正式成绩。

正式资格必须由控制端的独立验收回执取得：`kind:research300-v3-policy-qualification`、`revision:v3.2`，绑定原 manifest、新输入协议及全部评分源码依赖 SHA；560个正例全部通过、至少6591个既有反例控制全部通过，并补充审计等价、未知审计字段、物理输入严格性、受控身份绑定、原生执行关联、失败归因和逐字公开交付七类控制。数量门槛不是新策略已经验收的证据；当前没有这份回执。

配置相关回执均为控制目录中的 `{path,sha256}`。运行配置、采集器验收、引擎可用性回执分别使用 `research300-runtime-configuration`、`research300-v3-collector-qualification`、`research300-engine-availability`，并绑定 `sutCommit/editionManifestSha256/executionSpecificationSha256`。运行配置需 `configurationApplied:true`；采集器需 `revision:v3.2/allPassed:true/evaluationCode`，PKPM 另需 `sectionInputBoundaryEngines` 包含 `PKPM`；引擎需 `engine/version/available:true`。这些回执的发布流程尚待完整接线，本轮没有调用它们。

实际配置回执还需 `candidateIsolationVerified/controlFilesInaccessible:true`；允许 Sclaw shell 时还需 `shellIsolationVerified:true`。仅设置工作目录不构成权限隔离。未确认的控制边界继续列为配置阻塞。

离线评分的未来调用形式：

```sh
node scripts/research300_v3/grade_candidate_v32.cjs \
  --edition /path/to/frozen-edition --control-root /path/to/protected-capture \
  --index index.json --index-sha256 OPERATOR_PIN \
  --readiness /path/to/preparation/readiness.json --readiness-sha256 OPERATOR_PIN \
  --output /path/to/new-grade.json
```

2026-10-29 草案阶段遵守当时“不能测试”的约束，仅做源码审查、语法解析、文件准备和哈希核对。2026-11-01 在用户要求扎实完善 benchmark 后，完成了本地契约测试和封存正例/对照的离线重放，详见审查记录与[验收标准](REVIEWER-ACCEPTANCE.md)。本地检查没有调用候选或求解器，没有授予真实采集器验收或正式实验资格。
