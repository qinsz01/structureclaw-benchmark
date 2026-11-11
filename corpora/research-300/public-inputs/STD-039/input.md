## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|T0|0|3|[false, true, false, true, true, true]|
|B1|4|0|[false, true, false, true, true, true]|
|T1|4|3|[false, true, false, true, true, true]|
|B2|8|0|[false, true, false, true, true, true]|
|T2|8|3|[false, true, false, true, true, true]|
|B3|12|0|[false, true, false, true, true, true]|
|T3|12|3|[false, true, false, true, true, true]|
|B4|16|0|[false, true, false, true, true, true]|
|T4|16|3|[false, true, false, true, true, true]|
|B5|20|0|[false, true, true, true, true, true]|
|T5|20|3|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Geometry — Elements

|id|nodes|section|
|---|---|---|
|BC1|["B0", "B1"]|A2|
|TC1|["T0", "T1"]|A1|
|BC2|["B1", "B2"]|A2|
|TC2|["T1", "T2"]|A1|
|BC3|["B2", "B3"]|A2|
|TC3|["T2", "T3"]|A1|
|BC4|["B3", "B4"]|A2|
|TC4|["T3", "T4"]|A1|
|BC5|["B4", "B5"]|A2|
|TC5|["T4", "T5"]|A1|
|V0|["B0", "T0"]|A3|
|V1|["B1", "T1"]|A3|
|V2|["B2", "T2"]|A3|
|V3|["B3", "T3"]|A3|
|V4|["B4", "T4"]|A3|
|V5|["B5", "T5"]|A3|
|D1|["T0", "B1"]|A3|
|D2|["T1", "B2"]|A3|
|D3|["B2", "T3"]|A3|
|D4|["B3", "T4"]|A3|
|D5|["B4", "T5"]|A3|

Applies to every listed row: type = truss; material = M1.

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
|M1|steel|steel|206000|79230.76923076923|0.3|7850|

## Properties — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|A1|109.54451150103323|109.54451150103323|0.012|1.2e-05|1.2e-05|2.0280000000000002e-05|
|A2|100.0|100.0|0.01|8.333333333333334e-06|8.333333333333334e-06|1.4083333333333335e-05|
|A3|77.45966692414834|77.45966692414834|0.006|3e-06|3e-06|5.070000000000001e-06|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

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

|Load ID → element / node|fz|
|---|---|
|P-T1 → T1|-8|
|P-T2 → T2|-12|
|P-T3 → T3|-16|
|P-T4 → T4|-10|

Applies to every listed row: type = nodal; reference_frame = global.

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
|case:LC1:member:BC1:N@2:right|member|BC1|N|kN|2.0|right|
|case:LC1:member:TC1:N@2:right|member|TC1|N|kN|2.0|right|
|case:LC1:member:BC2:N@2:right|member|BC2|N|kN|2.0|right|
|case:LC1:member:TC2:N@2:right|member|TC2|N|kN|2.0|right|
|case:LC1:member:BC3:N@2:right|member|BC3|N|kN|2.0|right|
|case:LC1:member:TC3:N@2:right|member|TC3|N|kN|2.0|right|
|case:LC1:member:BC4:N@2:right|member|BC4|N|kN|2.0|right|
|case:LC1:member:TC4:N@2:right|member|TC4|N|kN|2.0|right|
|case:LC1:member:BC5:N@2:right|member|BC5|N|kN|2.0|right|
|case:LC1:member:TC5:N@2:right|member|TC5|N|kN|2.0|right|
|case:LC1:member:V0:N@1.5:right|member|V0|N|kN|1.5|right|
|case:LC1:member:V1:N@1.5:right|member|V1|N|kN|1.5|right|
|case:LC1:member:V2:N@1.5:right|member|V2|N|kN|1.5|right|
|case:LC1:member:V3:N@1.5:right|member|V3|N|kN|1.5|right|
|case:LC1:member:V4:N@1.5:right|member|V4|N|kN|1.5|right|
|case:LC1:member:V5:N@1.5:right|member|V5|N|kN|1.5|right|
|case:LC1:member:D1:N@2.5:right|member|D1|N|kN|2.5|right|
|case:LC1:member:D2:N@2.5:right|member|D2|N|kN|2.5|right|
|case:LC1:member:D3:N@2.5:right|member|D3|N|kN|2.5|right|
|case:LC1:member:D4:N@2.5:right|member|D4|N|kN|2.5|right|
|case:LC1:member:D5:N@2.5:right|member|D5|N|kN|2.5|right|
|case:LC1:node:B0:Fx|node|B0|Fx|kN|—|—|
|case:LC1:node:B0:Fz|node|B0|Fz|kN|—|—|
|case:LC1:node:B5:Fx|node|B5|Fx|kN|—|—|
|case:LC1:node:B5:Fz|node|B5|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = LC1.
