## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Section shape dimensions B and H are mm. Members are rigidly continuous at shared nodes; only listed supports restrain planar DOFs. Use OpenSees with the explicit properties and settings. Report signed values with location, global direction, unit, case/combination and current turn. Rz is support reaction in global +Z; fixed-end My is support reaction moment about global +Y by the right-hand rule. After a physical change, run the current state and retain input, snapshot, model differences, software version/settings, success log and result mapping. Do not guess essential missing input or present historical results as the updated result.
A continuous beam has three 5 m spans on global X: a pin at x=0 and vertical rollers at x=5, 10 and 15 m. All roller restraints are bilateral, preventing either upward or downward motion and allowing signed reactions. End spans use B1 and the middle span uses B2; B2 has half B1 Iy and Iz, equal A, and unchanged J/material. Global +Z is upward. Case D is wz=-8 kN/m over the entire beam. Case W is wz=+6 kN/m only over the middle span x=5–10 m. The three explicitly prescribed linear combinations are C0=1.0D, C1=1.0D+1.0W and C2=0.9D+1.5W. These are task-defined coefficients, with no automatic code combination generation.

## Input tables

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|

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
|n2|7.5|[false, true, false, true, false, true]|
|n3|10|[false, true, true, true, false, true]|
|n4|15|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input tables — Elements

|id|nodes|section|
|---|---|---|
|b1|["n0", "n1"]|B1|
|b2|["n1", "n2"]|B2|
|b3|["n2", "n3"]|B2|
|b4|["n3", "n4"]|B1|

Applies to every listed row: type = beam; material = M1.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input tables — Sections

|id|type|shape · kind|shape · B|shape · H|properties · Iy|properties · Iz|
|---|---|---|---|---|---|---|
|B1|rectangular|rectangular|300.0|600.0|0.0053999999999999986|0.0013499999999999996|
|B2|general|—|—|—|0.0026999999999999993|0.0006749999999999998|

Applies to every listed row: properties · A = 0.18; properties · J = 0.0037078593749999985; name = id.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|end|
|---|---|
|downward-b1 → b1, downward-b4 → b4|5|
|downward-b2 → b2|2.5|
|downward-b3 → b3|2.5|

Applies to every listed row: reference_frame = global; type = distributed; start = 0; wz = -8.

## Input tables — Load cases — W

|Field|Value|
|---|---|
|id|W|
|type|wind|

## Input tables — Load cases — W — Loads

|Load ID → element / node|
|---|
|upward-b2 → b2|
|upward-b3 → b3|

Applies to every listed row: reference_frame = global; type = distributed; start = 0; end = 2.5; wz = 6.

## Input tables — Load combinations

|id|factors · D|factors · W|
|---|---|---|
|C0|1|—|
|C1|1|1|
|C2|0.9|1.5|

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
|b2|[0, 0, 2.5]|
|b3|[0, 0, 2.5]|
|b4|[0, 0, 5]|
