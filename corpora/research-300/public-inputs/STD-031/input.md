## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|T0|0|3|[false, true, false, true, true, true]|
|B1|3|0|[false, true, false, true, true, true]|
|T1|3|3|[false, true, false, true, true, true]|
|B2|6|0|[false, true, false, true, true, true]|
|T2|6|3|[false, true, false, true, true, true]|
|B3|9|0|[false, true, false, true, true, true]|
|T3|9|3|[false, true, false, true, true, true]|
|B4|12|0|[false, true, false, true, true, true]|
|T4|12|3|[false, true, false, true, true, true]|
|B5|15|0|[false, true, false, true, true, true]|
|T5|15|3|[false, true, false, true, true, true]|
|B6|18|0|[false, true, true, true, true, true]|
|T6|18|3|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|BC1|["B0", "B1"]|
|TC1|["T0", "T1"]|
|BC2|["B1", "B2"]|
|TC2|["T1", "T2"]|
|BC3|["B2", "B3"]|
|TC3|["T2", "T3"]|
|BC4|["B3", "B4"]|
|TC4|["T3", "T4"]|
|BC5|["B4", "B5"]|
|TC5|["T4", "T5"]|
|BC6|["B5", "B6"]|
|TC6|["T5", "T6"]|
|V0|["B0", "T0"]|
|V1|["B1", "T1"]|
|V2|["B2", "T2"]|
|V3|["B3", "T3"]|
|V4|["B4", "T4"]|
|V5|["B5", "T5"]|
|V6|["B6", "T6"]|
|D1|["B0", "T1"]|
|D2|["T1", "B2"]|
|D3|["B2", "T3"]|
|D4|["T3", "B4"]|
|D5|["B4", "T5"]|
|D6|["T5", "B6"]|

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
|P-T1 → T1, P-T2 → T2, P-T3 → T3, P-T4 → T4, P-T5 → T5|nodal|global|-12|

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
|case:LC1:node:T3:ux|node|T3|ux|m|—|—|
|case:LC1:node:T3:uz|node|T3|uz|m|—|—|
|case:LC1:node:T4:ux|node|T4|ux|m|—|—|
|case:LC1:node:T4:uz|node|T4|uz|m|—|—|
|case:LC1:node:T5:ux|node|T5|ux|m|—|—|
|case:LC1:node:T5:uz|node|T5|uz|m|—|—|
|case:LC1:member:BC1:N@1.5:right|member|BC1|N|kN|1.5|right|
|case:LC1:member:TC1:N@1.5:right|member|TC1|N|kN|1.5|right|
|case:LC1:member:BC2:N@1.5:right|member|BC2|N|kN|1.5|right|
|case:LC1:member:TC2:N@1.5:right|member|TC2|N|kN|1.5|right|
|case:LC1:member:BC3:N@1.5:right|member|BC3|N|kN|1.5|right|
|case:LC1:member:TC3:N@1.5:right|member|TC3|N|kN|1.5|right|
|case:LC1:member:BC4:N@1.5:right|member|BC4|N|kN|1.5|right|
|case:LC1:member:TC4:N@1.5:right|member|TC4|N|kN|1.5|right|
|case:LC1:member:BC5:N@1.5:right|member|BC5|N|kN|1.5|right|
|case:LC1:member:TC5:N@1.5:right|member|TC5|N|kN|1.5|right|
|case:LC1:member:BC6:N@1.5:right|member|BC6|N|kN|1.5|right|
|case:LC1:member:TC6:N@1.5:right|member|TC6|N|kN|1.5|right|
|case:LC1:member:V0:N@1.5:right|member|V0|N|kN|1.5|right|
|case:LC1:member:V1:N@1.5:right|member|V1|N|kN|1.5|right|
|case:LC1:member:V2:N@1.5:right|member|V2|N|kN|1.5|right|
|case:LC1:member:V3:N@1.5:right|member|V3|N|kN|1.5|right|
|case:LC1:member:V4:N@1.5:right|member|V4|N|kN|1.5|right|
|case:LC1:member:V5:N@1.5:right|member|V5|N|kN|1.5|right|
|case:LC1:member:V6:N@1.5:right|member|V6|N|kN|1.5|right|
|case:LC1:member:D1:N@2.12132034356:right|member|D1|N|kN|2.1213203435596424|right|
|case:LC1:member:D2:N@2.12132034356:right|member|D2|N|kN|2.1213203435596424|right|
|case:LC1:member:D3:N@2.12132034356:right|member|D3|N|kN|2.1213203435596424|right|
|case:LC1:member:D4:N@2.12132034356:right|member|D4|N|kN|2.1213203435596424|right|
|case:LC1:member:D5:N@2.12132034356:right|member|D5|N|kN|2.1213203435596424|right|
|case:LC1:member:D6:N@2.12132034356:right|member|D6|N|kN|2.1213203435596424|right|
|case:LC1:node:B0:Fx|node|B0|Fx|kN|—|—|
|case:LC1:node:B0:Fz|node|B0|Fz|kN|—|—|
|case:LC1:node:B6:Fx|node|B6|Fx|kN|—|—|
|case:LC1:node:B6:Fz|node|B6|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = LC1.
