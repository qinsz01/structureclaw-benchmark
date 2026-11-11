## Input t1

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Unresolved conflicting dimension note: overall width=30 m; individual bay schedule=18 m+18 m. Coordinates below are the bay-schedule alternative, not a resolution.

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

|id|x|z|restraints|
|---|---|---|---|
|A|0|0|[true, true, true, true, true, true]|
|B|18|0|[true, true, true, true, true, true]|
|C|36|0|[true, true, true, true, true, true]|
|L|0|9|[false, true, false, true, false, true]|
|M|18|9|[false, true, false, true, false, true]|
|P|27|9|[false, true, false, true, false, true]|
|R|36|9|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input t1 — Elements

|id|type|nodes|section|
|---|---|---|---|
|cL|column|["A", "L"]|C1|
|cM|column|["B", "M"]|C1|
|cR|column|["C", "R"]|C1|
|roofL|beam|["L", "M"]|B1|
|roofRa|beam|["M", "P"]|B1|
|roofRb|beam|["P", "R"]|B1|

Applies to every listed row: material = M1.

## Input t1 — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input t1 — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input t1 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load cases — D — Loads

|Load ID → element / node|type|wz|fz|
|---|---|---|---|
|q-roofL → roofL, q-roofRa → roofRa, q-roofRb → roofRb|distributed|-6|—|
|hoist → P|nodal|—|-24|

Applies to every listed row: reference_frame = global.

## Input t1 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
