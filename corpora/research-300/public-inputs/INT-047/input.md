## Input

输入表。截面shape的B、H尺寸为mm，截面properties数值为输入依据。全局X水平、Z向上，Y补成右手系。坐标m；节点力kN；节点力矩kN*m；线载kN/m；E、G为MPa；A为m2；Iy、Iz、J为m4；密度kg/m3。约束顺序ux,uy,uz,rx,ry,rz；true表示固定。构件局部x沿起点到终点。平面XZ构件局部y为全局+Y，局部z=x叉乘y，绕局部y弯曲采用Iy。空间杆局部z取明示参考向量在垂直局部x平面的投影，局部y=z叉乘x。一阶线弹性静力，自重关闭；不自动添加荷载、组合、楼板、刚域或二阶效应。分布载荷区间按实际杆长以m计，除非本轮明确待确认该基准。未列荷载分量为零。梁柱共节点刚接；桁架仅轴向受力，转动约束只消除未激活自由度。每个可计算状态使用OpenSees；物理修改后重新计算，纯查询仅在状态未变时复用可追溯结果。保存软件版本/设置、成功日志、模型快照和原始结果映射。

## Input

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|
|metadata|{}|

## Input — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input — Nodes

|id|x|z|restraints|
|---|---|---|---|
|A|0|0|[true, true, true, true, true, true]|
|B|18|0|[true, true, true, true, true, true]|
|ML|0|3|[false, true, false, true, false, true]|
|TL|6|3|[false, true, false, true, false, true]|
|SR|18|5|[false, true, false, true, false, true]|
|TR|20|5|[false, true, false, true, false, true]|
|L|0|7|[false, true, false, true, false, true]|
|R|18|7|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input — Elements

|id|type|nodes|section|
|---|---|---|---|
|cLa|column|["A", "ML"]|C1|
|cLb|column|["ML", "L"]|C1|
|cRa|column|["B", "SR"]|C1|
|cRb|column|["SR", "R"]|C1|
|roof|beam|["L", "R"]|B1|
|mezz|beam|["ML", "TL"]|B1|
|stub|beam|["SR", "TR"]|B1|

Applies to every listed row: material = M1.

## Input — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load cases — D — Loads

|Load ID → element / node|wz|
|---|---|
|q-roof → roof|-6|
|q-mezz → mezz|-4|
|q-stub → stub|-3|

Applies to every listed row: reference_frame = global; type = distributed.

## Input — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
