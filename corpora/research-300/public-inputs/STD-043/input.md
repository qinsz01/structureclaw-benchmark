## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|z|restraints|
|---|---|---|---|
|A|0|0|[true, true, true, true, true, true]|
|B|18|0|[true, true, true, true, true, true]|
|L|0|7|[false, true, false, true, false, true]|
|M|9|7|[false, true, false, true, false, true]|
|R|18|7|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Geometry — Elements

|id|type|nodes|section|
|---|---|---|---|
|CL|column|["A", "L"]|COLUMN|
|CR|column|["B", "R"]|COLUMN|
|RL|beam|["L", "M"]|ROOF|
|RR|beam|["M", "R"]|ROOF|

Applies to every listed row: material = M1.

## Properties

|Field|Value|
|---|---|
|load_combinations|[]|
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

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|ROOF|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|COLUMN|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Properties — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Properties — Local axes

|Field|Value|
|---|---|
|localAxes|Local 1 points from the first listed node to the second; local 2 is global +Y; local 3 = local 1 cross local 2.|
|kinematics|Euler-Bernoulli, axial and flexural deformation included; shear deformation excluded; no end releases.|
|inactiveDofs|["uy", "rx", "rz"]|

## Loads

|Field|Value|
|---|---|
|load_combinations|[]|
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

|Load ID → element / node|reference_frame|type|wz|start|end|
|---|---|---|---|---|---|
|D-1 → RL, D-2 → RR|global|distributed|-6|0.0|9.0|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · id|component|unit|
|---|---|---|---|
|case:D:node:L:ux|L|ux|m|
|case:D:node:L:uz|L|uz|m|
|case:D:node:R:ux|R|ux|m|
|case:D:node:R:uz|R|uz|m|
|case:D:node:M:uz|M|uz|m|
|case:D:node:A:Fx|A|Fx|kN|
|case:D:node:A:Fz|A|Fz|kN|
|case:D:node:A:My|A|My|kN.m|
|case:D:node:B:Fx|B|Fx|kN|
|case:D:node:B:Fz|B|Fz|kN|
|case:D:node:B:My|B|My|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Analysis and reporting conventions

完整输入见附件。全局XYZ为右手系，Z向上；平面结构位于XZ面。表列节点均为实际连通节点。构件局部x由i端指向j端；二维局部y为全局+Y，局部z=x×y；三维局部y=归一化(reference×x)，局部z=x×y，参考向量逐杆给出。N拉为正；截面N/T/M2/M3在i端取节点抵抗力的负值，在j端取正值；V2/V3在i端取正值、j端取负值。节点位移和支反力按全局分量，转角服从右手定则。线载按构件实际长度计，斜杆亦然。一阶线弹性，自重、刚性楼板、刚域、二阶和施工阶段关闭；仅使用题定工况及组合。逐项完成input.md中所有请求，保留位置、截面侧别、正负号、分量、单位、工况/组合。跨内内力恢复须计入荷载项。实际运行OpenSees，保留版本、可运行输入、实际求解日志及原始结果/工况对应关系。正文和结构化结果均须给出题定结果，并独立检查平衡。附件不提供数值答案或原生执行证据。
