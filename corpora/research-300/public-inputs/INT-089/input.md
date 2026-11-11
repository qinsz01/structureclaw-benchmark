## Input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Timoshenko beam/column and axial-only truss analysis.|
|appendixDecision|C1=corner, C2=edge excluding corners, C3=interior, C4=replacement section; all are explicit elastic sections.|
|documentType|Public engineering input tables|
|combinationTable|[]|

## Input — Stories

|id|elevation|
|---|---|
|s1|0|
|s2|3.6|

Applies to every listed row: height = 3.6; rigid_diaphragm = false.

## Input — Units

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

## Input — Axis definitions

|Field|Value|
|---|---|
|globalAxes|Right-handed XYZ; Z upward.|
|planarAxes|XZ plane: local x = i to j, local y = global +Y, local z = x cross y.|
|spatialAxes|local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.|
|sectionRoll|y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.|
|reactionNaming|Rz in the task means vertical support force Fz, not nodal rotation rz.|

## Input — Column groups

|Field|Value|
|---|---|
|corner|["c0-0-1", "c0-2-1", "c2-0-1", "c2-2-1", "c0-0-2", "c0-2-2", "c2-0-2", "c2-2-2"]|
|edge_non_corner|["c0-1-1", "c1-0-1", "c1-2-1", "c2-1-1", "c0-1-2", "c1-0-2", "c1-2-2", "c2-1-2"]|
|interior|["c1-1-1", "c1-1-2"]|

## Input — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|n0-0-0|0|0|0|[true, true, true, false, false, false]|
|n0-1-0|0|5|0|[true, true, true, true, true, true]|
|n0-2-0|0|10|0|[true, true, true, true, true, true]|
|n1-0-0|6|0|0|[true, true, true, true, true, true]|
|n1-1-0|6|5|0|[true, true, true, true, true, true]|
|n1-2-0|6|10|0|[true, true, true, true, true, true]|
|n2-0-0|12|0|0|[true, true, true, true, true, true]|
|n2-1-0|12|5|0|[true, true, true, true, true, true]|
|n2-2-0|12|10|0|[true, true, true, false, false, false]|
|n0-0-1|0|0|3.6|[false, false, false, false, false, false]|
|n0-1-1|0|5|3.6|[false, false, false, false, false, false]|
|n0-2-1|0|10|3.6|[false, false, false, false, false, false]|
|n1-0-1|6|0|3.6|[false, false, false, false, false, false]|
|n1-1-1|6|5|3.6|[false, false, false, false, false, false]|
|n1-2-1|6|10|3.6|[false, false, false, false, false, false]|
|n2-0-1|12|0|3.6|[false, false, false, false, false, false]|
|n2-1-1|12|5|3.6|[false, false, false, false, false, false]|
|n2-2-1|12|10|3.6|[false, false, false, false, false, false]|
|n0-0-2|0|0|7.2|[false, false, false, false, false, false]|
|n0-1-2|0|5|7.2|[false, false, false, false, false, false]|
|n0-2-2|0|10|7.2|[false, false, false, false, false, false]|
|n1-0-2|6|0|7.2|[false, false, false, false, false, false]|
|n1-1-2|6|5|7.2|[false, false, false, false, false, false]|
|n1-2-2|6|10|7.2|[false, false, false, false, false, false]|
|n2-0-2|12|0|7.2|[false, false, false, false, false, false]|
|n2-1-2|12|5|7.2|[false, false, false, false, false, false]|
|n2-2-2|12|10|7.2|[false, false, false, false, false, false]|

## Input — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-0-1|column|["n0-0-0", "n0-0-1"]|C1|
|x0-0-1|beam|["n0-0-1", "n1-0-1"]|BX|
|y0-0-1|beam|["n0-0-1", "n0-1-1"]|BY|
|c0-1-1|column|["n0-1-0", "n0-1-1"]|C2|
|x0-1-1|beam|["n0-1-1", "n1-1-1"]|BX|
|y0-1-1|beam|["n0-1-1", "n0-2-1"]|BY|
|c0-2-1|column|["n0-2-0", "n0-2-1"]|C1|
|x0-2-1|beam|["n0-2-1", "n1-2-1"]|BX|
|c1-0-1|column|["n1-0-0", "n1-0-1"]|C2|
|x1-0-1|beam|["n1-0-1", "n2-0-1"]|BX|
|y1-0-1|beam|["n1-0-1", "n1-1-1"]|BY|
|c1-1-1|column|["n1-1-0", "n1-1-1"]|C3|
|x1-1-1|beam|["n1-1-1", "n2-1-1"]|BX|
|y1-1-1|beam|["n1-1-1", "n1-2-1"]|BY|
|c1-2-1|column|["n1-2-0", "n1-2-1"]|C2|
|x1-2-1|beam|["n1-2-1", "n2-2-1"]|BX|
|c2-0-1|column|["n2-0-0", "n2-0-1"]|C1|
|y2-0-1|beam|["n2-0-1", "n2-1-1"]|BY|
|c2-1-1|column|["n2-1-0", "n2-1-1"]|C2|
|y2-1-1|beam|["n2-1-1", "n2-2-1"]|BY|
|c2-2-1|column|["n2-2-0", "n2-2-1"]|C1|
|c0-0-2|column|["n0-0-1", "n0-0-2"]|C1|
|x0-0-2|beam|["n0-0-2", "n1-0-2"]|BX|
|y0-0-2|beam|["n0-0-2", "n0-1-2"]|BY|
|c0-1-2|column|["n0-1-1", "n0-1-2"]|C2|
|x0-1-2|beam|["n0-1-2", "n1-1-2"]|BX|
|y0-1-2|beam|["n0-1-2", "n0-2-2"]|BY|
|c0-2-2|column|["n0-2-1", "n0-2-2"]|C1|
|x0-2-2|beam|["n0-2-2", "n1-2-2"]|BX|
|c1-0-2|column|["n1-0-1", "n1-0-2"]|C2|
|x1-0-2|beam|["n1-0-2", "n2-0-2"]|BX|
|y1-0-2|beam|["n1-0-2", "n1-1-2"]|BY|
|c1-1-2|column|["n1-1-1", "n1-1-2"]|C3|
|x1-1-2|beam|["n1-1-2", "n2-1-2"]|BX|
|y1-1-2|beam|["n1-1-2", "n1-2-2"]|BY|
|c1-2-2|column|["n1-2-1", "n1-2-2"]|C2|
|x1-2-2|beam|["n1-2-2", "n2-2-2"]|BX|
|c2-0-2|column|["n2-0-1", "n2-0-2"]|C1|
|y2-0-2|beam|["n2-0-2", "n2-1-2"]|BY|
|c2-1-2|column|["n2-1-1", "n2-1-2"]|C2|
|y2-1-2|beam|["n2-1-2", "n2-2-2"]|BY|
|c2-2-2|column|["n2-2-1", "n2-2-2"]|C1|

Applies to every listed row: material = M1.

## Input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Input — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|BX|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|BY|300.0|500.0|0.15|0.0031249999999999997|0.001125|0.0028173707999999994|
|C1|450.0|450.0|0.2025|0.0034171875000000005|0.0034171875000000005|0.005775046875000001|
|C2|400.0|500.0|0.2|0.004166666666666667|0.0026666666666666674|0.005474167466666667|
|C3|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|C4|450.0|600.0|0.27|0.0081|0.00455625|0.009840743591308595|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load case table — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-x0-0-1 → x0-0-1, D-y0-0-1 → y0-0-1, D-x0-1-1 → x0-1-1, D-y0-1-1 → y0-1-1, D-x0-2-1 → x0-2-1, D-x1-0-1 → x1-0-1, D-y1-0-1 → y1-0-1, D-x1-1-1 → x1-1-1, D-y1-1-1 → y1-1-1, D-x1-2-1 → x1-2-1, D-y2-0-1 → y2-0-1, D-y2-1-1 → y2-1-1, D-x0-0-2 → x0-0-2, D-y0-0-2 → y0-0-2, D-x0-1-2 → x0-1-2, D-y0-1-2 → y0-1-2, D-x0-2-2 → x0-2-2, D-x1-0-2 → x1-0-2, D-y1-0-2 → y1-0-2, D-x1-1-2 → x1-1-2, D-y1-1-2 → y1-1-2, D-x1-2-2 → x1-2-2, D-y2-0-2 → y2-0-2, D-y2-1-2 → y2-1-2|global|distributed|-8|

## Input — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input — Coordinate contract

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input — Member axis data — Element reference vectors

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
|x1-0-1|[0, 0, 1]|
|y1-0-1|[0, 0, 1]|
|c1-1-1|[1, 0, 0]|
|x1-1-1|[0, 0, 1]|
|y1-1-1|[0, 0, 1]|
|c1-2-1|[1, 0, 0]|
|x1-2-1|[0, 0, 1]|
|c2-0-1|[1, 0, 0]|
|y2-0-1|[0, 0, 1]|
|c2-1-1|[1, 0, 0]|
|y2-1-1|[0, 0, 1]|
|c2-2-1|[1, 0, 0]|
|c0-0-2|[1, 0, 0]|
|x0-0-2|[0, 0, 1]|
|y0-0-2|[0, 0, 1]|
|c0-1-2|[1, 0, 0]|
|x0-1-2|[0, 0, 1]|
|y0-1-2|[0, 0, 1]|
|c0-2-2|[1, 0, 0]|
|x0-2-2|[0, 0, 1]|
|c1-0-2|[1, 0, 0]|
|x1-0-2|[0, 0, 1]|
|y1-0-2|[0, 0, 1]|
|c1-1-2|[1, 0, 0]|
|x1-1-2|[0, 0, 1]|
|y1-1-2|[0, 0, 1]|
|c1-2-2|[1, 0, 0]|
|x1-2-2|[0, 0, 1]|
|c2-0-2|[1, 0, 0]|
|y2-0-2|[0, 0, 1]|
|c2-1-2|[1, 0, 0]|
|y2-1-2|[0, 0, 1]|
|c2-2-2|[1, 0, 0]|

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
