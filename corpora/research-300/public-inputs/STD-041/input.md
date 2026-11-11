## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|A|0|0|0|[true, true, true, true, true, true]|
|B|6|0|0|[true, true, true, true, true, true]|
|C|6|6|0|[true, true, true, true, true, true]|
|D|0|6|0|[true, true, true, true, true, true]|
|P|2|3|3|[false, false, false, true, true, true]|

## Geometry — Elements

|id|nodes|
|---|---|
|AB|["A", "B"]|
|BC|["B", "C"]|
|CD|["C", "D"]|
|DA|["D", "A"]|
|AP|["A", "P"]|
|BP|["B", "P"]|
|CP|["C", "P"]|
|DP|["D", "P"]|

Applies to every listed row: type = truss; material = M1; section = A1.

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
|dimension|3d|
|plane|null|
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
|A1|rectangular|100.0|40.0|0.004|5.333333333333335e-07|3.333333333333334e-06|1.5968802133333337e-06|

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
|inactiveDofs|["rx", "ry", "rz"]|

## Properties — Local axes — Element reference vectors

|Field|Value|
|---|---|
|AB|[0, 0, 1]|
|BC|[0, 0, 1]|
|CD|[0, 0, 1]|
|DA|[0, 0, 1]|
|AP|[0, 0, 1]|
|BP|[0, 0, 1]|
|CP|[0, 0, 1]|
|DP|[0, 0, 1]|

## Properties — Local axes — Member groups

|Field|Value|
|---|---|
|base-perimeter|["AB", "BC", "CD", "DA"]|
|inclined|["AP", "BP", "CP", "DP"]|

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

|Load ID → element / node|reference_frame|type|fx|fz|
|---|---|---|---|---|
|D-1 → P|global|nodal|15.0|-40.0|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case:D:node:P:ux|node|P|ux|m|—|—|
|case:D:node:P:uy|node|P|uy|m|—|—|
|case:D:node:P:uz|node|P|uz|m|—|—|
|case:D:member:AB:N@3:right|member|AB|N|kN|3.0|right|
|case:D:member:BC:N@3:right|member|BC|N|kN|3.0|right|
|case:D:member:CD:N@3:right|member|CD|N|kN|3.0|right|
|case:D:member:DA:N@3:right|member|DA|N|kN|3.0|right|
|case:D:member:AP:N@2.34520787991:right|member|AP|N|kN|2.345207879911715|right|
|case:D:member:BP:N@2.91547594742:right|member|BP|N|kN|2.9154759474226504|right|
|case:D:member:CP:N@2.91547594742:right|member|CP|N|kN|2.9154759474226504|right|
|case:D:member:DP:N@2.34520787991:right|member|DP|N|kN|2.345207879911715|right|
|case:D:node:A:Fx|node|A|Fx|kN|—|—|
|case:D:node:A:Fy|node|A|Fy|kN|—|—|
|case:D:node:A:Fz|node|A|Fz|kN|—|—|
|case:D:node:B:Fx|node|B|Fx|kN|—|—|
|case:D:node:B:Fy|node|B|Fy|kN|—|—|
|case:D:node:B:Fz|node|B|Fz|kN|—|—|
|case:D:node:C:Fx|node|C|Fx|kN|—|—|
|case:D:node:C:Fy|node|C|Fy|kN|—|—|
|case:D:node:C:Fz|node|C|Fz|kN|—|—|
|case:D:node:D:Fx|node|D|Fx|kN|—|—|
|case:D:node:D:Fy|node|D|Fy|kN|—|—|
|case:D:node:D:Fz|node|D|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis and reporting conventions

完整输入见附件。全局XYZ为右手系，Z向上；平面结构位于XZ面。表列节点均为实际连通节点。构件局部x由i端指向j端；二维局部y为全局+Y，局部z=x×y；三维局部y=归一化(reference×x)，局部z=x×y，参考向量逐杆给出。N拉为正；截面N/T/M2/M3在i端取节点抵抗力的负值，在j端取正值；V2/V3在i端取正值、j端取负值。节点位移和支反力按全局分量，转角服从右手定则。线载按构件实际长度计，斜杆亦然。一阶线弹性，自重、刚性楼板、刚域、二阶和施工阶段关闭；仅使用题定工况及组合。逐项完成input.md中所有请求，保留位置、截面侧别、正负号、分量、单位、工况/组合。跨内内力恢复须计入荷载项。实际运行OpenSees，保留版本、可运行输入、实际求解日志及原始结果/工况对应关系。正文和结构化结果均须给出题定结果，并独立检查平衡。附件不提供数值答案或原生执行证据。
