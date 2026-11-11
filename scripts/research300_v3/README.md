# Research300 v3 工程建模与决策版

> 2026-11-11 冻结前验证约束：全部 300 题均只用于评测，catalogue 中的 dev/test 字段作废。候选接入调试、冒烟及验收只用排除同源/相近模型后的旧题或非 benchmark 产品夹具。下文历史开发集叙述只解释过去运行，不再构成运行授权。冻结协议草案见 [freeze-draft-20261111](../../docs/implementation/freeze-draft-20261111.md)。

独立版本为 [research300-v3-v1](../../corpora/research300-v3-v1/catalogue.md)。300题、560轮，STD/MM/INT各100题；每种形态的L1/L2/L3/L4为10/20/40/30，全局为30/60/120/90。旧版题库、默认导出和历史成绩保留。

2026-11-11 冻结验证约定：全部 300 题仅用于评测，catalogue 中的历史 dev/test 字段作废。候选系统的接入调试、冒烟和验收使用与 v3 来源及几何/拓扑不重叠的旧题或独立探针；下文候选运行示例仅记录历史入口，不用于本次冻结验证。

本版提高的是工程建模和决策要求。90道综合题含78道单向反力传递、12道刚接组合，每题有三个独立截面组、27种组合、四项全局响应约束和总体积目标。81道首态可行题至少有两类约束分别影响最优解；9道首态无可行方案，必须交付最小最大利用率的见证设计。INT综合题中27/30会在后续变更中改变最优设计集合。

120道L3含90道静力分区重布比较、20道质量推导模态题和10道质量推导线弹性时程题。静力题须保持Q总合力并改变其空间分配，搜索全部节点、组合及规定构件端截面的真实控制位置。动力题由D+规定比例Q推导X向质量，再检查周期、振型或固定步长时程峰值及峰时。INT的L1/L2/L3/L4分别为2/3/4/4轮，后续只签发变更，并选择性恢复Q而保留设备恒载。

210道原创题、10个工程/文献项目组的60道改编题，以及30道保留已核验物理题核的商业端题。新增分配梁、荷载、等效截面和限值均明确属于作者设定。它们是现有框架内的线弹性子结构任务，不是原工程全模型或规范认证。保守拓扑仍为229类，版本增加决策复杂度，没有把截面或编号变化计成新拓扑。

## 输入和证据边界

L1/L2沿用冻结的低中难度资料格式。L3/L4由轴网、节点定位、构件分段、连接详图和面荷载分区重建，不提供完整求解模型、预换算荷载、控制位置或最优选项。70道高难MM采用轴网图和图像尺寸键；30道低中难MM保留可读节点表图像。图纸中的尺寸为权威值，布局为示意图。

维护者输入审计从公开资料读取全部几何、连接及支承，包括图像字体模板转写；载荷与修订资料完整性另行核对。字体模板转写是源引导检查，不是外部盲审。独立直接刚度/质量凝聚/Newmark参考与生产求解器分离。原生预检检查所有轮次的实际执行和最终选择；每个27方案集合的独立计算保留在私有参考中，不要求候选穷举27次原生作业。

`run_candidate.py`默认仅运行明确选定的开发集Codex校验；显式`--scope full`才允许全量题目和商业引擎。根目录默认拒绝，逐轮开放当前及历史题面、通用工具和本题scratch；私有参考、评测源码、其他题、后续轮次、用户配置和网络均由负向探测检查。对话按同一thread续接；评分在候选运行之外完成，不提供反馈。StructureClaw正式对比尚未运行；全量验证的进度和留出集使用情况另行记录。

## 评分策略

`evaluate.cjs`同时检查被执行物理输入、指定引擎的封存回执、真实响应、带符号报告、单位、控制身份、接口值和全局最优性。高难题逐个已执行工况比较有效荷载，允许不影响当前物理状态的作业复用及正确的内部ID映射。

全局指标还在独立参考的对应控制位置核对原生带符号值；每项接口值也逐分量核对独立参考。不能因实际输出和报告同时反号而通过。合法并列控制位置仍可报告，振型的整体符号和尺度等价仍保留。

本版单独修正四类误拒：JSON的正负零；明确为空的非物理默认集合；空offsets导致曲线恢复降级时读取原生准确端力；分布荷载相同端点的浮点分裂。准确端力适配只允许已完成线弹性作业、明确的原生局部端作用矢量和已验证的轴系，i端取负、j端保留。它不生成中间截面或恢复曲线，也不修改受保护状态。分布荷载采用既有1e-8 m物理位置精度，同时要求合力、一阶矩和区间强度一致，短而强的错误荷载不能因位置合并消失。数值响应容差保持原规则。

高难物理比较器是冻结比较器的本版分支；旧版源码和SUT保持原样。非空扩展、真实偏心、错误支承、材料、荷载、重力和控制输出仍须被拒绝。详见本目录测试以及逐轮正例和反例记录。

## 本地复现

使用带numpy、Pillow、pydantic 2、OpenSeesPy的Python环境；本次环境为 `/home/openclaw/.structureclaw/.venv/bin/python`，Node为22。SUT固定为 `db3c0b1da44fe668a6037a6c2e7f068d14354539`。

以下命令均要求新的输出目录，保留此前失败记录：

```sh
python -m scripts.research300_v3.specs --cache /tmp/v3-project-cache --output /tmp/v3-assignment.json
python -m scripts.research300_v3.build --assignment /tmp/v3-assignment.json --output /tmp/v3-edition
python -m scripts.research300_v3.audit --edition /tmp/v3-edition --output /tmp/v3-input-audit
python -m unittest scripts.research300_v3.test_mechanics -v
node --test scripts/research300_v3/test_evaluate.cjs
```

原生预检采用通用broker/client。商业作业需要此前授权并核验的<native-host>安装记录与129个固定源文件，不能在缺失时假装求解成功：

```sh
python scripts/research300_v3/run_oracle.py --edition /tmp/v3-edition --work /tmp/v3-native-work --base /tmp/v3-native-sessions --sut /path/to/pinned-sut --local-workers 8
node --max-old-space-size=4096 scripts/research300_v3/qualify.cjs /tmp/v3-edition /tmp/v3-native-work /tmp/v3-qualification
```

开发集候选试验与评分分开运行：

```sh
python -m scripts.research300_v3.run_candidate --edition /tmp/v3-edition --work /tmp/v3-candidate-work --base /tmp/v3-candidate-sessions --sut /path/to/pinned-sut --cases V3-STD-071 --model gpt-6.1-sol
node scripts/research300_v3/grade_candidate.cjs /tmp/v3-edition /tmp/v3-candidate-work /tmp/v3-candidate-grade.json
```

完整300题作答须显式指定`--scope full`，此模式也允许240道留出题及商业引擎；默认开发集边界不变。商业端使用经重新核验的安装记录，两个候选可并行思考，实际PKPM/YJK作业仍经独占锁串行运行。每题保留独立会话，INT轮次在同一thread续接；全部候选只得到自身真实求解器反馈，评分在外部进行。新的全量验证记录不覆盖此前13题的开发校验，也不自动构成与StructureClaw的正式对比。

```sh
python -m scripts.research300_v3.run_candidate --edition corpora/research300-v3-v1 --work /tmp/v3-full-work --base /tmp/v3-full-sessions --sut /path/to/pinned-sut --scope full --remote-state /path/to/verified-native-work --workers 6 --commercial-workers 2 --model gpt-6.1-sol
node scripts/research300_v3/grade_candidate.cjs corpora/research300-v3-v1 /tmp/v3-full-work /tmp/v3-full-grade.json
node --test scripts/research300_v3/test_candidate_scope.cjs
```

首次协调器因调用服务错误而中断时，先关闭本次拥有的原协调器和CLI进程，等待原broker封存待完成作业，再运行`resume_candidate.py`。该入口保存中断尝试、续接原thread，绝不重答已完成轮次，也不提供评分反馈；HTTP429及“Selected model is at capacity”等服务错误可在同一会话冷却后续接。上下文耗尽和模型输入错误不按此类服务错误自动重试。`work/candidate-concurrency.json`只控制新调用的并发与冷却，不中断已在运行的会话；全部调整保留历史。现有协调器仍在运行时，先保留未完成轮次并等待其余作业封存，再启动下一次恢复。本次全量验证采用自适应并发，耗时包含限流等待，不能用于正式速度比较。

```sh
python -m scripts.research300_v3.resume_candidate --edition /tmp/v3-edition --work /tmp/v3-full-work --base /tmp/v3-full-sessions --sut /path/to/pinned-sut --model-slots 2
python3 -m scripts.research300_v3.summarize_candidate --edition /tmp/v3-edition --work /tmp/v3-full-work --grade /tmp/v3-full-grade.json --output /tmp/v3-full-review
python -m scripts.research300_v3.archive_candidate --edition /tmp/v3-edition --work /tmp/v3-full-work --sessions /tmp/v3-full-sessions --grade /tmp/v3-full-grade.json --output /tmp/v3-full-review/evidence
python3 scripts/research300_v3/verify_candidate_archive.py --review /tmp/v3-full-review/evidence --replay
```

Excel导出需要`openpyxl`。原始作答按字节复制、逐文件保留SHA256，Excel长内容分片，不截断；无效JSON也作为实际交付保存。离线重评分使用归档源码与封存原生状态，不调用模型或求解器。文件系统错误的绝对路径仅作诊断位置映射，数量、指标和容差不变。相应检查为`test_candidate_recovery.py`、`test_candidate_archive.py`及`test_candidate_summary.py`。

Codex调用方式按[官方非交互模式文档](https://learn.chatgpt.com/docs/non-interactive-mode)及已安装CLI核对。候选为强模型开发校验，修正评测器后重评分不能当成独立留出集成绩；难度标签不以制造模型失败为目标。

最终输入审计、完整原生评分、实际候选成绩、分卷证据和未完成的正式实验条件见本版审查记录。所有保存和提交均在本地完成，不push或部署。

完整300题、560轮的候选作答与复核记录已另行保存。冻结首评使用原`grade_candidate.cjs`，为426轮通过；同一批答案经独立的`grade_candidate_v31.cjs`复核为483轮通过，57轮误拒得到修正。原四个数值源码、题面、参考数值、容差和原始答案均不覆盖。

```sh
node scripts/research300_v3/grade_candidate_v31.cjs /tmp/v3-edition /tmp/v3-full-work /tmp/v3-reviewed-grade.json
python3 -m scripts.research300_v3.qualify_parallel --edition /tmp/v3-edition --work /tmp/v3-native-work --output /tmp/v3-reviewed-qualification --workers 6
python3 -m scripts.research300_v3.audit_load_arithmetic --edition /tmp/v3-edition --output /tmp/v3-public-load-arithmetic.json
node --test scripts/research300_v3/test_evaluate_v31.cjs
python3 -m unittest scripts.research300_v3.test_load_arithmetic -v
```

复核版按已执行分析区分活动物理输入。显式节点质量的线性动力检查全部质量及动力设置，不以未执行的静力工况台账作额外门槛；未耦合静力中的节点质量不会成为惯性门槛。SDK精确默认值与省略值等价；纯几何自然层分组仅在所有自动行为关闭时消去。非空扩展、活动控制、真实几何、荷载、支承和刚度仍严格检查。端力适配允许明确为空或六个已知偏心分量精确为零的记录，只读取真实求解器端矢量并核验轴系。

封存时可用`archive_candidate --reviewed-grade /tmp/v3-reviewed-grade.json`同时保存首评和复核评分；`verify_candidate_archive --replay`会分别重评分并核对同一批原始交付。

用户个人fork最新开发分支的300题逐题静态能力审查另行记录。审查以GitHub `work/research-next@00ecd812`为主基线，并区分本地未上传的`0a17bfdc`和历史Codex使用的`db3c0b1d`；只读取题设、源码及既有参考记录，未调用候选、求解器或测试套件。PKPM安装版本、综合题规则证据/编程预算、视觉配置和v3运行证据接入条件逐题列出，不将Codex完成率当作sclaw能力覆盖证明。

后续评估与输入接入修订新增显式选择的 v3.2 草案：[协议](POLICY-V32.md)、逐题前提/逐字公开输入准备、受控证据读取器，以及审计元数据比较和失败归因。它尚未运行验收，不能替代默认冻结入口或历史成绩。当前模板为15题阻塞、285题附条件，不能据此报告模型失败率。本轮只做静态文件准备、语法解析和哈希核对，没有试答、求解器调用或测试。

最新原生兼容与证据接入后续修订增加独立本地 Sclaw 兼容提交 `4f63d909`、原始 worker 采集、Windows 启动器源码、离线证据封存和本地交付包。[交付协议](NATIVE-HANDOFF-V32.md)明确 Windows 原生执行与本地控制/评分职责；没有上传、部署或运行验收。新本地版本的300题仍全部附条件，远端和历史结果保持原样。旧修订记录的源码指纹对应其原提交，最新源码指纹见后续记录。

2026-11-01 的审稿意见加固记录补充 v3.2 契约测试，修复审计标签掩盖独立错误的失败归因，并用封存原生结果完成560/560正例、6591/6591对照的离线回归。新入口没有改变冻结 v3/v3.1 或历史成绩。[验收标准](REVIEWER-ACCEPTANCE.md)明确等价域、容差、独立工程师审查和正式对照/消融要求；60题105轮初始盲审材料已经准备，人工审查未完成。运行资格仍为300题附条件。

```sh
npm run test:research300-v32
npm run test:research300-v32-inputs
```

新增独立的 [Codex v3.2 小批量接入入口](CODEX-V32-SMOKE.md)：逐轮原文/原图投递、控制端登记原生请求、封存真实答案与完整执行证据，再由独立诊断入口评分。该入口仅用于明确选择的 OpenSees dev 题，固定历史原生后端，始终保留 `formalComparisonScore:false`；不改变默认冻结入口或放宽正式资格检查。进程预算与采集测试可运行 `npm run test:research300-v32-codex`。

2026-11-01 的真实试答与冷重评记录：预选7题11轮通过，72次候选原生求解完整保留；150项初始对照和4项旧状态证据对照符合预期，独立目录重评文件逐字相同。该记录包含实际可读的证据链示例及两次无候选调用的启动失败，不能解释成全库难度或正式论文成绩。

## 分离的档案输入与 v3.3 维护者重放

源码仓库不保存运行证据。需要历史审查记录的工具通过 `SCLAW_BENCH_ARCHIVE` 选择档案仓库根目录（其下包含 `docs/implementation/reviews/`）；未设置时保留旧路径兼容。输出仍应放在当前仓库的 `.bench-work/`，不要指向只读档案。原始答案、原生状态和题库须分别显式传入。

```sh
export SCLAW_BENCH_ARCHIVE=/path/to/read-only-archive
python3 -m scripts.research300_v3.replay_retained_parallel_v33 \
  --edition corpora/research300-v3-v1 --work /path/to/retained-native-work \
  --answers /path/to/flat-retained-answers --output /path/to/new-replay --workers 6
```

新入口将同一批维护者原件和原 v3.2 对照应用于 v3.3，单独保存源码指纹。`--answers` 必须直接包含 `CASE/TURN/answer.json`；对分片目录先查原始清单及逐文件 SHA，不能猜测或重新生成答案。v3.2/v3.3 判定源码及数值容差不变。离线回归不会授予真实采集器验收或正式实验资格。
