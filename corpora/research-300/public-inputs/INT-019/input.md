## Input t1

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。
编题补齐的实体属性附表：M1弹性模量E=206000 MPa、nu=0.3、rho=7850 kg/m3，G逐项明列。截面以列出的实体属性为准。各杆截面转角均为0，无杆端释放。观测节点接入连续梁，不新增支承或质量。上述值补齐源规划未给定的附表。工况D、L1、L2独立保存。组合为原始工况响应的线性组合；修改组合系数不能覆盖原始载荷强度。

## Input t1

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|metadata|{}|

## Input t1 — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input t1 — Nodes

|id|x|restraints|
|---|---|---|
|n0|0|[true, true, true, true, false, true]|
|n1|4|[false, true, true, true, false, true]|
|n2|7|[false, true, false, true, false, true]|
|n3|10|[false, true, true, true, false, true]|
|n4|14|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input t1 — Elements

|id|nodes|
|---|---|
|b1|["n0", "n1"]|
|b2|["n1", "n2"]|
|b3|["n2", "n3"]|
|b4|["n3", "n4"]|

Applies to every listed row: type = beam; material = M1; section = B1.

## Input t1 — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input t1 — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|B1|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|

Applies to every listed row: name = id; shape · kind = type.

## Input t1 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load cases — D — Loads

|Load ID → element / node|type|wz|fz|
|---|---|---|---|
|D-udl-b1 → b1, D-udl-b2 → b2, D-udl-b3 → b3, D-udl-b4 → b4|distributed|-8|—|
|D-middle-point → n2|nodal|—|-20|

Applies to every listed row: reference_frame = global.

## Input t1 — Load cases — L1

|Field|Value|
|---|---|
|id|L1|
|type|live|

## Input t1 — Load cases — L1 — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|L1-udl-b2 → b2, L1-udl-b3 → b3|global|distributed|-10|

## Input t1 — Load cases — L2

|Field|Value|
|---|---|
|id|L2|
|type|live|

## Input t1 — Load cases — L2 — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|L2-udl-b1 → b1, L2-udl-b4 → b4|global|distributed|-10|

## Input t1 — Load combinations

|id|factors · L1|factors · L2|
|---|---|---|
|C1|—|—|
|C2|1|—|
|C3|—|1|

Applies to every listed row: factors · D = 1.

## Input t1 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
