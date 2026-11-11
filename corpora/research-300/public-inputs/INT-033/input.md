## Input tables

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。
明确为12节点21杆的平行弦；BC0为B0至B1。仅B1和B3各向下10kN。

## Input tables

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|
|metadata|{}|

## Input tables — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input tables — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|T0|0|2.5|[false, true, false, true, true, true]|
|B1|3|0|[false, true, false, true, true, true]|
|T1|3|2.5|[false, true, false, true, true, true]|
|B2|6|0|[false, true, false, true, true, true]|
|T2|6|2.5|[false, true, false, true, true, true]|
|B3|9|0|[false, true, false, true, true, true]|
|T3|9|2.5|[false, true, false, true, true, true]|
|B4|12|0|[false, true, false, true, true, true]|
|T4|12|2.5|[false, true, false, true, true, true]|
|B5|15|0|[false, true, true, true, true, true]|
|T5|15|2.5|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Input tables — Elements

|id|nodes|
|---|---|
|BC0|["B0", "B1"]|
|TC0|["T0", "T1"]|
|BC1|["B1", "B2"]|
|TC1|["T1", "T2"]|
|BC2|["B2", "B3"]|
|TC2|["T2", "T3"]|
|BC3|["B3", "B4"]|
|TC3|["T3", "T4"]|
|BC4|["B4", "B5"]|
|TC4|["T4", "T5"]|
|V0|["B0", "T0"]|
|V1|["B1", "T1"]|
|V2|["B2", "T2"]|
|V3|["B3", "T3"]|
|V4|["B4", "T4"]|
|V5|["B5", "T5"]|
|DG0|["B1", "T0"]|
|DG1|["B2", "T1"]|
|DG2|["B3", "T2"]|
|DG3|["B4", "T3"]|
|DG4|["B5", "T4"]|

Applies to every listed row: type = truss; material = M1; section = A.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|steel|steel|205000|78846.15384615384|0.3|7850|

## Input tables — Sections

|id|type|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|
|A|rod|0.01|1e-05|1e-05|2e-05|

Applies to every listed row: name = id.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fy|fz|mx|my|mz|
|---|---|---|---|---|---|---|---|---|
|odd-1 → B1, odd-3 → B3|global|nodal|0|0|-10|0|0|0|

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
