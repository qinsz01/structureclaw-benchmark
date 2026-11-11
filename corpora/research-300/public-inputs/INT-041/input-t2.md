## Input t2

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。

## Input t2

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|

## Input t2 — Coordinate system

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input t2 — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|A|0|0|0|[true, true, true, true, true, true]|
|B|6|0|0|[true, true, true, true, true, true]|
|C|6|6|0|[true, true, true, true, true, true]|
|D|0|6|0|[true, true, true, true, true, true]|
|P|2|3|3|[false, false, false, true, true, true]|

## Input t2 — Elements

|id|nodes|section|
|---|---|---|
|AB|["A", "B"]|A1|
|BC|["B", "C"]|A1|
|CD|["C", "D"]|A1|
|DA|["D", "A"]|A1|
|AP|["A", "P"]|A1|
|BP|["B", "P"]|A1|
|CP|["C", "P"]|A2|
|DP|["D", "P"]|A1|

Applies to every listed row: type = truss; material = M1.

## Input t2 — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input t2 — Sections

|id|properties · A|
|---|---|
|A1|0.01|
|A2|0.02|

Applies to every listed row: type = general; properties · Iy = 1e-05; properties · Iz = 1e-05; properties · J = 2e-05; name = id.

## Input t2 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t2 — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fz|
|---|---|---|---|---|
|apex → P|global|nodal|20|-30|

## Input t2 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input t2 — Metadata — Element reference vectors

|Field|Value|
|---|---|
|AB|[0, 0, 1]|
|BC|[0, 0, 1]|
|CD|[0, 0, 1]|
|DA|[0, 0, 1]|
|AP|[0, 0, 1]|
|BP|[0, 0, 1]|
|CP|[0, 0, 1]|
|DP|[0, 0, 1]|
