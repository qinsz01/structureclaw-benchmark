## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Section shape dimensions B and H are mm. Members are rigidly continuous at shared nodes; only listed supports restrain planar DOFs. Use OpenSees with the explicit properties and settings. Report signed values with location, global direction, unit, case/combination and current turn. Rz is support reaction in global +Z; fixed-end My is support reaction moment about global +Y by the right-hand rule. After a physical change, run the current state and retain input, snapshot, model differences, software version/settings, success log and result mapping. Do not guess essential missing input or present historical results as the updated result.
A continuous beam lies on global X with a pin at x=0 and vertical rollers at x=5 and 10 m. The free right end is initially x=12 m. In case D only the overhang x=10–12 m carries an 8 kN/m downward UDL, and a separate 10 kN downward point force acts at the free end. Both supported spans carry no UDL. All connected spans use B1.

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
|n0|0|[true, true, true, true, false, true]|
|n1|5|[false, true, true, true, false, true]|
|n2|10|[false, true, true, true, false, true]|
|n3|12|[false, true, false, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input tables — Elements

|id|nodes|
|---|---|
|b1|["n0", "n1"]|
|b2|["n1", "n2"]|
|b3|["n2", "n3"]|

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

|Load ID → element / node|type|start|end|wz|fz|
|---|---|---|---|---|---|
|overhang-b3 → b3|distributed|0|2|-8|—|
|free-end-force → n3|nodal|—|—|—|-10|

Applies to every listed row: reference_frame = global.

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
|b1|[0, 0, 5]|
|b2|[0, 0, 5]|
|b3|[0, 0, 2]|
