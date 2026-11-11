# Challenge 6 v1 / 六题挑战试验集

这是独立于 research-300 的候选挑战集，共 **6 题、18 轮**，用于检查原始 300 题覆盖较少的建模决策、资料整合与长流程修改。当前分析范围仍是经过验证的一阶弹性静力 OpenSees；没有用未支持的分析能力增加难度。

| 题号 | 轮数 | 要求 |
| --- | ---: | --- |
| CH-001 | 6 | 48 节点、88 构件的三层空间框架；活载修改、柱局部轴旋转、材料变化和局部撤销相互独立 |
| CH-002 | 6 | 同名工况/组合、局部恒载区间、点荷载位置/幅值的分别撤销，以及不重新求解的单位查询 |
| CH-003 | 1 | 几何只见 PNG，需与构件、材料、截面、荷载清单联合建模，无并行 SVG 或节点坐标 CSV |
| CH-004 | 1 | 正式修订单只覆盖指定构件的截面与恒载区间，其他字段保留原清单 |
| CH-005 | 2 | 必要支座自由度未知，先针对性澄清，确认后实际分析 |
| CH-006 | 2 | 同等签发资料对柱转角冲突，先确认优先取值，再计算不同组合 |

“更难”目前指增加了任务处理要求，不是已经完成的多模型难度结论。这六题使用两个基础拓扑，主要作为不同资料和交互条件的对照，结构多样性仍有限。候选题的输入尚无外部独立盲审。题源与输出要求在候选实测前固定；实测分数独立记录，不替换原版 300 题或其成绩。

首轮同款 Codex 实测已完成：**6/6 题、18/18 轮通过**，24 次实际后端求解全部成功。原评估器对合法模型表达的误判经 v2/v3 显式修正，全部原始作答和旧评分保留，数值容差没有改变。该结果说明本轮增加的要求尚不足以拉开 Codex 的表现。完整依据见 [试跑复核](../../docs/implementation/reviews/challenge-pilot-20261028/README.md)。

## 接口条件

采用 **documented-common-backend** 条件：候选可以阅读通用模型 API 与分析接口说明，由自己生成模型，再调用相同的实际求解后端。它无需训练时就知道私有接口。接口文档、合法工具报错是候选可见信息；隐藏模型、参考值、未来轮次和评分反馈不是。

本版使用较短的任务入口提示，将必要工具知识集中在 [tool-contract.md](../../scripts/challenge/tool-contract.md) 和公开模型 schema 中。文档继续说明单位、调用方法和交付结构；不逐步指导某题如何建模、如何修改或如何检查答案。已释放的早期资料可继续读取，只有未来资料隐藏。任务内容和提示方式同时变化，因此成绩差别不能单独归因于其中某一因素。

与 Sclaw 比较共同后端下的任务处理能力时，应给双方相同的可用文档、题面、求解服务、轮次释放规则和预算。Sclaw 原生集成与安装配置能力属于另一种实验条件，需要另行报告。

## 参考与评分

- 每个确定状态均由独立矩阵方法和独立 OpenSees 接口交叉计算；26 次原生参考求解均在原请求容差下通过。
- 额外通过固定 StructureClaw 提交的实际后端验证，保留原始 worker 输出与捕获记录。查询轮复用已有结果，不产生新的后端求解。
- 模型必须物理等价；数值必须来自受信任协调器的当前真实执行。查询可复用同一物理模型的旧执行。复制参考值、修改返回数值或伪造运行标识不能替代执行证据。
- 数值交付接受公开说明的结构化 JSON 与兼容单位换算，不靠输出排版制造难度。所有值要求有符号、单位、位置和精确工况/组合。
- 对缺项/冲突题，先提出定位到具体字段的必要问题；未确认时不允许求解。不会因为“问了任意一个问题”就通过。

`manifest.json` 的 `candidateRuns: 0` 是生成时记录，不是实时试跑计数。该文件及列出的公私源文件按 SHA-256 绑定；后续候选执行另有自己的 `source-binding.json`、原始事件和评分。`cases/*/private` 含维护者模型与参考，禁止作为候选工作目录。

## 复核与执行

在仓库根目录，使用含 NumPy、Pillow、OpenSeesPy 和对应后端依赖的 Python 环境：

```sh
python -m unittest discover -s scripts/challenge -p test_challenge.py -v

python scripts/challenge/verify.py \
  --edition corpora/challenge-6-v1 \
  --sut /path/to/pinned/structureclaw \
  --work /tmp/challenge-oracle-new
```

验证是维护者正例与错误反例控制，不能计作模型作答成绩。`verify.py` 保存每个原生运行、18 轮评分及错误截面、反向荷载、错误报告、修改结果、缺少真实执行、复用过期执行等反例。

先准备候选环境（默认不调用模型）：

```sh
python scripts/challenge/run.py \
  --edition corpora/challenge-6-v1 \
  --sut /path/to/pinned/structureclaw \
  --python /path/to/runtime/bin/python \
  --work /tmp/challenge-prepared-private-new \
  --base /tmp/challenge-prepared-public-new
```

实际执行时，使用另一组不存在的 `--work` / `--base`，增加 `--execute`；默认模型为本次基础集同款 `gpt-6.1-sol`、high。通过 `--cases CH-003,CH-005` 可显式选题。协调器只将候选提交的数值模型交给真实求解器，候选环境禁止网络及维护者目录访问。每题使用独立会话，各轮保持同一会话；每轮结果保留，不按分数重试。

运行器保留试验最初的 v1 评分，最终成绩需对所有未改动的原始作答统一重放 v3，避免把 SDK 默认字段、零组合系数或严格约束的平面三维表达误判为物理错误：

```sh
python scripts/challenge/replay.py \
  --edition corpora/challenge-6-v1 --run /tmp/challenge-private
```

单轮评分重放：

```sh
node scripts/challenge/evaluate-v3.cjs \
  --edition corpora/challenge-6-v1 --run /tmp/challenge-private \
  --case CH-001 --turn t1 --output /tmp/challenge-replay-new.json
```

只在本地维护；本轮不上传。
