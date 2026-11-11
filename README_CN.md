# StructureClaw Benchmark

[English](README.md)

运行记录、原始会话和原生求解证据存放在仓库之外的归档中，不纳入版本库。

Research300 v3 工程建模与决策版
已调整为300题、560轮，难度分布30/60/120/90，包含90道耦合工程决策题。
隔离Codex开发试测、原生验收与正式实验剩余条件分别记录，旧版及历史成绩保留。

Codex完整作答与复核
已完成300个新题目会话、560轮交付。复核后483轮、263道整题通过；修正57轮评价器误拒，未改动作答或数值容差。
首评、剩余荷载输入错误、原始答案和Excel均保留。此次全量校验已使用原留出题。

完整 Research300 v2 新版
已将全部 300 题重编为 540 轮，包含 60 道工程改编题，设计难度分布为 60/120/90/30。
新版输入、参考、预检证据及候选试验待办独立记录；下方默认命令和历史成绩仍对应原版题库。

300 道结构工程题，中英文各半：标准流程、交互任务、多模态建模各 100 题，
共 420 轮对话，使用 OpenSees、PKPM 和 YJK。

300 题均已具备参考结果并通过原生证据核验；当前输入的独立盲审和候选模型实测尚未完成，
当前 StructureClaw 还需建立新的实验冻结。最新就绪检查
列出了验证结果、已知跨引擎差异及正式实验的剩余条件。
后端与 Codex 输入预检
补充了完整后端回归、Windows 进程测试及 12 道公开输入重建结果。
新增输入审查使用 [v2 协议](docs/public-input-review-protocol-v2.md)及
`npm run review:inputs -- export|seal|grade|verify ...`，分别报告物理、协议、澄清和来源观察；旧版入口保留用于历史重放。
当前评分器为 v2.1，题包协议仍为 v2；补充压力测试记录了后续修复和反例检查。

[截面多样性候选新版](docs/section-diversity.md)已生成独立的 300 题输入：267 题调整编题补充的截面，33 题保留明确尺寸或特殊截面。
该版本有独立的来源绑定和数值检查，尚未替换本页默认题库；历史 Codex 成绩继续对应原题。

## 使用题目

导出完整题目包：

```sh
npm ci
npm run export:research300 -- --output /tmp/structureclaw-benchmark
```

题目包只包含目录、逐轮指令和输入文件。多模态每轮只给**一张 PNG 图纸或一个 DXF**，
材料、截面、荷载及必要说明均在图纸内。标准题和交互题每轮最多附一份可读输入表；
后续轮次按对话顺序提供补充信息。

题目包不含答案、评分记录、校验码和内部审计信息，可以作为模型的输入来源。

## 查看预览

```sh
cd viewer
npm ci
npm run build
npm run preview
```

打开 <http://127.0.0.1:4173/>，默认查看题目和参考结果；需要核验来源时再打开维护模式。
预览包含参考答案，与供模型使用的题目包分开。

当前题库的[分类说明](docs/research300-classification.md)、[Excel 总表](planning/releases/StructureClaw_Benchmark_300题_当前版.xlsx)
和[统计 JSON](planning/releases/research300-catalogue.json)使用同一份分类与计数规则。网页支持分类筛选，并提供当前 Excel 和 JSON 下载。
`planning/sources/` 中的原始工作簿保留为规划归档。

```sh
npm run catalogue:research300  # 更新当前 Excel 和统计 JSON
npm run check:catalogue       # 检查当前总表是否与题库一致
```

## 评估

评估检查模型是否符合题意、是否使用指定引擎实际求解、带符号数值与单位、交互行为及图形。
Codex 与 StructureClaw 的结果使用同一个评估入口：

```sh
npm run prepare:evaluation -- --case STD-001 --output /tmp/bench-STD-001
npm run evaluate -- --input /path/to/result.json --case STD-001 \
  --context /tmp/bench-STD-001/capture-context.json --output /tmp/assessment.json
```

准备命令默认只释放第一轮。后续轮次使用 `--turn t2`（以题目实际轮次 ID 为准）
生成新目录，其中只有截至该轮的历史。仅将 `agent-input/` 提供给被测系统，
并隔离未来输入包、采集上下文和参考数据。Codex 的 JSONL 事件记录可以用
`--state` 关联实际生成的模型和求解状态。[结果适配与采集说明](docs/result-adapters.md)
列出了 Codex、StructureClaw 完整状态、会话、SSE 与运行归档的用法；参考结果验证和
评估证据说明见 [Research 300 使用说明](docs/research-300.md)。

导出、评估和预览统一使用 `corpora/research-300/public-inputs/` 中的[当前公开输入](docs/public-inputs.md)，
不提供版本选择；缺失或损坏的输入会直接报错。原始题源与历史审计证据保留用于追溯。
历史评分规则见 [SPEC_CN.md](SPEC_CN.md)。

## 许可证

MIT
