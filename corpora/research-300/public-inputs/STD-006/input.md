## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|restraints|
|---|---|---|
|N0|0|[true, true, true, true, false, true]|
|N1|4|[false, true, false, true, false, true]|
|N2|8|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|E01|["N0", "N1"]|
|E02|["N1", "N2"]|

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

|Load ID → element / node|type|start|end|wz|fx|fz|my|
|---|---|---|---|---|---|---|---|
|D-1 → E01, D-2 → E02|distributed|0|4.0|-18|—|—|—|
|D-3 → N2|nodal|—|—|—|0|0|20|

Applies to every listed row: reference_frame = global.

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
|case:D:node:N1:uz|node|N1|uz|m|—|—|
|case:D:node:N2:ry|node|N2|ry|rad|—|—|
|case:D:member:E01:M2@4:left|member|E01|M2|kN.m|4.0|left|
|case:D:member:E02:M2@0:right|member|E02|M2|kN.m|0|right|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis and reporting conventions

Use the complete attached input tables. Global XYZ is right handed with Z upward; any planar model uses the XZ plane. All nodes listed are connected physical joints. Member local x points from i to j. In 2D local y=global +Y and local z=x cross y. In 3D local y=normalize(reference cross x), local z=x cross y; reference vectors are explicit. N is positive in tension. Signed section N/T/M2/M3 equal minus the i-end resisting action at the start and plus the j-end action at the end; V2/V3 use plus i-end and minus j-end action. Report global nodal displacements and support reactions; rotations follow the right-hand rule. Distributed loads act per actual member length, including inclined members. Use first-order linear elasticity with self-weight, rigid floors, rigid offsets, P-delta and construction stages off. Use only the specified cases and combinations. Compute every request in input.md, retaining its location, side, signed component, unit and case/combination. Interior forces must include applied-load terms. Execute OpenSees and retain version, runnable input, actual solver log and raw result/case mapping. Report the requested results in the response body as well as structured results; independently check equilibrium. No numerical answer or native execution evidence is supplied.
