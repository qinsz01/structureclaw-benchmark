## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|z|restraints|
|---|---|---|---|
|A|0|0|[true, true, true, true, true, true]|
|B|18|0|[true, true, true, true, true, true]|
|C|36|0|[true, true, true, true, true, true]|
|L|0|9|[false, true, false, true, false, true]|
|J|18|9|[false, true, false, true, false, true]|
|R|36|9|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Geometry — Elements

|id|type|nodes|section|
|---|---|---|---|
|CL|column|["A", "L"]|COLUMN|
|CM|column|["B", "J"]|COLUMN|
|CR|column|["C", "R"]|COLUMN|
|R1|beam|["L", "J"]|ROOF|
|R2|beam|["J", "R"]|ROOF|

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

|Load ID → element / node|type|wz|start|end|fx|fz|
|---|---|---|---|---|---|---|
|D-1 → R1, D-2 → R2|distributed|-6|0.0|18.0|—|—|
|crane → J|nodal|—|—|—|4.9|-49.0|

Applies to every listed row: reference_frame = global.

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case:D:node:L:ux|node|L|ux|m|—|—|
|case:D:node:L:uz|node|L|uz|m|—|—|
|case:D:node:J:ux|node|J|ux|m|—|—|
|case:D:node:J:uz|node|J|uz|m|—|—|
|case:D:node:R:ux|node|R|ux|m|—|—|
|case:D:node:R:uz|node|R|uz|m|—|—|
|case:D:node:A:Fx|node|A|Fx|kN|—|—|
|case:D:node:A:Fz|node|A|Fz|kN|—|—|
|case:D:node:A:My|node|A|My|kN.m|—|—|
|case:D:node:B:Fx|node|B|Fx|kN|—|—|
|case:D:node:B:Fz|node|B|Fz|kN|—|—|
|case:D:node:B:My|node|B|My|kN.m|—|—|
|case:D:node:C:Fx|node|C|Fx|kN|—|—|
|case:D:node:C:Fz|node|C|Fz|kN|—|—|
|case:D:node:C:My|node|C|My|kN.m|—|—|
|case:D:member:CM:M2@0:right|member|CM|M2|kN.m|0.0|right|
|case:D:member:CM:M2@9:left|member|CM|M2|kN.m|9.0|left|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis and reporting conventions

Use the complete attached input tables. Global XYZ is right handed with Z upward; any planar model uses the XZ plane. All nodes listed are connected physical joints. Member local x points from i to j. In 2D local y=global +Y and local z=x cross y. In 3D local y=normalize(reference cross x), local z=x cross y; reference vectors are explicit. N is positive in tension. Signed section N/T/M2/M3 equal minus the i-end resisting action at the start and plus the j-end action at the end; V2/V3 use plus i-end and minus j-end action. Report global nodal displacements and support reactions; rotations follow the right-hand rule. Distributed loads act per actual member length, including inclined members. Use first-order linear elasticity with self-weight, rigid floors, rigid offsets, P-delta and construction stages off. Use only the specified cases and combinations. Compute every request in input.md, retaining its location, side, signed component, unit and case/combination. Interior forces must include applied-load terms. Execute OpenSees and retain version, runnable input, actual solver log and raw result/case mapping. Report the requested results in the response body as well as structured results; independently check equilibrium. No numerical answer or native execution evidence is supplied.
