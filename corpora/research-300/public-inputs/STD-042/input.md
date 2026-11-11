## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|A0|0|0|0|[true, true, true, true, true, true]|
|B0|4|0|0|[true, true, true, true, true, true]|
|C0|2|3.4641016151377544|0|[true, true, true, true, true, true]|
|A1|0|0|3|[false, false, false, true, true, true]|
|B1|4|0|3|[false, false, false, true, true, true]|
|C1|2|3.4641016151377544|3|[false, false, false, true, true, true]|
|A2|0|0|6|[false, false, false, true, true, true]|
|B2|4|0|6|[false, false, false, true, true, true]|
|C2|2|3.4641016151377544|6|[false, false, false, true, true, true]|

## Geometry — Elements

|id|nodes|section|
|---|---|---|
|CH1|["A0", "A1"]|CHORD|
|CH2|["B0", "B1"]|CHORD|
|CH3|["C0", "C1"]|CHORD|
|CH4|["A1", "A2"]|CHORD|
|CH5|["B1", "B2"]|CHORD|
|CH6|["C1", "C2"]|CHORD|
|H1|["A0", "B0"]|HORIZONTAL|
|H2|["B0", "C0"]|HORIZONTAL|
|H3|["C0", "A0"]|HORIZONTAL|
|H4|["A1", "B1"]|HORIZONTAL|
|H5|["B1", "C1"]|HORIZONTAL|
|H6|["C1", "A1"]|HORIZONTAL|
|H7|["A2", "B2"]|HORIZONTAL|
|H8|["B2", "C2"]|HORIZONTAL|
|H9|["C2", "A2"]|HORIZONTAL|
|D1|["A0", "B1"]|DIAGONAL|
|D2|["B0", "A1"]|DIAGONAL|
|D3|["B0", "C1"]|DIAGONAL|
|D4|["C0", "B1"]|DIAGONAL|
|D5|["C0", "A1"]|DIAGONAL|
|D6|["A0", "C1"]|DIAGONAL|
|D7|["A1", "B2"]|DIAGONAL|
|D8|["B1", "A2"]|DIAGONAL|
|D9|["B1", "C2"]|DIAGONAL|
|D10|["C1", "B2"]|DIAGONAL|
|D11|["C1", "A2"]|DIAGONAL|
|D12|["A1", "C2"]|DIAGONAL|

Applies to every listed row: type = truss; material = M1.

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

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|CHORD|80.0|80.0|0.0064|3.413333333333334e-06|3.413333333333334e-06|5.768533333333335e-06|
|HORIZONTAL|70.0|70.0|0.004900000000000001|2.0008333333333342e-06|2.0008333333333342e-06|3.3814083333333346e-06|
|DIAGONAL|60.0|60.0|0.0036|1.0799999999999998e-06|1.0799999999999998e-06|1.8251999999999997e-06|

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
|inactiveDofs|["rx", "ry", "rz"]|
|crossingConnectivity|Members connect only at listed endpoints; all diagonal X crossings are unconnected.|

## Properties — Local axes — Element reference vectors

|Field|Value|
|---|---|
|CH1|[1, 0, 0]|
|CH2|[1, 0, 0]|
|CH3|[1, 0, 0]|
|CH4|[1, 0, 0]|
|CH5|[1, 0, 0]|
|CH6|[1, 0, 0]|
|H1|[0, 0, 1]|
|H2|[0, 0, 1]|
|H3|[0, 0, 1]|
|H4|[0, 0, 1]|
|H5|[0, 0, 1]|
|H6|[0, 0, 1]|
|H7|[0, 0, 1]|
|H8|[0, 0, 1]|
|H9|[0, 0, 1]|
|D1|[0, 0, 1]|
|D2|[0, 0, 1]|
|D3|[0, 0, 1]|
|D4|[0, 0, 1]|
|D5|[0, 0, 1]|
|D6|[0, 0, 1]|
|D7|[0, 0, 1]|
|D8|[0, 0, 1]|
|D9|[0, 0, 1]|
|D10|[0, 0, 1]|
|D11|[0, 0, 1]|
|D12|[0, 0, 1]|

## Properties — Local axes — Member groups

|Field|Value|
|---|---|
|inter-level-chords|["CH1", "CH2", "CH3", "CH4", "CH5", "CH6"]|
|horizontal-ties|["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9"]|
|inter-level-diagonals|["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"]|

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

|Load ID → element / node|reference_frame|type|fx|
|---|---|---|---|
|D-1 → A2, D-2 → B2, D-3 → C2|global|nodal|10.0|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case:D:node:A2:ux|node|A2|ux|m|—|—|
|case:D:node:A2:uy|node|A2|uy|m|—|—|
|case:D:node:A2:uz|node|A2|uz|m|—|—|
|case:D:node:B2:ux|node|B2|ux|m|—|—|
|case:D:node:B2:uy|node|B2|uy|m|—|—|
|case:D:node:B2:uz|node|B2|uz|m|—|—|
|case:D:node:C2:ux|node|C2|ux|m|—|—|
|case:D:node:C2:uy|node|C2|uy|m|—|—|
|case:D:node:C2:uz|node|C2|uz|m|—|—|
|case:D:member:CH1:N@1.5:right|member|CH1|N|kN|1.5|right|
|case:D:member:CH2:N@1.5:right|member|CH2|N|kN|1.5|right|
|case:D:member:CH3:N@1.5:right|member|CH3|N|kN|1.5|right|
|case:D:member:CH4:N@1.5:right|member|CH4|N|kN|1.5|right|
|case:D:member:CH5:N@1.5:right|member|CH5|N|kN|1.5|right|
|case:D:member:CH6:N@1.5:right|member|CH6|N|kN|1.5|right|
|case:D:member:H1:N@2:right|member|H1|N|kN|2.0|right|
|case:D:member:H2:N@2:right|member|H2|N|kN|2.0|right|
|case:D:member:H3:N@2:right|member|H3|N|kN|2.0|right|
|case:D:member:H4:N@2:right|member|H4|N|kN|2.0|right|
|case:D:member:H5:N@2:right|member|H5|N|kN|2.0|right|
|case:D:member:H6:N@2:right|member|H6|N|kN|2.0|right|
|case:D:member:H7:N@2:right|member|H7|N|kN|2.0|right|
|case:D:member:H8:N@2:right|member|H8|N|kN|2.0|right|
|case:D:member:H9:N@2:right|member|H9|N|kN|2.0|right|
|case:D:member:D1:N@2.5:right|member|D1|N|kN|2.5|right|
|case:D:member:D2:N@2.5:right|member|D2|N|kN|2.5|right|
|case:D:member:D3:N@2.5:right|member|D3|N|kN|2.5|right|
|case:D:member:D4:N@2.5:right|member|D4|N|kN|2.5|right|
|case:D:member:D5:N@2.5:right|member|D5|N|kN|2.5|right|
|case:D:member:D6:N@2.5:right|member|D6|N|kN|2.5|right|
|case:D:member:D7:N@2.5:right|member|D7|N|kN|2.5|right|
|case:D:member:D8:N@2.5:right|member|D8|N|kN|2.5|right|
|case:D:member:D9:N@2.5:right|member|D9|N|kN|2.5|right|
|case:D:member:D10:N@2.5:right|member|D10|N|kN|2.5|right|
|case:D:member:D11:N@2.5:right|member|D11|N|kN|2.5|right|
|case:D:member:D12:N@2.5:right|member|D12|N|kN|2.5|right|
|case:D:node:A0:Fx|node|A0|Fx|kN|—|—|
|case:D:node:A0:Fy|node|A0|Fy|kN|—|—|
|case:D:node:A0:Fz|node|A0|Fz|kN|—|—|
|case:D:node:B0:Fx|node|B0|Fx|kN|—|—|
|case:D:node:B0:Fy|node|B0|Fy|kN|—|—|
|case:D:node:B0:Fz|node|B0|Fz|kN|—|—|
|case:D:node:C0:Fx|node|C0|Fx|kN|—|—|
|case:D:node:C0:Fy|node|C0|Fy|kN|—|—|
|case:D:node:C0:Fz|node|C0|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|case:D:total-base:Fx|["case:D:node:A0:Fx", "case:D:node:B0:Fx", "case:D:node:C0:Fx"]|Signed sum of Fx reactions at A0, B0 and C0 in load case D.|
|case:D:total-base:Fy|["case:D:node:A0:Fy", "case:D:node:B0:Fy", "case:D:node:C0:Fy"]|Signed sum of Fy reactions at A0, B0 and C0 in load case D.|
|case:D:total-base:Fz|["case:D:node:A0:Fz", "case:D:node:B0:Fz", "case:D:node:C0:Fz"]|Signed sum of Fz reactions at A0, B0 and C0 in load case D.|

Applies to every listed row: operation = sum; unit = kN.

## Analysis and reporting conventions

Use the complete attached input tables. Global XYZ is right handed with Z upward; any planar model uses the XZ plane. All nodes listed are connected physical joints. Member local x points from i to j. In 2D local y=global +Y and local z=x cross y. In 3D local y=normalize(reference cross x), local z=x cross y; reference vectors are explicit. N is positive in tension. Signed section N/T/M2/M3 equal minus the i-end resisting action at the start and plus the j-end action at the end; V2/V3 use plus i-end and minus j-end action. Report global nodal displacements and support reactions; rotations follow the right-hand rule. Distributed loads act per actual member length, including inclined members. Use first-order linear elasticity with self-weight, rigid floors, rigid offsets, P-delta and construction stages off. Use only the specified cases and combinations. Compute every request in input.md, retaining its location, side, signed component, unit and case/combination. Interior forces must include applied-load terms. Execute OpenSees and retain version, runnable input, actual solver log and raw result/case mapping. Report the requested results in the response body as well as structured results; independently check equilibrium. No numerical answer or native execution evidence is supplied.
