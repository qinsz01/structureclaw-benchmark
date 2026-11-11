## Input t1

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。
编题补齐附件：明确连接表与截面绝对属性补齐源规划的待编附表。所有单元为两端铰接、仅轴向受力的桁架杆；轴力N以受拉为正。不添加节点质量。E/G单位MPa，密度kg/m3，截面属性完整明列。转动自由度约束仅消除轴力单元未激活的记账自由度，不提供抗弯刚度。首根下弦输出杆为BC1，按L0→L1方向定义；截面A1为0.10×0.10 m实心方形。所有null X坐标均未提供，不表示0。

## Input t1

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|
|metadata|{}|
|panelLengthsM|[2, null, 4, 3]|
|coordinateStatus|第二节间长度未给出；U2/L2及其右侧节点的X坐标待补齐|

## Input t1 — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input t1 — Nodes

|id|x|z|restraints|
|---|---|---|---|
|L0|0|0|[true, true, true, true, true, true]|
|U0|0|2.2|[false, true, false, true, true, true]|
|L1|2|0|[false, true, false, true, true, true]|
|U1|2|2.2|[false, true, false, true, true, true]|
|L2|null|0|[false, true, false, true, true, true]|
|U2|null|2.2|[false, true, false, true, true, true]|
|L3|null|0|[false, true, false, true, true, true]|
|U3|null|2.2|[false, true, false, true, true, true]|
|L4|null|0|[false, true, true, true, true, true]|
|U4|null|2.2|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Input t1 — Elements

|id|nodes|
|---|---|
|BC1|["L0", "L1"]|
|TC1|["U0", "U1"]|
|BC2|["L1", "L2"]|
|TC2|["U1", "U2"]|
|BC3|["L2", "L3"]|
|TC3|["U2", "U3"]|
|BC4|["L3", "L4"]|
|TC4|["U3", "U4"]|
|V0|["L0", "U0"]|
|V1|["L1", "U1"]|
|V2|["L2", "U2"]|
|V3|["L3", "U3"]|
|V4|["L4", "U4"]|
|DG1|["L0", "U1"]|
|DG2|["L1", "U2"]|
|DG3|["U2", "L3"]|
|DG4|["U3", "L4"]|

Applies to every listed row: type = truss; material = M1; section = A1.

## Input t1 — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input t1 — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|A1|rectangular|100.0|100.0|0.010000000000000002|8.333333333333335e-06|8.333333333333335e-06|1.4083333333333338e-05|

Applies to every listed row: name = id; shape · kind = type.

## Input t1 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load cases — D — Loads

|Load ID → element / node|fz|fx|
|---|---|---|
|vertical-U1 → U1|-8|—|
|vertical-U2 → U2|-12|—|
|vertical-U3 → U3|-10|—|
|horizontal-U2 → U2|—|4|

Applies to every listed row: reference_frame = global; type = nodal.

## Input t1 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
