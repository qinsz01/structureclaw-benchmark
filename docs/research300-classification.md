# Research 300 题目大类与能力子类说明

现有 **300 题**分为 **3 个题目大类**（`family`）：STD 标准工作流、INT 交互与稳健性、MM 多模态逆向建模。各大类再按主要考点分为共 **22 个能力子类**（`category`）：STD 6 个、INT 9 个、MM 7 个。每题只有一个 `category` 和一条逐题判定的归类理由 `rationale`，分类题数合计始终为 300；一题涉及的其他要求仍保留在题面和合同中，不再按第二标签重复计数。分类是基准元数据，不改题面、状态、参考结果、容差或评分规则，也不表示被测模型已经通过对应能力。

确定性映射在 [research300-taxonomy.json](../planning/research300-taxonomy.json)。`schemaVersion=1`；`categories` 提供稳定英文键、所属题目大类、双语名称和定义，`cases` 明确列出全部 `STD-001..100`、`INT-001..100`、`MM-001..100` 的唯一归属与理由。消费端按 ID 查表，不使用题名关键词重新分类。

## 统计与适用范围

| 计数口径 | STD | INT | MM | 合计 |
| --- | ---: | ---: | ---: | ---: |
| 题目 | 100 | 100 | 100 | 300 |
| 输入轮次 | 100 | 215 | 105 | 420 |
| 合同登记的模型状态项 | 100 | 164 | 100 | 364 |

420 是对话输入轮次数，364 是合同 `modelStates` 条目数，包含修改和恢复状态；两者都不是题数。364 也不是对物理结构去重后的数量。澄清轮不一定有可计算状态，纯查询修订不一定建立新物理状态。

分析范围为题定引擎下的**一阶线弹性静力**。杆系几何、约束、实体材料截面、荷载、工况、查询位置及输出表达构成本分类范围；轴压响应不等于稳定验算，混凝土弹性分析不等于配筋或承载力设计。分类不新增动力、非线性或规范设计能力结论。

难度 `L1/L2/L3` 沿用原规划的**预设复杂度**，独立于能力子类；不是用被测模型成功率、耗时或实测结果校准的经验难度。求解器分配与结构类型也保留为独立元数据，不作为能力子类划分依据。

## STD：标准工作流

以任务区别于普通完整建模的主要要求归类。边界与连接关注约束/自由度语义及共节点；几何与拓扑关注外形、网格、构件存在性及端点图。材料/截面关注属性及分组赋值；局部轴朝向和带符号坐标变换归单位与坐标。荷载与组合关注加载和工况关系。仅在报告形式本身是明确区分点时归结果与报告，不能因为每题都要输出反力或位移就把它们全部归入结果类。

| 能力子类 / English | 稳定键 | 题数 | 代表题 |
| --- | --- | ---: | --- |
| 边界与连接语义 / Boundary and connectivity semantics | `std_boundary_connectivity` | 15 | STD-002、STD-015、STD-036 |
| 几何与拓扑建模 / Geometry and topology modeling | `std_geometry_topology` | 33 | STD-032、STD-067、STD-100 |
| 单位与坐标解释 / Units and coordinate interpretation | `std_units_coordinates` | 9 | STD-007、STD-090、STD-094 |
| 材料与截面映射 / Material and section assignment | `std_materials_sections` | 14 | STD-013、STD-073、STD-089 |
| 荷载与工况组合 / Loads, cases and combinations | `std_loads_combinations` | 28 | STD-019、STD-055、STD-091 |
| 结果查询与报告 / Result queries and reporting | `std_results_reporting` | 1 | STD-006 |

STD 的复合题按逐题理由明确主考点，例如 STD-026 的截面组（第二、三跨 B2）与活载组（第二、四跨）交错，因此归入材料与截面子类；加载要求仍保留。STD-006 实际要求一页计算摘要并与结构化表一致，是结果与报告子类的真实例子。各子类数量来自逐题判定，不为凑齐组数平均分配。

## INT：交互鲁棒性

INT 首先按**交互行为**划分，基础梁、桁架或框架仍由独立结构类型字段描述。以下主要考点优先规则按顺序确定唯一能力子类：

1. 有明确的历史撤销/恢复操作，归撤销与状态恢复；须维护不在撤销范围内的其他轮修改。
2. 初始记录对同一字段给出不兼容值、映射或维度，归冲突信息澄清，即使后面还包含更新。
3. 初始输入的单位、方向、原点、轴映射、线载长度或折算基准未明确，归单位、坐标与荷载基准澄清。
4. 初始物理必需字段仍缺失，或长度/几何明确无效，归缺项与无效输入处理；不将合法负绝对坐标和带符号荷载归为无效。
5. 有效物理模型不变、只改查询位置/范围/输出单位，归结果查询与表达修订。完整输入且无后续修改的对照任务归直接执行。
6. 其余有效模型编辑按对象归类。混合编辑链采用**几何/拓扑 → 材料/截面/局部轴 → 荷载/工况/组合**的主要考点优先顺序；不是只看最后一轮。已建立有效模型后，对编辑目标、版本或范围的确认随该编辑对象归类。

| 能力子类 / English | 稳定键 | 题数 | 代表题 |
| --- | --- | ---: | --- |
| 缺项与无效输入处理 / Missing and invalid input handling | `int_missing_invalid_input` | 17 | INT-017、INT-040、INT-069 |
| 冲突信息澄清 / Conflicting information clarification | `int_conflict_clarification` | 14 | INT-004、INT-057、INT-098 |
| 单位、坐标与荷载基准澄清 / Unit, coordinate and load-basis clarification | `int_units_coordinates_clarification` | 12 | INT-025、INT-048、INT-094 |
| 材料截面与成员组定向更新 / Targeted property and member-group updates | `int_targeted_parameter_update` | 10 | INT-013、INT-077、INT-090 |
| 几何与拓扑更新 / Geometry and topology updates | `int_geometry_topology_update` | 11 | INT-006、INT-049、INT-087 |
| 荷载、工况与组合更新 / Load, case and combination updates | `int_loads_combinations_update` | 18 | INT-019、INT-056、INT-091 |
| 撤销与状态恢复 / Undo and state recovery | `int_undo_recovery` | 7 | INT-026、INT-074、INT-088 |
| 结果查询与表达修订 / Result query and presentation revision | `int_result_query_revision` | 3 | INT-003、INT-033、INT-097 |
| 完整合法输入直接执行 / Direct execution of complete valid input | `int_complete_input_execution` | 8 | INT-024、INT-036、INT-068 |

边界例子：INT-017/070 的负相对长度是录入错误；INT-068 的负绝对基底标高是合法完整输入。INT-024/051 的正负荷载是直接执行对照。INT-033 只是额外极值查询范围待确认，已有常规结果仍可计算。INT-026 撤回早一轮荷载修改时必须保留较新截面修改。INT-090 移除的是初始模型已有局部轴旋转，不是撤回对话上一轮操作，因此归定向属性更新。INT-049 含屋脊移动与后续坡载修改，按几何更新为主；INT-054 含荷载表与中柱截面连续更新，按属性更新为主。

## MM：多模态逆向建模

保留已有七个输入任务子类型及其边界，不把梁/桁架/框架名称改作能力子类，也不再同时计入 STD 技能组。图表联合强调图形与属性/荷载表之间的对应；在当前公开输入中合并为一份图纸仍属该类。多视图描述重建方式，不意味着每题都是三维空间模型。DXF 两类按原定工程输入用途区分，不能只凭附件数量或文件后缀重新划分。

| 能力子类 / English | 稳定键 | 题数 | 代表题 |
| --- | --- | ---: | --- |
| 力学简图 / Mechanics schematics | `mm_mechanics_schematic` | 12 | MM-002、MM-015、MM-095 |
| 工程标注图 / Annotated engineering drawings | `mm_annotated_engineering_drawing` | 28 | MM-004、MM-061、MM-099 |
| 图表联合 / Diagram and table fusion | `mm_diagram_table_fusion` | 17 | MM-014、MM-066、MM-089 |
| 多视图重建 / Multiview reconstruction | `mm_multiview_reconstruction` | 15 | MM-040、MM-079、MM-100 |
| 结构DXF / Structural DXF interpretation | `mm_structural_dxf` | 15 | MM-008、MM-036、MM-084 |
| 建筑DXF / Architectural DXF interpretation | `mm_architectural_dxf` | 8 | MM-047、MM-075、MM-086 |
| 缺失/质量澄清 / Missing or low-quality visual input clarification | `mm_missing_quality_clarification` | 5 | MM-007、MM-058、MM-072 |

缺失/质量澄清的全部 5 题是 MM-007、MM-021、MM-032、MM-058、MM-072；分别涵盖模糊荷载、图表冲突、缺屋脊尺寸、裁掉柱脚以及遮蔽错层高差。补充信息按题定轮次释放，不提前把后轮补图当作首轮输入。

## 当前目录、Excel 与网页共用方式

[当前目录 JSON](../planning/releases/research300-catalogue.json) 和 [当前版 Excel](../planning/releases/StructureClaw_Benchmark_300题_当前版.xlsx) 由同一目录构建器读取本映射、冻结合同和当前公开输入生成。Excel 是新的当前发行物；[原规划工作簿](../planning/sources/StructureClaw_Bench_300题规划_求解器补充版_20261013.xlsx) 保持归档，不覆盖，也不把原表中的“规划/待编制”状态当作当前交付状态。

```sh
npm run catalogue:research300
npm run check:catalogue
cd viewer
npm run build
```

`catalogue:research300` 更新仓库中的当前目录和 Excel，`check:catalogue` 检查保存的发行物是否与当前输入和分类一致。网页构建使用同一份内存目录同步生成网页数据与仓库 `planning/releases/` 两份发行物，并通过 `/data/catalogue.json`、`/data/benchmark-catalogue.xlsx` 提供下载。网页和工作簿按能力子类统计时均使用 `case.category` 对应的子类，一题一票。新增或修订分类须先修改本映射的对应 ID 和理由，再同时重建两种发行物，不能只改单侧展示名称。

分类所依据的只读档案为 [任务表](../planning/sources/all-tasks-engines-v2.json)、[模型表](../planning/sources/all-models-engines-v2.json) 和 [原始能力需求记录](../planning/capability-coverage-300.json)。初始缺项、合法输入对照和实际编辑行为同时核对了 [公开输入](../corpora/research-300/public-inputs)。这些能力子类提供更清楚的浏览/统计口径，不回写归档来源，也不重写源题要求。

## 独立结构校验

以下只读 Python 校验不调用模型或求解器，可独立检查唯一 ID、完整覆盖、题目大类一致、非空子类及 MM 原有子类型计数：

```sh
python - <<'PYCODE'
import json
from collections import Counter
from pathlib import Path

tax = json.loads(Path('planning/research300-taxonomy.json').read_text())
source = json.loads(Path('planning/sources/all-tasks-engines-v2.json').read_text())
assert tax['schemaVersion'] == 1
cats = {row['key']: row for row in tax['categories']}
rows = tax['cases']
expected = {f'{p}-{i:03d}' for p in ('STD', 'INT', 'MM') for i in range(1, 101)}
assert len(cats) == len(tax['categories']) == 22
assert len(rows) == len({row['id'] for row in rows}) == 300
assert {row['id'] for row in rows} == expected
families = {row['id']: row['family'] for row in source}
counts = Counter(row['category'] for row in rows)
assert set(counts) == set(cats)
for row in rows:
    assert cats[row['category']]['family'] == families[row['id']]
    assert row['rationale'].strip()
for cat in cats.values():
    assert all(cat[field].strip() for field in ('key', 'family', 'zh', 'en', 'description'))
assert Counter(cats[row['category']]['family'] for row in rows) == Counter({
    'standard_workflow': 100, 'interactive_robustness': 100,
    'multimodal_reverse_engineering': 100})
mm = Counter(cats[row['category']]['zh'] for row in rows if row['id'].startswith('MM-'))
assert mm == Counter({'力学简图': 12, '工程标注图': 28, '图表联合': 17,
    '多视图重建': 15, '结构DXF': 15, '建筑DXF': 8, '缺失/质量澄清': 5})
print('300 unique cases; 22 populated categories; all family and MM counts valid')
PYCODE
```
