## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|T0|0|1.6|[false, true, false, true, true, true]|
|B1|3|0|[false, true, false, true, true, true]|
|T1|3|1.9|[false, true, false, true, true, true]|
|B2|6|0|[false, true, false, true, true, true]|
|T2|6|2.2|[false, true, false, true, true, true]|
|B3|9|0|[false, true, false, true, true, true]|
|T3|9|2.5|[false, true, false, true, true, true]|
|B4|12|0|[false, true, false, true, true, true]|
|T4|12|2.2|[false, true, false, true, true, true]|
|B5|15|0|[false, true, false, true, true, true]|
|T5|15|1.9|[false, true, false, true, true, true]|
|B6|18|0|[false, true, true, true, true, true]|
|T6|18|1.6|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|BC0|["B0", "B1"]|
|BC1|["B1", "B2"]|
|BC2|["B2", "B3"]|
|BC3|["B3", "B4"]|
|BC4|["B4", "B5"]|
|BC5|["B5", "B6"]|
|TC0|["T0", "T1"]|
|TC1|["T1", "T2"]|
|TC2|["T2", "T3"]|
|TC3|["T3", "T4"]|
|TC4|["T4", "T5"]|
|TC5|["T5", "T6"]|
|V0|["B0", "T0"]|
|V1|["B1", "T1"]|
|V2|["B2", "T2"]|
|V3|["B3", "T3"]|
|V4|["B4", "T4"]|
|V5|["B5", "T5"]|
|V6|["B6", "T6"]|
|D0|["T0", "B1"]|
|D1|["T1", "B2"]|
|D2|["T2", "B3"]|
|D3|["T3", "B4"]|
|D4|["T4", "B5"]|
|D5|["T5", "B6"]|

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
|D-B1 → B1, D-B2 → B2, D-B3 → B3, D-B4 → B4, D-B5 → B5|global|nodal|-15|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|location · positionM|location · side|component|unit|
|---|---|---|---|---|---|---|
|case:D:member:BC0:N@0:right|member|BC0|0|right|N|kN|
|case:D:member:BC1:N@0:right|member|BC1|0|right|N|kN|
|case:D:member:BC2:N@0:right|member|BC2|0|right|N|kN|
|case:D:member:BC3:N@0:right|member|BC3|0|right|N|kN|
|case:D:member:BC4:N@0:right|member|BC4|0|right|N|kN|
|case:D:member:BC5:N@0:right|member|BC5|0|right|N|kN|
|case:D:member:TC0:N@0:right|member|TC0|0|right|N|kN|
|case:D:member:TC1:N@0:right|member|TC1|0|right|N|kN|
|case:D:member:TC2:N@0:right|member|TC2|0|right|N|kN|
|case:D:member:TC3:N@0:right|member|TC3|0|right|N|kN|
|case:D:member:TC4:N@0:right|member|TC4|0|right|N|kN|
|case:D:member:TC5:N@0:right|member|TC5|0|right|N|kN|
|case:D:member:V0:N@0:right|member|V0|0|right|N|kN|
|case:D:member:V1:N@0:right|member|V1|0|right|N|kN|
|case:D:member:V2:N@0:right|member|V2|0|right|N|kN|
|case:D:member:V3:N@0:right|member|V3|0|right|N|kN|
|case:D:member:V4:N@0:right|member|V4|0|right|N|kN|
|case:D:member:V5:N@0:right|member|V5|0|right|N|kN|
|case:D:member:V6:N@0:right|member|V6|0|right|N|kN|
|case:D:member:D0:N@0:right|member|D0|0|right|N|kN|
|case:D:member:D1:N@0:right|member|D1|0|right|N|kN|
|case:D:member:D2:N@0:right|member|D2|0|right|N|kN|
|case:D:member:D3:N@0:right|member|D3|0|right|N|kN|
|case:D:member:D4:N@0:right|member|D4|0|right|N|kN|
|case:D:member:D5:N@0:right|member|D5|0|right|N|kN|
|case:D:node:B1:ux|node|B1|—|—|ux|m|
|case:D:node:B1:uz|node|B1|—|—|uz|m|
|case:D:node:B2:ux|node|B2|—|—|ux|m|
|case:D:node:B2:uz|node|B2|—|—|uz|m|
|case:D:node:B3:ux|node|B3|—|—|ux|m|
|case:D:node:B3:uz|node|B3|—|—|uz|m|
|case:D:node:B4:ux|node|B4|—|—|ux|m|
|case:D:node:B4:uz|node|B4|—|—|uz|m|
|case:D:node:B5:ux|node|B5|—|—|ux|m|
|case:D:node:B5:uz|node|B5|—|—|uz|m|
|case:D:node:B0:Fx|node|B0|—|—|Fx|kN|
|case:D:node:B0:Fz|node|B0|—|—|Fz|kN|
|case:D:node:B6:Fx|node|B6|—|—|Fx|kN|
|case:D:node:B6:Fz|node|B6|—|—|Fz|kN|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis and reporting conventions

Use the complete attached input tables. Global XYZ is right handed with Z upward; any planar model uses the XZ plane. All nodes listed are connected physical joints. Member local x points from i to j. In 2D local y=global +Y and local z=x cross y. In 3D local y=normalize(reference cross x), local z=x cross y; reference vectors are explicit. N is positive in tension. Signed section N/T/M2/M3 equal minus the i-end resisting action at the start and plus the j-end action at the end; V2/V3 use plus i-end and minus j-end action. Report global nodal displacements and support reactions; rotations follow the right-hand rule. Distributed loads act per actual member length, including inclined members. Use first-order linear elasticity with self-weight, rigid floors, rigid offsets, P-delta and construction stages off. Use only the specified cases and combinations. Compute every request in input.md, retaining its location, side, signed component, unit and case/combination. Interior forces must include applied-load terms. Execute OpenSees and retain version, runnable input, actual solver log and raw result/case mapping. Report the requested results in the response body as well as structured results; independently check equilibrium. No numerical answer or native execution evidence is supplied.
