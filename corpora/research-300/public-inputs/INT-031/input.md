## Input tables

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。
端节间腹杆分组明确为V0、V1、DG0、V5、V6、DG5，均为2A；其他腹杆与全部弦杆均A。

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
|T0|0|3|[false, true, false, true, true, true]|
|B1|3|0|[false, true, false, true, true, true]|
|T1|3|3|[false, true, false, true, true, true]|
|B2|6|0|[false, true, false, true, true, true]|
|T2|6|3|[false, true, false, true, true, true]|
|B3|9|0|[false, true, false, true, true, true]|
|T3|9|3|[false, true, false, true, true, true]|
|B4|12|0|[false, true, false, true, true, true]|
|T4|12|3|[false, true, false, true, true, true]|
|B5|15|0|[false, true, false, true, true, true]|
|T5|15|3|[false, true, false, true, true, true]|
|B6|18|0|[false, true, true, true, true, true]|
|T6|18|3|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Input tables — Elements

|id|nodes|section|
|---|---|---|
|BC0|["B0", "B1"]|A|
|TC0|["T0", "T1"]|A|
|BC1|["B1", "B2"]|A|
|TC1|["T1", "T2"]|A|
|BC2|["B2", "B3"]|A|
|TC2|["T2", "T3"]|A|
|BC3|["B3", "B4"]|A|
|TC3|["T3", "T4"]|A|
|BC4|["B4", "B5"]|A|
|TC4|["T4", "T5"]|A|
|BC5|["B5", "B6"]|A|
|TC5|["T5", "T6"]|A|
|V0|["B0", "T0"]|ENDWEB|
|V1|["B1", "T1"]|ENDWEB|
|V2|["B2", "T2"]|A|
|V3|["B3", "T3"]|A|
|V4|["B4", "T4"]|A|
|V5|["B5", "T5"]|ENDWEB|
|V6|["B6", "T6"]|ENDWEB|
|DG0|["B0", "T1"]|ENDWEB|
|DG1|["T1", "B2"]|A|
|DG2|["B2", "T3"]|A|
|DG3|["T3", "B4"]|A|
|DG4|["B4", "T5"]|A|
|DG5|["T5", "B6"]|ENDWEB|

Applies to every listed row: type = truss; material = M1.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|steel|steel|205000|78846.15384615384|0.3|7850|

## Input tables — Sections

|id|properties · A|
|---|---|
|A|0.01|
|ENDWEB|0.02|

Applies to every listed row: type = rod; properties · Iy = 1e-05; properties · Iz = 1e-05; properties · J = 2e-05; name = id.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fy|fz|mx|my|mz|
|---|---|---|---|---|---|---|---|---|
|point-1 → T1, point-2 → T2, point-3 → T3, point-4 → T4, point-5 → T5|global|nodal|0|0|-12|0|0|0|

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
