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
|M1|3|1.5|[false, true, false, true, true, true]|
|M2|6|1.5|[false, true, false, true, true, true]|
|M3|9|1.5|[false, true, false, true, true, true]|
|M4|12|1.5|[false, true, false, true, true, true]|
|M5|15|1.5|[false, true, false, true, true, true]|

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
|V6|["B6", "T6"]|
|V1L|["B1", "M1"]|
|V1U|["M1", "T1"]|
|V2L|["B2", "M2"]|
|V2U|["M2", "T2"]|
|V3L|["B3", "M3"]|
|V3U|["M3", "T3"]|
|V4L|["B4", "M4"]|
|V4U|["M4", "T4"]|
|V5L|["B5", "M5"]|
|V5U|["M5", "T5"]|
|K01|["B0", "M1"]|
|K02|["T0", "M1"]|
|K03|["B1", "M2"]|
|K04|["T1", "M2"]|
|K05|["B2", "M3"]|
|K06|["T2", "M3"]|
|K07|["M3", "B4"]|
|K08|["M3", "T4"]|
|K09|["M4", "B5"]|
|K10|["M4", "T5"]|
|K11|["M5", "B6"]|
|K12|["M5", "T6"]|

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
|M1|steel|steel|206000|79230.76923076923|0.3|7850|

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
|P-T1 → T1, P-T2 → T2|nodal|global|-12|

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
|case:LC1:member:V0:N@1.5:right|member|V0|N|kN|1.5|right|
|case:LC1:member:V6:N@1.5:right|member|V6|N|kN|1.5|right|
|case:LC1:member:V1L:N@0.75:right|member|V1L|N|kN|0.75|right|
|case:LC1:member:V1U:N@0.75:right|member|V1U|N|kN|0.75|right|
|case:LC1:member:V2L:N@0.75:right|member|V2L|N|kN|0.75|right|
|case:LC1:member:V2U:N@0.75:right|member|V2U|N|kN|0.75|right|
|case:LC1:member:V3L:N@0.75:right|member|V3L|N|kN|0.75|right|
|case:LC1:member:V3U:N@0.75:right|member|V3U|N|kN|0.75|right|
|case:LC1:member:V4L:N@0.75:right|member|V4L|N|kN|0.75|right|
|case:LC1:member:V4U:N@0.75:right|member|V4U|N|kN|0.75|right|
|case:LC1:member:V5L:N@0.75:right|member|V5L|N|kN|0.75|right|
|case:LC1:member:V5U:N@0.75:right|member|V5U|N|kN|0.75|right|
|case:LC1:member:K01:N@1.67705098312:right|member|K01|N|kN|1.6770509831248424|right|
|case:LC1:member:K02:N@1.67705098312:right|member|K02|N|kN|1.6770509831248424|right|
|case:LC1:member:K03:N@1.67705098312:right|member|K03|N|kN|1.6770509831248424|right|
|case:LC1:member:K04:N@1.67705098312:right|member|K04|N|kN|1.6770509831248424|right|
|case:LC1:member:K05:N@1.67705098312:right|member|K05|N|kN|1.6770509831248424|right|
|case:LC1:member:K06:N@1.67705098312:right|member|K06|N|kN|1.6770509831248424|right|
|case:LC1:member:K07:N@1.67705098312:right|member|K07|N|kN|1.6770509831248424|right|
|case:LC1:member:K08:N@1.67705098312:right|member|K08|N|kN|1.6770509831248424|right|
|case:LC1:member:K09:N@1.67705098312:right|member|K09|N|kN|1.6770509831248424|right|
|case:LC1:member:K10:N@1.67705098312:right|member|K10|N|kN|1.6770509831248424|right|
|case:LC1:member:K11:N@1.67705098312:right|member|K11|N|kN|1.6770509831248424|right|
|case:LC1:member:K12:N@1.67705098312:right|member|K12|N|kN|1.6770509831248424|right|
|case:LC1:node:B0:Fx|node|B0|Fx|kN|—|—|
|case:LC1:node:B0:Fz|node|B0|Fz|kN|—|—|
|case:LC1:node:B6:Fx|node|B6|Fx|kN|—|—|
|case:LC1:node:B6:Fz|node|B6|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = LC1.
