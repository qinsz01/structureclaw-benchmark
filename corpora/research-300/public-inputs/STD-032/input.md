## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|B1|3|0|[false, true, false, true, true, true]|
|B2|6|0|[false, true, false, true, true, true]|
|B3|9|0|[false, true, false, true, true, true]|
|B4|12|0|[false, true, false, true, true, true]|
|B5|15|0|[false, true, true, true, true, true]|
|T1|3|1|[false, true, false, true, true, true]|
|T2|6|2|[false, true, false, true, true, true]|
|R|7.5|2.5|[false, true, false, true, true, true]|
|T3|9|2|[false, true, false, true, true, true]|
|T4|12|1|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|BC1|["B0", "B1"]|
|BC2|["B1", "B2"]|
|BC3|["B2", "B3"]|
|BC4|["B3", "B4"]|
|BC5|["B4", "B5"]|
|TC1|["B0", "T1"]|
|TC2|["T1", "T2"]|
|TC3|["T2", "R"]|
|TC4|["R", "T3"]|
|TC5|["T3", "T4"]|
|TC6|["T4", "B5"]|
|V1|["B1", "T1"]|
|V2|["B2", "T2"]|
|V3|["B3", "T3"]|
|V4|["B4", "T4"]|
|D1|["B1", "T2"]|
|D2|["B2", "R"]|
|D3|["B3", "R"]|
|D4|["B4", "T3"]|

Applies to every listed row: type = truss; material = M1; section = T1.

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
|M1|steel|steel|205000|78846.15384615384|0.3|7850|

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

## Loads — Load cases — LC1

|Field|Value|
|---|---|
|id|LC1|
|type|dead|

## Loads — Load cases — LC1 — Loads

|Load ID → element / node|type|reference_frame|fz|
|---|---|---|---|
|P-T1 → T1, P-T2 → T2, P-R → R, P-T3 → T3, P-T4 → T4|nodal|global|-10|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case:LC1:node:T1:ux|node|T1|ux|m|—|—|
|case:LC1:node:T1:uz|node|T1|uz|m|—|—|
|case:LC1:node:T2:ux|node|T2|ux|m|—|—|
|case:LC1:node:T2:uz|node|T2|uz|m|—|—|
|case:LC1:node:R:ux|node|R|ux|m|—|—|
|case:LC1:node:R:uz|node|R|uz|m|—|—|
|case:LC1:node:T3:ux|node|T3|ux|m|—|—|
|case:LC1:node:T3:uz|node|T3|uz|m|—|—|
|case:LC1:node:T4:ux|node|T4|ux|m|—|—|
|case:LC1:node:T4:uz|node|T4|uz|m|—|—|
|case:LC1:member:TC3:N@0.790569415042:right|member|TC3|N|kN|0.7905694150420949|right|
|case:LC1:member:TC4:N@0.790569415042:right|member|TC4|N|kN|0.7905694150420949|right|
|case:LC1:member:D2:N@1.45773797371:right|member|D2|N|kN|1.4577379737113252|right|
|case:LC1:member:D3:N@1.45773797371:right|member|D3|N|kN|1.4577379737113252|right|
|case:LC1:node:B0:Fx|node|B0|Fx|kN|—|—|
|case:LC1:node:B0:Fz|node|B0|Fz|kN|—|—|
|case:LC1:node:B5:Fx|node|B5|Fx|kN|—|—|
|case:LC1:node:B5:Fz|node|B5|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = LC1.
