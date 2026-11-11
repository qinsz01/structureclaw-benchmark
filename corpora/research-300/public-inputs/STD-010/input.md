## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|restraints|
|---|---|---|
|N0|0|[true, true, true, true, true, true]|
|N1|4|[false, true, false, true, false, true]|
|N2|8|[true, true, true, true, true, true]|

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

## Properties — Load combinations

|id|factors · D|factors · L|
|---|---|---|
|D+L|1|1|

## Loads

|Field|Value|
|---|---|
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

|Load ID → element / node|reference_frame|type|start|end|wz|
|---|---|---|---|---|---|
|D-1 → E01, D-2 → E02|global|distributed|0|4.0|-8|

## Loads — Load cases — L

|Field|Value|
|---|---|
|id|L|
|type|live|

## Loads — Load cases — L — Loads

|Load ID → element / node|reference_frame|type|start|end|wz|
|---|---|---|---|---|---|
|L-1 → E01|global|distributed|0|4.0|-6|

## Loads — Load combinations

|id|factors · D|factors · L|
|---|---|---|
|D+L|1|1|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|selection · kind|selection · id|location · id|component|unit|
|---|---|---|---|---|---|
|case:D:node:N0:Fx|case|D|N0|Fx|kN|
|case:D:node:N0:Fz|case|D|N0|Fz|kN|
|case:D:node:N0:My|case|D|N0|My|kN.m|
|case:D:node:N2:Fx|case|D|N2|Fx|kN|
|case:D:node:N2:Fz|case|D|N2|Fz|kN|
|case:D:node:N2:My|case|D|N2|My|kN.m|
|case:D:node:N1:uz|case|D|N1|uz|m|
|case:L:node:N0:Fx|case|L|N0|Fx|kN|
|case:L:node:N0:Fz|case|L|N0|Fz|kN|
|case:L:node:N0:My|case|L|N0|My|kN.m|
|case:L:node:N2:Fx|case|L|N2|Fx|kN|
|case:L:node:N2:Fz|case|L|N2|Fz|kN|
|case:L:node:N2:My|case|L|N2|My|kN.m|
|case:L:node:N1:uz|case|L|N1|uz|m|
|combination:D+L:node:N0:Fx|combination|D+L|N0|Fx|kN|
|combination:D+L:node:N0:Fz|combination|D+L|N0|Fz|kN|
|combination:D+L:node:N0:My|combination|D+L|N0|My|kN.m|
|combination:D+L:node:N2:Fx|combination|D+L|N2|Fx|kN|
|combination:D+L:node:N2:Fz|combination|D+L|N2|Fz|kN|
|combination:D+L:node:N2:My|combination|D+L|N2|My|kN.m|
|combination:D+L:node:N1:uz|combination|D+L|N1|uz|m|

Applies to every listed row: location · kind = node.

## Analysis and reporting conventions

Use the complete attached input tables. Global XYZ is right handed with Z upward; any planar model uses the XZ plane. All nodes listed are connected physical joints. Member local x points from i to j. In 2D local y=global +Y and local z=x cross y. In 3D local y=normalize(reference cross x), local z=x cross y; reference vectors are explicit. N is positive in tension. Signed section N/T/M2/M3 equal minus the i-end resisting action at the start and plus the j-end action at the end; V2/V3 use plus i-end and minus j-end action. Report global nodal displacements and support reactions; rotations follow the right-hand rule. Distributed loads act per actual member length, including inclined members. Use first-order linear elasticity with self-weight, rigid floors, rigid offsets, P-delta and construction stages off. Use only the specified cases and combinations. Compute every request in input.md, retaining its location, side, signed component, unit and case/combination. Interior forces must include applied-load terms. Execute OpenSees and retain version, runnable input, actual solver log and raw result/case mapping. Report the requested results in the response body as well as structured results; independently check equilibrium. No numerical answer or native execution evidence is supplied.
