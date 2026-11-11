## Input tables

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩单位仅按各项明确注明，右端数值20的力矩单位待确认；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。已明确荷载的未列分量为零；右端待澄清力矩不属于已完成输入，不可视为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。
截面shape中B和H尺寸单位为mm；共用节点连续刚接，只有明示支承约束平面自由度。使用OpenSees及明确给出的属性和设置。输出须有符号、位置、全局方向、单位、工况/组合及当前轮次。Rz是全局+Z支反力；固端My是按右手规则绕全局+Y的支座反力矩。物理模型修改后必须计算当前状态，保存输入、快照及字段差异、软件版本/设置、成功日志和结果映射。不得猜测必要缺项，不得把历史结果当作更新结果。
连续梁沿全局X轴，两跨各5 m；x=0铰支，x=5、10 m竖向滚支。工况D仅右跨x=5～10 m向下6 kN/m，左跨没有均布载。右端x=10 m另有绕全局+Y的正向节点力矩，数值写作20，但力矩单位未提供；按右手规则约定方向。任何其他已知量的单位都不适用于这个待澄清数值。x=7.5 m是连通观测节点。

## Input tables

|Field|Value|
|---|---|
|schema_version|2.2.0|
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
|n1|5|[false, true, true, true, false, true]|
|n2|7.5|[false, true, false, true, false, true]|
|n3|10|[false, true, true, true, false, true]|

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

|Load ID → element / node|
|---|
|right-span-b2 → b2|
|right-span-b3 → b3|

Applies to every listed row: reference_frame = global; type = distributed; start = 0; end = 2.5; wz = -6.

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
|b1|[0, 0, 5]|
|b2|[0, 0, 2.5]|
|b3|[0, 0, 2.5]|
