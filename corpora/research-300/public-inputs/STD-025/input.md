## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|restraints|
|---|---|---|
|S0|0|[true, true, true, true, false, true]|
|P1|2.5|[false, true, false, true, false, true]|
|S1|5|[false, true, true, true, false, true]|
|P2|7.5|[false, true, false, true, false, true]|
|S2|10|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|B1a|["S0", "P1"]|
|B1b|["P1", "S1"]|
|B2a|["S1", "P2"]|
|B2b|["P2", "S2"]|

Applies to every listed row: type = beam; material = M1; section = B1.

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

## Properties — Local axes

|Field|Value|
|---|---|
|spanLengthsM|[5, 5]|
|spanSectionIds|["B1", "B1"]|
|beamTheory|Euler-Bernoulli|
|localAxes|Each beam runs along +global X; local 1=+X, local 2=+Y, local 3=+Z.|
|continuity|Every support and midpoint is one shared node; no member end releases.|

## Properties — Local axes — Observation nodes

|Field|Value|
|---|---|
|span-1-midpoint|P1|
|span-2-midpoint|P2|

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

|Load ID → element / node|type|wz|my|
|---|---|---|---|
|D-B1a → B1a, D-B1b → B1b, D-B2a → B2a, D-B2b → B2b|distributed|-6|—|
|D-end-moment → S2|nodal|—|20|

Applies to every listed row: reference_frame = global.

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case:D:node:S0:Fz|node|S0|Fz|kN|—|—|
|case:D:node:S1:Fz|node|S1|Fz|kN|—|—|
|case:D:node:S2:Fz|node|S2|Fz|kN|—|—|
|case:D:node:S0:Fx|node|S0|Fx|kN|—|—|
|case:D:node:S1:Fx|node|S1|Fx|kN|—|—|
|case:D:node:S2:Fx|node|S2|Fx|kN|—|—|
|case:D:node:P1:uz|node|P1|uz|m|—|—|
|case:D:node:P2:uz|node|P2|uz|m|—|—|
|case:D:member:B1b:M2@2.5:left|member|B1b|M2|kN.m|2.5|left|
|case:D:member:B2a:M2@0:right|member|B2a|M2|kN.m|0|right|
|case:D:node:S2:ry|node|S2|ry|rad|—|—|
|case:D:member:B1a:M2@0:right|member|B1a|M2|kN.m|0|right|
|case:D:member:B1a:M2@2.5:left|member|B1a|M2|kN.m|2.5|left|
|case:D:member:B2a:M2@2.5:left|member|B2a|M2|kN.m|2.5|left|
|case:D:member:B2b:M2@2.5:left|member|B2b|M2|kN.m|2.5|left|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis and reporting conventions

完整输入见附件。全局XYZ为右手系，Z向上；平面结构位于XZ面。表列节点均为实际连通节点。构件局部x由i端指向j端；二维局部y为全局+Y，局部z=x×y；三维局部y=归一化(reference×x)，局部z=x×y，参考向量逐杆给出。N拉为正；截面N/T/M2/M3在i端取节点抵抗力的负值，在j端取正值；V2/V3在i端取正值、j端取负值。节点位移和支反力按全局分量，转角服从右手定则。线载按构件实际长度计，斜杆亦然。一阶线弹性，自重、刚性楼板、刚域、二阶和施工阶段关闭；仅使用题定工况及组合。逐项完成input.md中所有请求，保留位置、截面侧别、正负号、分量、单位、工况/组合。跨内内力恢复须计入荷载项。实际运行OpenSees，保留版本、可运行输入、实际求解日志及原始结果/工况对应关系。正文和结构化结果均须给出题定结果，并独立检查平衡。附件不提供数值答案或原生执行证据。
