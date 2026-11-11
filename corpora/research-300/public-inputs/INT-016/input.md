## Input t1

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Author-completed physical appendix: elastic material M1 has E=206000 MPa, nu=0.3 and rho=7850 kg/m3; G is explicitly listed. The listed section properties are authoritative inputs. All members have zero roll and no end releases. Observation nodes share the connected beam, with no added support or mass. Input values complete the unspecified source appendix. B2 has the same A as B1 and 0.6 times both Iy and Iz; its explicitly completed J is 0.6 times B1. The point-load location is not linked to any observation node until the distance convention is resolved.

## Input t1

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|
|metadata|{}|

## Input t1 — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input t1 — Nodes

|id|x|restraints|
|---|---|---|
|n0|0|[true, true, true, true, false, true]|
|n1|4|[false, true, true, true, false, true]|
|n2|7.5|[false, true, false, true, false, true]|
|n3|11|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input t1 — Elements

|id|nodes|section|
|---|---|---|
|b1|["n0", "n1"]|B1|
|b2|["n1", "n2"]|B2|
|b3|["n2", "n3"]|B2|

Applies to every listed row: type = beam; material = M1.

## Input t1 — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input t1 — Sections

|id|type|shape · kind|shape · B|shape · H|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|B1|rectangular|rectangular|300.0|600.0|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|B2|general|—|—|—|0.003239999999999999|0.0008099999999999997|0.002224715624999999|

Applies to every listed row: properties · A = 0.18; name = id.

## Input t1 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load cases — D — Loads

|id|type|element|wz|span|distanceM|coordinateOrigin|measurementDirection|fz|
|---|---|---|---|---|---|---|---|---|
|D-udl-b1|distributed|b1|-10|—|—|—|—|—|
|D-udl-b2|distributed|b2|-10|—|—|—|—|—|
|D-udl-b3|distributed|b3|-10|—|—|—|—|—|
|long-span-point|point|—|—|second (long) span|3.5|null|null|-30|

Applies to every listed row: reference_frame = global.

## Input t1 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
