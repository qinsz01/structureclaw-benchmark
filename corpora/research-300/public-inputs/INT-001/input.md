## Input tables

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。
截面shape内B和H尺寸单位为mm，其余截面properties按上述明确单位。使用OpenSees，输出带符号数值并注明节点/位置、全局方向、单位、工况及当前轮次。Rz表示全局+Z支反力；固端My指按右手定则绕全局+Y的支座反力矩。物理模型修改后必须重新运行；保存输入、模型快照、软件版本/设置、成功日志及结果位置映射。纯查询仅可复用可追溯至同一未变状态的有效结果；必要信息未解决时不得编造数值。不得额外引入释放、支承、质量、刚域、自动组合或附加载荷。内部连通节点不增加平移支承。后续只执行明确修改。
跨度6 m，梁沿全局X轴，x=0铰支、x=6 m竖向滚支。工况D含全跨向下20 kN/m及x=1.5 m向下12 kN点力。x=3 m是连通观测节点。

## Input tables

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|

## Input tables — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input tables — Nodes

|id|x|restraints|
|---|---|---|
|n0|0|[true, true, true, true, false, true]|
|n1|1.5|[false, true, false, true, false, true]|
|n2|3|[false, true, false, true, false, true]|
|n3|6|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input tables — Elements

|id|nodes|
|---|---|
|b1|["n0", "n1"]|
|b2|["n1", "n2"]|
|b3|["n2", "n3"]|

Applies to every listed row: type = beam; material = M1; section = B1.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input tables — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|B1|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|

Applies to every listed row: name = id; shape · kind = type.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|type|start|end|wz|fz|
|---|---|---|---|---|---|
|uniform-b1 → b1|distributed|0|1.5|-20|—|
|uniform-b2 → b2|distributed|0.0|1.5|-20|—|
|uniform-b3 → b3|distributed|0|3|-20|—|
|near-support-point → n1|nodal|—|—|—|-12|

Applies to every listed row: reference_frame = global.

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input tables — Metadata — Element reference vectors

|Field|Value|
|---|---|
|b1|[0, 0, 1.5]|
|b2|[0, 0, 1.5]|
|b3|[0, 0, 3]|
