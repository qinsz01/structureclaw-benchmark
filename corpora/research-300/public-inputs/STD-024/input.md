## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|restraints|
|---|---|---|
|S0|0|[true, true, true, true, false, true]|
|P1|2.5|[false, true, false, true, false, true]|
|S1|5|[false, true, true, true, false, true]|
|P2|7.5|[false, true, false, true, false, true]|
|S2|10|[false, true, true, true, false, true]|
|P3|12.5|[false, true, false, true, false, true]|
|S3|15|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Geometry — Elements

|id|nodes|
|---|---|
|B1a|["S0", "P1"]|
|B1b|["P1", "S1"]|
|B2a|["S1", "P2"]|
|B2b|["P2", "S2"]|
|B3a|["S2", "P3"]|
|B3b|["P3", "S3"]|

Applies to every listed row: type = beam; material = M1; section = B1.

## Properties

|Field|Value|
|---|---|
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

|id|factors · W|
|---|---|
|C0|—|
|C1|1|

Applies to every listed row: factors · D = 1.

## Properties — Local axes

|Field|Value|
|---|---|
|spanLengthsM|[5, 5, 5]|
|spanSectionIds|["B1", "B1", "B1"]|
|beamTheory|Euler-Bernoulli|
|localAxes|Each beam runs along +global X; local 1=+X, local 2=+Y, local 3=+Z.|
|continuity|Every support and midpoint is one shared node; no member end releases.|

## Properties — Local axes — Observation nodes

|Field|Value|
|---|---|
|span-1-midpoint|P1|
|span-2-midpoint|P2|
|span-3-midpoint|P3|

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

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-B1a → B1a, D-B1b → B1b, D-B2a → B2a, D-B2b → B2b, D-B3a → B3a, D-B3b → B3b|global|distributed|-8|

## Loads — Load cases — W

|Field|Value|
|---|---|
|id|W|
|type|wind|

## Loads — Load cases — W — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|W-B2a → B2a, W-B2b → B2b|global|distributed|6|

## Loads — Load combinations

|id|factors · W|
|---|---|
|C0|—|
|C1|1|

Applies to every listed row: factors · D = 1.

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|selection · id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|---|
|combination:C0:node:S0:Fz|C0|node|S0|Fz|kN|—|—|
|combination:C0:node:S1:Fz|C0|node|S1|Fz|kN|—|—|
|combination:C0:node:S2:Fz|C0|node|S2|Fz|kN|—|—|
|combination:C0:node:S3:Fz|C0|node|S3|Fz|kN|—|—|
|combination:C0:node:S0:Fx|C0|node|S0|Fx|kN|—|—|
|combination:C0:node:S1:Fx|C0|node|S1|Fx|kN|—|—|
|combination:C0:node:S2:Fx|C0|node|S2|Fx|kN|—|—|
|combination:C0:node:S3:Fx|C0|node|S3|Fx|kN|—|—|
|combination:C0:node:P1:uz|C0|node|P1|uz|m|—|—|
|combination:C0:node:P2:uz|C0|node|P2|uz|m|—|—|
|combination:C0:node:P3:uz|C0|node|P3|uz|m|—|—|
|combination:C0:member:B1b:M2@2.5:left|C0|member|B1b|M2|kN.m|2.5|left|
|combination:C0:member:B2a:M2@0:right|C0|member|B2a|M2|kN.m|0|right|
|combination:C0:member:B2b:M2@2.5:left|C0|member|B2b|M2|kN.m|2.5|left|
|combination:C0:member:B3a:M2@0:right|C0|member|B3a|M2|kN.m|0|right|
|combination:C1:node:S0:Fz|C1|node|S0|Fz|kN|—|—|
|combination:C1:node:S1:Fz|C1|node|S1|Fz|kN|—|—|
|combination:C1:node:S2:Fz|C1|node|S2|Fz|kN|—|—|
|combination:C1:node:S3:Fz|C1|node|S3|Fz|kN|—|—|
|combination:C1:node:S0:Fx|C1|node|S0|Fx|kN|—|—|
|combination:C1:node:S1:Fx|C1|node|S1|Fx|kN|—|—|
|combination:C1:node:S2:Fx|C1|node|S2|Fx|kN|—|—|
|combination:C1:node:S3:Fx|C1|node|S3|Fx|kN|—|—|
|combination:C1:node:P1:uz|C1|node|P1|uz|m|—|—|
|combination:C1:node:P2:uz|C1|node|P2|uz|m|—|—|
|combination:C1:node:P3:uz|C1|node|P3|uz|m|—|—|
|combination:C1:member:B1b:M2@2.5:left|C1|member|B1b|M2|kN.m|2.5|left|
|combination:C1:member:B2a:M2@0:right|C1|member|B2a|M2|kN.m|0|right|
|combination:C1:member:B2b:M2@2.5:left|C1|member|B2b|M2|kN.m|2.5|left|
|combination:C1:member:B3a:M2@0:right|C1|member|B3a|M2|kN.m|0|right|

Applies to every listed row: selection · kind = combination.

## Analysis and reporting conventions

Use the complete attached input tables. Global XYZ is right handed with Z upward; any planar model uses the XZ plane. All nodes listed are connected physical joints. Member local x points from i to j. In 2D local y=global +Y and local z=x cross y. In 3D local y=normalize(reference cross x), local z=x cross y; reference vectors are explicit. N is positive in tension. Signed section N/T/M2/M3 equal minus the i-end resisting action at the start and plus the j-end action at the end; V2/V3 use plus i-end and minus j-end action. Report global nodal displacements and support reactions; rotations follow the right-hand rule. Distributed loads act per actual member length, including inclined members. Use first-order linear elasticity with self-weight, rigid floors, rigid offsets, P-delta and construction stages off. Use only the specified cases and combinations. Compute every request in input.md, retaining its location, side, signed component, unit and case/combination. Interior forces must include applied-load terms. Execute OpenSees and retain version, runnable input, actual solver log and raw result/case mapping. Report the requested results in the response body as well as structured results; independently check equilibrium. No numerical answer or native execution evidence is supplied.
