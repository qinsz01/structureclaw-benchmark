## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|restraints|
|---|---|---|
|N0|0|[true, true, true, true, false, true]|
|N1|2|[false, true, false, true, false, true]|
|N2|4|[false, true, true, true, false, true]|
|N3|7|[false, true, false, true, false, true]|
|N4|10|[false, true, true, true, false, true]|
|N5|12|[false, true, false, true, false, true]|
|N6|14|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|E01|["N0", "N1"]|
|E02|["N1", "N2"]|
|E03|["N2", "N3"]|
|E04|["N3", "N4"]|
|E05|["N4", "N5"]|
|E06|["N5", "N6"]|

Applies to every listed row: type = beam; material = M1; section = B1.

## Properties

|Field|Value|
|---|---|
|localAxes|{}|
|analysis|first-order linear elastic Euler-Bernoulli frame and axial-only truss|
|restraintConvention|[ux,uy,uz,rx,ry,rz]; true = zero prescribed displacement; false = free active DOF; planar inactive DOFs and truss rotations are explicitly suppressed|
|sectionRollConvention|ey_new=cos(theta)*ey+sin(theta)*ez; ez_new=-sin(theta)*ey+cos(theta)*ez; theta in degrees about i-to-j|

## Properties — Units

|Field|Value|
|---|---|
|E|MPa|
|G|MPa|
|rho|kg/m3|
|shape|mm|
|A|m2|
|Iy|m4|
|Iz|m4|
|J|m4|

## Properties — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Properties — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Properties — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|B1|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|

Applies to every listed row: name = id; shape · kind = type.

## Properties — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Properties — Load combinations

|id|factors · L1|factors · L2|
|---|---|---|
|C0|—|—|
|C1|1|—|
|C2|—|1|

Applies to every listed row: factors · D = 1.

## Loads

|Field|Value|
|---|---|
|distributedLoadMeasure|per actual member length, global vector; start/end in metres from i unless units above specify mm|

## Loads — Units

|Field|Value|
|---|---|
|force|kN|
|moment|kN.m|
|lineLoad|kN/m|
|position|m|

## Loads — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Loads — Load cases — D — Loads

|Load ID → element / node|end|
|---|---|
|D-1 → E01, D-2 → E02, D-5 → E05, D-6 → E06|2.0|
|D-3 → E03, D-4 → E04|3.0|

Applies to every listed row: reference_frame = global; type = distributed; start = 0; wz = -8.

## Loads — Load cases — L2

|Field|Value|
|---|---|
|id|L2|
|type|live|

## Loads — Load cases — L2 — Loads

|Load ID → element / node|reference_frame|type|start|end|wz|
|---|---|---|---|---|---|
|L2-1 → E01, L2-2 → E02, L2-3 → E05, L2-4 → E06|global|distributed|0|2.0|-10|

## Loads — Load cases — L1

|Field|Value|
|---|---|
|id|L1|
|type|live|

## Loads — Load cases — L1 — Loads

|Load ID → element / node|reference_frame|type|start|end|wz|
|---|---|---|---|---|---|
|L1-1 → E03, L1-2 → E04|global|distributed|0|3.0|-10|

## Loads — Load combinations

|id|factors · L1|factors · L2|
|---|---|---|
|C0|—|—|
|C1|1|—|
|C2|—|1|

Applies to every listed row: factors · D = 1.

## Requested outputs — Quantities

|id|selection · id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|---|
|combination:C0:node:N0:Fx|C0|node|N0|Fx|kN|—|—|
|combination:C0:node:N0:Fz|C0|node|N0|Fz|kN|—|—|
|combination:C0:node:N2:Fx|C0|node|N2|Fx|kN|—|—|
|combination:C0:node:N2:Fz|C0|node|N2|Fz|kN|—|—|
|combination:C0:node:N4:Fx|C0|node|N4|Fx|kN|—|—|
|combination:C0:node:N4:Fz|C0|node|N4|Fz|kN|—|—|
|combination:C0:node:N6:Fx|C0|node|N6|Fx|kN|—|—|
|combination:C0:node:N6:Fz|C0|node|N6|Fz|kN|—|—|
|combination:C0:node:N1:uz|C0|node|N1|uz|m|—|—|
|combination:C0:node:N3:uz|C0|node|N3|uz|m|—|—|
|combination:C0:node:N5:uz|C0|node|N5|uz|m|—|—|
|combination:C0:member:E02:M2@2:left|C0|member|E02|M2|kN.m|2.0|left|
|combination:C0:member:E03:M2@0:right|C0|member|E03|M2|kN.m|0|right|
|combination:C0:member:E04:M2@3:left|C0|member|E04|M2|kN.m|3.0|left|
|combination:C0:member:E05:M2@0:right|C0|member|E05|M2|kN.m|0|right|
|combination:C1:node:N0:Fx|C1|node|N0|Fx|kN|—|—|
|combination:C1:node:N0:Fz|C1|node|N0|Fz|kN|—|—|
|combination:C1:node:N2:Fx|C1|node|N2|Fx|kN|—|—|
|combination:C1:node:N2:Fz|C1|node|N2|Fz|kN|—|—|
|combination:C1:node:N4:Fx|C1|node|N4|Fx|kN|—|—|
|combination:C1:node:N4:Fz|C1|node|N4|Fz|kN|—|—|
|combination:C1:node:N6:Fx|C1|node|N6|Fx|kN|—|—|
|combination:C1:node:N6:Fz|C1|node|N6|Fz|kN|—|—|
|combination:C1:node:N1:uz|C1|node|N1|uz|m|—|—|
|combination:C1:node:N3:uz|C1|node|N3|uz|m|—|—|
|combination:C1:node:N5:uz|C1|node|N5|uz|m|—|—|
|combination:C1:member:E02:M2@2:left|C1|member|E02|M2|kN.m|2.0|left|
|combination:C1:member:E03:M2@0:right|C1|member|E03|M2|kN.m|0|right|
|combination:C1:member:E04:M2@3:left|C1|member|E04|M2|kN.m|3.0|left|
|combination:C1:member:E05:M2@0:right|C1|member|E05|M2|kN.m|0|right|
|combination:C2:node:N0:Fx|C2|node|N0|Fx|kN|—|—|
|combination:C2:node:N0:Fz|C2|node|N0|Fz|kN|—|—|
|combination:C2:node:N2:Fx|C2|node|N2|Fx|kN|—|—|
|combination:C2:node:N2:Fz|C2|node|N2|Fz|kN|—|—|
|combination:C2:node:N4:Fx|C2|node|N4|Fx|kN|—|—|
|combination:C2:node:N4:Fz|C2|node|N4|Fz|kN|—|—|
|combination:C2:node:N6:Fx|C2|node|N6|Fx|kN|—|—|
|combination:C2:node:N6:Fz|C2|node|N6|Fz|kN|—|—|
|combination:C2:node:N1:uz|C2|node|N1|uz|m|—|—|
|combination:C2:node:N3:uz|C2|node|N3|uz|m|—|—|
|combination:C2:node:N5:uz|C2|node|N5|uz|m|—|—|
|combination:C2:member:E02:M2@2:left|C2|member|E02|M2|kN.m|2.0|left|
|combination:C2:member:E03:M2@0:right|C2|member|E03|M2|kN.m|0|right|
|combination:C2:member:E04:M2@3:left|C2|member|E04|M2|kN.m|3.0|left|
|combination:C2:member:E05:M2@0:right|C2|member|E05|M2|kN.m|0|right|

Applies to every listed row: selection · kind = combination.

## Requested outputs — Derived

|id|operands|unit|description|
|---|---|---|---|
|governing:node:N0:Fx|["combination:C0:node:N0:Fx", "combination:C1:node:N0:Fx", "combination:C2:node:N0:Fx"]|kN|node:N0:Fx 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N0:Fz|["combination:C0:node:N0:Fz", "combination:C1:node:N0:Fz", "combination:C2:node:N0:Fz"]|kN|node:N0:Fz 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N2:Fx|["combination:C0:node:N2:Fx", "combination:C1:node:N2:Fx", "combination:C2:node:N2:Fx"]|kN|node:N2:Fx 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N2:Fz|["combination:C0:node:N2:Fz", "combination:C1:node:N2:Fz", "combination:C2:node:N2:Fz"]|kN|node:N2:Fz 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N4:Fx|["combination:C0:node:N4:Fx", "combination:C1:node:N4:Fx", "combination:C2:node:N4:Fx"]|kN|node:N4:Fx 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N4:Fz|["combination:C0:node:N4:Fz", "combination:C1:node:N4:Fz", "combination:C2:node:N4:Fz"]|kN|node:N4:Fz 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N6:Fx|["combination:C0:node:N6:Fx", "combination:C1:node:N6:Fx", "combination:C2:node:N6:Fx"]|kN|node:N6:Fx 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N6:Fz|["combination:C0:node:N6:Fz", "combination:C1:node:N6:Fz", "combination:C2:node:N6:Fz"]|kN|node:N6:Fz 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N1:uz|["combination:C0:node:N1:uz", "combination:C1:node:N1:uz", "combination:C2:node:N1:uz"]|m|node:N1:uz 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N3:uz|["combination:C0:node:N3:uz", "combination:C1:node:N3:uz", "combination:C2:node:N3:uz"]|m|node:N3:uz 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:node:N5:uz|["combination:C0:node:N5:uz", "combination:C1:node:N5:uz", "combination:C2:node:N5:uz"]|m|node:N5:uz 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:member:E02:M2@2:left|["combination:C0:member:E02:M2@2:left", "combination:C1:member:E02:M2@2:left", "combination:C2:member:E02:M2@2:left"]|kN.m|member:E02:M2@2:left 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:member:E03:M2@0:right|["combination:C0:member:E03:M2@0:right", "combination:C1:member:E03:M2@0:right", "combination:C2:member:E03:M2@0:right"]|kN.m|member:E03:M2@0:right 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:member:E04:M2@3:left|["combination:C0:member:E04:M2@3:left", "combination:C1:member:E04:M2@3:left", "combination:C2:member:E04:M2@3:left"]|kN.m|member:E04:M2@3:left 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|
|governing:member:E05:M2@0:right|["combination:C0:member:E05:M2@0:right", "combination:C1:member:E05:M2@0:right", "combination:C2:member:E05:M2@0:right"]|kN.m|member:E05:M2@0:right 三个组合中绝对值最大的带符号值及控制组合；绝对值相等时按C0、C1、C2顺序取首个。|

Applies to every listed row: operation = max_abs.

## Analysis and reporting conventions

完整输入见附件。全局XYZ为右手系，Z向上；平面结构位于XZ面。表列节点均为实际连通节点。构件局部x由i端指向j端；二维局部y为全局+Y，局部z=x×y；三维局部y=归一化(reference×x)，局部z=x×y，参考向量逐杆给出。N拉为正；截面N/T/M2/M3在i端取节点抵抗力的负值，在j端取正值；V2/V3在i端取正值、j端取负值。节点位移和支反力按全局分量，转角服从右手定则。线载按构件实际长度计，斜杆亦然。一阶线弹性，自重、刚性楼板、刚域、二阶和施工阶段关闭；仅使用题定工况及组合。逐项完成input.md中所有请求，保留位置、截面侧别、正负号、分量、单位、工况/组合。跨内内力恢复须计入荷载项。实际运行OpenSees，保留版本、可运行输入、实际求解日志及原始结果/工况对应关系。正文和结构化结果均须给出题定结果，并独立检查平衡。附件不提供数值答案或原生执行证据。
