# 公开求解工具与交付约定

工具目录提供 StructureModelV2 JSON schema、模型示例、原生结果说明和 analyze.py。Python 客户端接收请求 JSON 文件：

```
python /provided/tools/analyze.py --request request.json --session /provided/session --output result.json
```

静力请求为 `{"model": <完整模型>, "analysis":"static", "selection":{"kind":"combination","id":"SERVICE"}}`；基本工况用 kind=case。动力请求为 `{"model":<完整模型>,"analysis":"modal"或"transient","parameters":<本轮分析参数>}`；时程的 parameters.analysisType 为 time_history。时程 groundMotionFile 须先读取为 groundMotion 数组，groundMotionUnit 保持 g。返回真实 jobId 和原生 state/analysisResult。每次请求只能读取自己提交模型的结果，客户端不提供题目答案、转换后荷载、控制位置或最优方案。

交付 `answer.json`。所有数值都必须来自实际作业；作业 ID 不可编造。可自行编程整理施工资料、计算荷载、搜索设计和读取原生结果。面荷载与重力转换规则是题设的分析模型。相同物理输入允许改变内部 ID，评测将建立几何及输入对应关系；报告中的节点/构件采用图纸标注。允许正确换算单位，但不能只比较绝对值后丢掉符号。

L1/L2 的 quantities、derived 等格式见 task.json 的逐项要求及工具目录旧版数量交付约定。动力题沿用 quantities/modeShapes/jobIds 格式，并额外报告 `massTotal:{"value":数值,"unit":"tonne"}`，表示显式参与 X 向惯性质量之和。

L3 静力交付格式：

```
{"jobIdsByScenario":{"baseline":["job-..."],"relocated":["job-..."]},
 "metrics":{"baseline":{"uz":<指标>,"lateral":<指标>,"force":<指标>},
            "relocated":{"uz":<指标>,"lateral":<指标>,"force":<指标>}},
 "relativeChangeWhenRequested":{"uz":数值,"lateral":数值,"force":数值}}
```

仅有 current 场景时只交 current，无需相对变化。两个场景时相对变化定义为 `(abs(relocated)-abs(baseline))/abs(baseline)`，无量纲。每场景必须覆盖三个组合。uz 是全部分析节点有符号最大绝对竖向位移；lateral 是全部节点最大 sqrt(ux²+uy²)，非负；force 为全部梁柱两个端部 M2/M3 有符号最大绝对值（二维只 M2），纯轴力模型用 N，单位不得混用。

指标结构：`{"value":数值,"unit":"m"或"kN.m"或"kN","selection":{"kind":"combination","id":"..."},"governingJoint":"J..."}`；构件指标改为 `governingMember`、`positionM`、`side`、`component`（N/M2/M3）。端截面位置为沿签发构件 i→j 的距离，i 端 side=right，j 端 side=left。并列控制允许其中任一实际位置。

L4 交付格式：

```
{"design":{"G0":"A","G1":"B","G2":"C"},"feasible":true,
 "volume":{"value":数值,"unit":"m^3"},
 "metrics":{"upperVertical":<指标>,"primaryVertical":<指标>,
            "primaryLateral":<指标>,"primaryEndAction":<指标>},
 "jobIdsByModel":{"upper":["job-..."],"primary":["job-..."]},
 "transfers":[{"selection":{"kind":"case","id":"D"},
               "values":[{"upperSupport":"S0","primaryJoint":"J...","fx":数值,"fz":数值}]}]}
```

单向传递要求上部 D/Q/W 三个基本工况和主体三个组合的真实证据。transfers 含三个基本工况×四个接口，上部全局支座反力单位 kN。刚接组合题 jobIdsByModel 仅用 `combined`，覆盖三个组合；transfers 含三个组合×四个接口，报告 `ux`/`uz`（m）。选择本身、全部约束、体积、控制值及身份、接口传递/相容值和实际输入均独立核验。仅给正确设计标签或恰好相同数值不能替代真实建模证据。

后续轮次只签发变更。保留此前未撤销的输入；“只恢复初始 Q”不表示恢复 D 或撤销新增设备。不得查看其他题、未签发轮次或私有参考资料。评测不向候选返回分数或修改建议。
