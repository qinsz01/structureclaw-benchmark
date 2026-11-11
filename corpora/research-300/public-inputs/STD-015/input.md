## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|restraints|
|---|---|---|
|N0|0|[true, true, true, true, false, true]|
|N1|2.5|[false, true, false, true, false, true]|
|N2|5|[false, true, true, true, false, true]|
|N3|8|[false, true, false, true, false, true]|
|N4|11|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|E01|["N0", "N1"]|
|E02|["N1", "N2"]|
|E03|["N2", "N3"]|
|E04|["N3", "N4"]|

Applies to every listed row: type = beam; material = M1; section = B1.

## Properties

|Field|Value|
|---|---|
|load_combinations|[]|
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

|Load ID → element / node|end|
|---|---|
|D-1 → E01, D-2 → E02|2.5|
|D-3 → E03, D-4 → E04|3.0|

Applies to every listed row: reference_frame = global; type = distributed; start = 0; wz = -12.

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case:D:node:N0:Fx|node|N0|Fx|kN|—|—|
|case:D:node:N0:Fz|node|N0|Fz|kN|—|—|
|case:D:node:N2:Fx|node|N2|Fx|kN|—|—|
|case:D:node:N2:Fz|node|N2|Fz|kN|—|—|
|case:D:node:N4:Fx|node|N4|Fx|kN|—|—|
|case:D:node:N4:Fz|node|N4|Fz|kN|—|—|
|case:D:node:N1:uz|node|N1|uz|m|—|—|
|case:D:node:N3:uz|node|N3|uz|m|—|—|
|case:D:member:E02:M2@2.5:left|member|E02|M2|kN.m|2.5|left|
|case:D:member:E03:M2@0:right|member|E03|M2|kN.m|0|right|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis and reporting conventions

完整输入见附件。全局XYZ为右手系，Z向上；平面结构位于XZ面。表列节点均为实际连通节点。构件局部x由i端指向j端；二维局部y为全局+Y，局部z=x×y；三维局部y=归一化(reference×x)，局部z=x×y，参考向量逐杆给出。N拉为正；截面N/T/M2/M3在i端取节点抵抗力的负值，在j端取正值；V2/V3在i端取正值、j端取负值。节点位移和支反力按全局分量，转角服从右手定则。线载按构件实际长度计，斜杆亦然。一阶线弹性，自重、刚性楼板、刚域、二阶和施工阶段关闭；仅使用题定工况及组合。逐项完成input.md中所有请求，保留位置、截面侧别、正负号、分量、单位、工况/组合。跨内内力恢复须计入荷载项。实际运行OpenSees，保留版本、可运行输入、实际求解日志及原始结果/工况对应关系。正文和结构化结果均须给出题定结果，并独立检查平衡。附件不提供数值答案或原生执行证据。
