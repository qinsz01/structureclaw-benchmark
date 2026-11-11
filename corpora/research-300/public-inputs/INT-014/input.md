## Input t1

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Author-completed physical appendix: elastic material M1 has E=206000 MPa, nu=0.3 and rho=7850 kg/m3; G is explicitly listed. The listed section properties are authoritative inputs. All members have zero roll and no end releases. Observation nodes share the connected beam, with no added support or mass. Input values complete the unspecified source appendix. M2 has E=70000 MPa, nu=0.33 and rho=2700 kg/m3, with explicit G=E/[2(1+nu)]. The CONFLICT field is unresolved, not an instruction to average materials.

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
|n1|2|[false, true, false, true, false, true]|
|n2|4|[false, true, false, true, false, true]|
|n3|5|[false, true, false, true, false, true]|
|n4|6|[false, true, false, true, false, true]|
|n5|8|[false, true, false, true, false, true]|
|n6|10|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input t1 — Elements

|id|nodes|material|
|---|---|---|
|b1|["n0", "n1"]|M1|
|b2|["n1", "n2"]|M1|
|b3|["n2", "n3"]|CONFLICT: M1 and M2 both referenced|
|b4|["n3", "n4"]|CONFLICT: M1 and M2 both referenced|
|b5|["n4", "n5"]|CONFLICT: M1 and M2 both referenced|
|b6|["n5", "n6"]|CONFLICT: M1 and M2 both referenced|

Applies to every listed row: type = beam; section = B1.

## Input t1 — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|
|M2|M2|elastic|70000|26315.78947368421|0.33|2700|

## Input t1 — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|B1|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|

Applies to every listed row: name = id; shape · kind = type.

## Input t1 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load cases — D — Loads

|Load ID → element / node|type|wz|fz|my|
|---|---|---|---|---|
|D-udl-b2 → b2, D-udl-b3 → b3, D-udl-b4 → b4, D-udl-b5 → b5|distributed|-9|—|—|
|main-point → n4|nodal|—|-25|—|
|right-end-moment → n6|nodal|—|—|-8|

Applies to every listed row: reference_frame = global.

## Input t1 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
