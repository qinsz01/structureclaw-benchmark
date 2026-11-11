## Input t1

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Timoshenko beam/column and axial-only truss analysis.|
|loadTransfer|楼面面载全局向下，仅按相邻Y半跨之和作为受荷宽度传给X梁；Y梁不承接该面载，不另以板面荷载重复施加，不设刚性楼板。|
|floorPressureUnit|kN/m2|
|floorPressure|[10, 10, 10]|
|outputDefinition|逐一报告全部明示工况及组合：最高层实际梁柱节点中先取X最大、再取Y最大的节点Ux、Uz、Uy；最底层先取X最小、再取Y最小的柱底全局支反力矩My及竖向反力Rz=Fz。采用带符号的m、kN.m、kN，标明节点、方向、工况或组合及当前轮次；外挑自由端不是梁柱节点。|
|executionEvidence|各变更状态保存题定引擎的实际输入或原生工程、软件版本、有效设置、成功日志以及原始结果到节点/构件/工况的映射；截屏或其他引擎结果不能替代执行证据。保留原始工况并单独执行明示组合。|
|verbalBayStatement|X向两跨、Y向一跨。此文字与节点坐标表不一致，尚未确认优先项。|
|documentType|Public engineering input tables|
|combinationTable|[]|

## Input t1 — Stories

|id|elevation|height|
|---|---|---|
|s1|0|3.3|
|s2|3.3|3.3|
|s3|6.6|3.3000000000000007|

Applies to every listed row: rigid_diaphragm = false.

## Input t1 — Units

|Field|Value|
|---|---|
|coordinates|m|
|member_length|m|
|E|MPa|
|G|MPa|
|rho|kg/m3|
|A|m2|
|Iy|m4|
|Iz|m4|
|J|m4|
|shape|mm|
|force|kN|
|moment|kN.m|
|line_load|kN/m of actual member length|
|rotation_angle|degree|
|displacement|m|

## Input t1 — Axis definitions

|Field|Value|
|---|---|
|globalAxes|Right-handed XYZ; Z upward.|
|planarAxes|XZ plane: local x = i to j, local y = global +Y, local z = x cross y.|
|spatialAxes|local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.|
|sectionRoll|y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.|
|reactionNaming|Rz in the task means vertical support force Fz, not nodal rotation rz.|

## Input t1 — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|n0-0-0|0|0|0|[true, true, true, true, true, true]|
|n0-1-0|0|5|0|[true, true, true, true, true, true]|
|n0-2-0|0|10|0|[true, true, true, true, true, true]|
|n1-0-0|6|0|0|[true, true, true, true, true, true]|
|n1-1-0|6|5|0|[true, true, true, true, true, true]|
|n1-2-0|6|10|0|[true, true, true, true, true, true]|
|n0-0-1|0|0|3.3|[false, false, false, false, false, false]|
|n0-1-1|0|5|3.3|[false, false, false, false, false, false]|
|n0-2-1|0|10|3.3|[false, false, false, false, false, false]|
|n1-0-1|6|0|3.3|[false, false, false, false, false, false]|
|n1-1-1|6|5|3.3|[false, false, false, false, false, false]|
|n1-2-1|6|10|3.3|[false, false, false, false, false, false]|
|n0-0-2|0|0|6.6|[false, false, false, false, false, false]|
|n0-1-2|0|5|6.6|[false, false, false, false, false, false]|
|n0-2-2|0|10|6.6|[false, false, false, false, false, false]|
|n1-0-2|6|0|6.6|[false, false, false, false, false, false]|
|n1-1-2|6|5|6.6|[false, false, false, false, false, false]|
|n1-2-2|6|10|6.6|[false, false, false, false, false, false]|
|n0-0-3|0|0|9.9|[false, false, false, false, false, false]|
|n0-1-3|0|5|9.9|[false, false, false, false, false, false]|
|n0-2-3|0|10|9.9|[false, false, false, false, false, false]|
|n1-0-3|6|0|9.9|[false, false, false, false, false, false]|
|n1-1-3|6|5|9.9|[false, false, false, false, false, false]|
|n1-2-3|6|10|9.9|[false, false, false, false, false, false]|
|tip-0|7.2|0|9.9|[false, false, false, false, false, false]|
|tip-2|7.2|10|9.9|[false, false, false, false, false, false]|

## Input t1 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-0-1|column|["n0-0-0", "n0-0-1"]|C1|
|x0-0-1|beam|["n0-0-1", "n1-0-1"]|B1|
|y0-0-1|beam|["n0-0-1", "n0-1-1"]|B1|
|c0-1-1|column|["n0-1-0", "n0-1-1"]|C1|
|x0-1-1|beam|["n0-1-1", "n1-1-1"]|B1|
|y0-1-1|beam|["n0-1-1", "n0-2-1"]|B1|
|c0-2-1|column|["n0-2-0", "n0-2-1"]|C1|
|x0-2-1|beam|["n0-2-1", "n1-2-1"]|B1|
|c1-0-1|column|["n1-0-0", "n1-0-1"]|C1|
|y1-0-1|beam|["n1-0-1", "n1-1-1"]|B1|
|c1-1-1|column|["n1-1-0", "n1-1-1"]|C1|
|y1-1-1|beam|["n1-1-1", "n1-2-1"]|B1|
|c1-2-1|column|["n1-2-0", "n1-2-1"]|C1|
|c0-0-2|column|["n0-0-1", "n0-0-2"]|C1|
|x0-0-2|beam|["n0-0-2", "n1-0-2"]|B1|
|y0-0-2|beam|["n0-0-2", "n0-1-2"]|B1|
|c0-1-2|column|["n0-1-1", "n0-1-2"]|C1|
|x0-1-2|beam|["n0-1-2", "n1-1-2"]|B1|
|y0-1-2|beam|["n0-1-2", "n0-2-2"]|B1|
|c0-2-2|column|["n0-2-1", "n0-2-2"]|C1|
|x0-2-2|beam|["n0-2-2", "n1-2-2"]|B1|
|c1-0-2|column|["n1-0-1", "n1-0-2"]|C1|
|y1-0-2|beam|["n1-0-2", "n1-1-2"]|B1|
|c1-1-2|column|["n1-1-1", "n1-1-2"]|C1|
|y1-1-2|beam|["n1-1-2", "n1-2-2"]|B1|
|c1-2-2|column|["n1-2-1", "n1-2-2"]|C1|
|c0-0-3|column|["n0-0-2", "n0-0-3"]|C1|
|x0-0-3|beam|["n0-0-3", "n1-0-3"]|B1|
|y0-0-3|beam|["n0-0-3", "n0-1-3"]|B1|
|c0-1-3|column|["n0-1-2", "n0-1-3"]|C1|
|x0-1-3|beam|["n0-1-3", "n1-1-3"]|B1|
|y0-1-3|beam|["n0-1-3", "n0-2-3"]|B1|
|c0-2-3|column|["n0-2-2", "n0-2-3"]|C1|
|x0-2-3|beam|["n0-2-3", "n1-2-3"]|B1|
|c1-0-3|column|["n1-0-2", "n1-0-3"]|C1|
|y1-0-3|beam|["n1-0-3", "n1-1-3"]|B1|
|c1-1-3|column|["n1-1-2", "n1-1-3"]|C1|
|y1-1-3|beam|["n1-1-3", "n1-2-3"]|B1|
|c1-2-3|column|["n1-2-2", "n1-2-3"]|C1|
|overhang-0|beam|["n1-0-3", "tip-0"]|B1|
|overhang-2|beam|["n1-2-3", "tip-2"]|B1|

Applies to every listed row: material = M1.

## Input t1 — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Elastic steel|steel|200000|76923.07692307692|0.3|7850|

## Input t1 — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load case table — D — Loads

|Load ID → element / node|type|wz|fz|
|---|---|---|---|
|D-x0-0-1 → x0-0-1, D-x0-2-1 → x0-2-1, D-x0-0-2 → x0-0-2, D-x0-2-2 → x0-2-2, D-x0-0-3 → x0-0-3, D-x0-2-3 → x0-2-3|distributed|-25.0|—|
|D-x0-1-1 → x0-1-1, D-x0-1-2 → x0-1-2, D-x0-1-3 → x0-1-3|distributed|-50.0|—|
|tip-force-0 → tip-0, tip-force-2 → tip-2|nodal|—|-5|

Applies to every listed row: reference_frame = global.

## Input t1 — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input t1 — Coordinate contract

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input t1 — Member axis data — Element reference vectors

|Field|Value|
|---|---|
|c0-0-1|[1, 0, 0]|
|x0-0-1|[0, 0, 1]|
|y0-0-1|[0, 0, 1]|
|c0-1-1|[1, 0, 0]|
|x0-1-1|[0, 0, 1]|
|y0-1-1|[0, 0, 1]|
|c0-2-1|[1, 0, 0]|
|x0-2-1|[0, 0, 1]|
|c1-0-1|[1, 0, 0]|
|y1-0-1|[0, 0, 1]|
|c1-1-1|[1, 0, 0]|
|y1-1-1|[0, 0, 1]|
|c1-2-1|[1, 0, 0]|
|c0-0-2|[1, 0, 0]|
|x0-0-2|[0, 0, 1]|
|y0-0-2|[0, 0, 1]|
|c0-1-2|[1, 0, 0]|
|x0-1-2|[0, 0, 1]|
|y0-1-2|[0, 0, 1]|
|c0-2-2|[1, 0, 0]|
|x0-2-2|[0, 0, 1]|
|c1-0-2|[1, 0, 0]|
|y1-0-2|[0, 0, 1]|
|c1-1-2|[1, 0, 0]|
|y1-1-2|[0, 0, 1]|
|c1-2-2|[1, 0, 0]|
|c0-0-3|[1, 0, 0]|
|x0-0-3|[0, 0, 1]|
|y0-0-3|[0, 0, 1]|
|c0-1-3|[1, 0, 0]|
|x0-1-3|[0, 0, 1]|
|y0-1-3|[0, 0, 1]|
|c0-2-3|[1, 0, 0]|
|x0-2-3|[0, 0, 1]|
|c1-0-3|[1, 0, 0]|
|y1-0-3|[0, 0, 1]|
|c1-1-3|[1, 0, 0]|
|y1-1-3|[0, 0, 1]|
|c1-2-3|[1, 0, 0]|
|overhang-0|[0, 0, 1]|
|overhang-2|[0, 0, 1]|

## Native analysis conventions

商业引擎弹性分析约定：commercial-linear-static-v2

采用指定原生引擎进行一阶、小位移、线弹性静力分析，梁柱采用 Timoshenko
弯曲。对每根梁、柱明确规定有效剪切面积 Asy = Asz = 5*A/6，单位 m^2；
A 为当前已公开属性附表中的截面面积，Asy 对应局部 y 方向剪力 V2，Asz
对应局部 z 方向剪力 V3。这是本基准规定的理想化，包括只给数值属性的
广义截面，并非按截面名称推测；后续新增或修改的截面同样采用此明确公式。
桁架或支撑杆仍按题目规定仅承受轴力。

保留题定 E、G、A、Iy、Iz、J、几何、连接、支座、荷载及工况/组合。
题定采用混凝土未开裂毛截面时保留该刚度；局部轴、杆端截面内力符号及
单位仍按原附表。自重、刚性楼板、刚域、P-Delta 和施工阶段保持关闭。

显式实现题定弹性刚度，不以原生材料牌号的默认值替代。采用等效 EA、
G*Asy、G*Asz、GJ、E*Iy、E*Iz 的原生表达时，须保留题定物理参数，
同时报告实际原生材料/截面参数、修正系数及数值序列化差异。弹性刚度
等效不代表原生材料字段逐字相同，也不代表已验证应力或设计计算。
保存原生输入、设置、引擎版本、日志和原始结果证据。本附表提供分析输入，
不提供计算答案或验收结论。
