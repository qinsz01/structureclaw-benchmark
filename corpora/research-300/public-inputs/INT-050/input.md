## Input

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.

## Input

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|
|metadata|{}|

## Input — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input — Nodes

|id|x|z|restraints|
|---|---|---|---|
|A|0|0|[true, true, true, true, true, true]|
|B|12|0|[true, true, true, true, true, true]|
|C|30|0|[true, true, true, true, true, true]|
|L|0|6|[false, true, false, true, false, true]|
|M6|12|6|[false, true, false, true, false, true]|
|M8|12|8|[false, true, false, true, false, true]|
|R|30|8|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Input — Elements

|id|type|nodes|section|
|---|---|---|---|
|cL|column|["A", "L"]|C1|
|cMa|column|["B", "M6"]|C1|
|cMb|column|["M6", "M8"]|C2|
|cR|column|["C", "R"]|C1|
|roofL|beam|["L", "M6"]|B1|
|roofR|beam|["M8", "R"]|B1|

Applies to every listed row: material = M1.

## Input — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input — Sections

|id|type|shape · kind|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|
|B1|rectangular|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|rectangular|rectangular|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|C2|general|—|—|—|0.25|0.0026041666666666665|0.0026041666666666665|0.008802083333333334|

Applies to every listed row: name = id.

## Input — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load cases — D — Loads

|Load ID → element / node|wz|
|---|---|
|q-roofL → roofL|-5|
|q-roofR → roofR|-7|

Applies to every listed row: reference_frame = global; type = distributed.

## Input — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
