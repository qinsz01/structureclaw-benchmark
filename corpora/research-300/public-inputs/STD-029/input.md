## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|B1|6|0|[false, true, false, true, true, true]|
|B2|12|0|[false, true, true, true, true, true]|
|T1|3|1.5|[false, true, false, true, true, true]|
|T2|6|3|[false, true, false, true, true, true]|
|T3|9|1.5|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|BC0|["B0", "B1"]|
|BC1|["B1", "B2"]|
|TC0|["B0", "T1"]|
|TC1|["T1", "T2"]|
|TC2|["T2", "T3"]|
|TC3|["T3", "B2"]|
|W1|["T1", "B1"]|
|W2|["T2", "B1"]|
|W3|["T3", "B1"]|
|H|["T1", "T3"]|

Applies to every listed row: type = truss; material = M1; section = T1.

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

|id|name|type|E|nu|G|rho|
|---|---|---|---|---|---|---|
|M1|steel|steel|205000|0.3|78846.15384615384|7850|

## Properties — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|T1|rectangular|100.0|100.0|0.01|8.333333333333334e-06|8.333333333333334e-06|1.4083333333333335e-05|

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
|trussContract|Axial-only, pin-jointed elements. Only shared endpoint IDs connect members; geometric crossings do not add nodes.|
|axialForceConvention|N &gt; 0 is tension; N &lt; 0 is compression; report the signed value.|
|inactiveDofs|uy, rx, ry and rz are suppressed at every node; free in-plane translations remain ux and uz.|

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

|Load ID → element / node|reference_frame|type|fz|
|---|---|---|---|
|D-T1 → T1, D-T2 → T2, D-T3 → T3|global|nodal|-20|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|location · positionM|location · side|component|unit|
|---|---|---|---|---|---|---|
|case:D:member:BC0:N@0:right|member|BC0|0|right|N|kN|
|case:D:member:BC1:N@0:right|member|BC1|0|right|N|kN|
|case:D:member:TC0:N@0:right|member|TC0|0|right|N|kN|
|case:D:member:TC1:N@0:right|member|TC1|0|right|N|kN|
|case:D:member:TC2:N@0:right|member|TC2|0|right|N|kN|
|case:D:member:TC3:N@0:right|member|TC3|0|right|N|kN|
|case:D:member:W1:N@0:right|member|W1|0|right|N|kN|
|case:D:member:W2:N@0:right|member|W2|0|right|N|kN|
|case:D:member:W3:N@0:right|member|W3|0|right|N|kN|
|case:D:member:H:N@0:right|member|H|0|right|N|kN|
|case:D:node:T1:ux|node|T1|—|—|ux|m|
|case:D:node:T1:uz|node|T1|—|—|uz|m|
|case:D:node:T2:ux|node|T2|—|—|ux|m|
|case:D:node:T2:uz|node|T2|—|—|uz|m|
|case:D:node:T3:ux|node|T3|—|—|ux|m|
|case:D:node:T3:uz|node|T3|—|—|uz|m|
|case:D:node:B0:Fx|node|B0|—|—|Fx|kN|
|case:D:node:B0:Fz|node|B0|—|—|Fz|kN|
|case:D:node:B2:Fx|node|B2|—|—|Fx|kN|
|case:D:node:B2:Fz|node|B2|—|—|Fz|kN|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis and reporting conventions

完整输入见附件。全局XYZ为右手系，Z向上；平面结构位于XZ面。表列节点均为实际连通节点。构件局部x由i端指向j端；二维局部y为全局+Y，局部z=x×y；三维局部y=归一化(reference×x)，局部z=x×y，参考向量逐杆给出。N拉为正；截面N/T/M2/M3在i端取节点抵抗力的负值，在j端取正值；V2/V3在i端取正值、j端取负值。节点位移和支反力按全局分量，转角服从右手定则。线载按构件实际长度计，斜杆亦然。一阶线弹性，自重、刚性楼板、刚域、二阶和施工阶段关闭；仅使用题定工况及组合。逐项完成input.md中所有请求，保留位置、截面侧别、正负号、分量、单位、工况/组合。跨内内力恢复须计入荷载项。实际运行OpenSees，保留版本、可运行输入、实际求解日志及原始结果/工况对应关系。正文和结构化结果均须给出题定结果，并独立检查平衡。附件不提供数值答案或原生执行证据。
