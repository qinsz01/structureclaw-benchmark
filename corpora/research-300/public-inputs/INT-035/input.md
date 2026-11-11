## Input tables

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。
x=6m处的竖杆几何线段为B2至T2，K腹杆几何线段为B1至P、T1至P，P=(6,0,1.5)m。P与竖杆是否共用结构节点尚未给定，故这些局部杆未在下面节点连接表中定案；竖杆若在P连接则分成上下两段，若不连接则保持整根。各相关杆均截面A、材料M1。9kN向下荷载位于P，其结构节点归属也待同一连接问题确认。其他K节点连接已明确。

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
|M1|3|1.5|[false, true, false, true, true, true]|
|M3|9|1.5|[false, true, false, true, true, true]|
|M4|12|1.5|[false, true, false, true, true, true]|
|M5|15|1.5|[false, true, false, true, true, true]|
|M6|18|1.5|[false, true, false, true, true, true]|

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
|BC5|["B5", "B6"]|
|TC5|["T5", "T6"]|
|V0|["B0", "T0"]|
|V1a|["B1", "M1"]|
|V1b|["M1", "T1"]|
|K1a|["B0", "M1"]|
|K1b|["T0", "M1"]|
|V3a|["B3", "M3"]|
|V3b|["M3", "T3"]|
|K3a|["B2", "M3"]|
|K3b|["T2", "M3"]|
|V4a|["B4", "M4"]|
|V4b|["M4", "T4"]|
|K4a|["B3", "M4"]|
|K4b|["T3", "M4"]|
|V5a|["B5", "M5"]|
|V5b|["M5", "T5"]|
|K5a|["B4", "M5"]|
|K5b|["T4", "M5"]|
|V6a|["B6", "M6"]|
|V6b|["M6", "T6"]|
|K6a|["B5", "M6"]|
|K6b|["T5", "M6"]|

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

|Load ID → element / node|fz|
|---|---|
|left-top-0 → T0, left-top-1 → T1, left-top-2 → T2, left-top-3 → T3|-8|
|midpoint-direct → P: geometric point (6,0,1.5); structural joint identity unresolved|-9|

Applies to every listed row: reference_frame = global; type = nodal; fx = 0; fy = 0; mx = 0; my = 0; mz = 0.

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
