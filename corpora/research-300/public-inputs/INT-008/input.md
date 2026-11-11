## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Section shape dimensions B and H are in mm; all section properties use the explicit SI units stated above. Use OpenSees. Report signed values with node/location, global direction, unit, load case and current turn. Rz means the support reaction in global +Z; fixed-end My means support reaction moment about global +Y by the right-hand rule. Each change to a physical model requires a fresh run. Save input, model snapshot, version/settings, successful log and result mapping. Reuse results for a query only when traceable to the same unchanged state. Do not produce numerical answers while essential input is unresolved. Do not introduce releases, extra supports, masses, rigid zones, automatic combinations or additional loads. Connected internal nodes have no added translational support. Only explicit later edits change this input.
A 9 m beam lies on global X, fixed at x=0 and supported by a vertical roller at x=9 m. In case D, a downward 12 kN/m UDL acts only on x=2 to 7 m. The observation point is x=4.5 m. Connected stations at x=2, 3, 4.5, 7 and 8 m carry no extra supports.

## Input tables

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|

## Input tables — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input tables — Nodes

|id|x|restraints|
|---|---|---|
|n0|0|[true, true, true, true, true, true]|
|n1|2|[false, true, false, true, false, true]|
|n2|3|[false, true, false, true, false, true]|
|n3|4.5|[false, true, false, true, false, true]|
|n4|7|[false, true, false, true, false, true]|
|n5|8|[false, true, false, true, false, true]|
|n6|9|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input tables — Elements

|id|nodes|
|---|---|
|b1|["n0", "n1"]|
|b2|["n1", "n2"]|
|b3|["n2", "n3"]|
|b4|["n3", "n4"]|
|b5|["n4", "n5"]|
|b6|["n5", "n6"]|

Applies to every listed row: type = beam; material = M1; section = B1.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input tables — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|B1|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|

Applies to every listed row: name = id; shape · kind = type.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|end|
|---|---|
|partial-b2 → b2|1|
|partial-b3 → b3|1.5|
|partial-b4 → b4|2.5|

Applies to every listed row: reference_frame = global; type = distributed; start = 0; wz = -12.

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input tables — Metadata — Element reference vectors

|Field|Value|
|---|---|
|b1|[0, 0, 2]|
|b2|[0, 0, 1]|
|b3|[0, 0, 1.5]|
|b4|[0, 0, 2.5]|
|b5|[0, 0, 1]|
|b6|[0, 0, 1]|
