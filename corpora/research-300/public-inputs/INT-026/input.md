## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Section shape dimensions B and H are mm. Members are rigidly continuous at shared nodes; only listed supports restrain planar DOFs. Use OpenSees with the explicit properties and settings. Report signed values with location, global direction, unit, case/combination and current turn. Rz is support reaction in global +Z; fixed-end My is support reaction moment about global +Y by the right-hand rule. After a physical change, run the current state and retain input, snapshot, model differences, software version/settings, success log and result mapping. Do not guess essential missing input or present historical results as the updated result.
A continuous beam lies on global X with spans 4, 6, 5 and 4 m. Supports are a pin at x=0 and vertical rollers at x=4, 10, 15 and 19 m. The middle two spans x=4–15 m use B2; the first and fourth spans use B1. B3 is provided as a separate available section. Case D has a downward 8 kN/m UDL over the entire beam plus a separate downward 16 kN point force at fourth-span midpoint x=17 m. Case L has downward 10 kN/m only on spans 2 and 4, x=4–10 m and x=15–19 m. Prescribed combinations remain C1=D and C2=D+L. The x=17 m observation/load node is connected to both adjacent members and has no extra support.

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
|n1|4|[false, true, true, true, false, true]|
|n2|10|[false, true, true, true, false, true]|
|n3|15|[false, true, true, true, false, true]|
|n4|17|[false, true, false, true, false, true]|
|n5|19|[false, true, true, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input tables — Elements

|id|nodes|section|
|---|---|---|
|b1|["n0", "n1"]|B1|
|b2|["n1", "n2"]|B2|
|b3|["n2", "n3"]|B2|
|b4|["n3", "n4"]|B1|
|b5|["n4", "n5"]|B1|

Applies to every listed row: type = beam; material = M1.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input tables — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|B2|300.0|700.0|0.21|0.008574999999999998|0.0015749999999999998|0.004603782069970844|
|B3|350.0|800.0|0.27999999999999997|0.014933333333333335|0.0028583333333333325|0.008291641882975894|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|type|start|end|wz|fz|
|---|---|---|---|---|---|
|dead-full-b1 → b1|distributed|0|4|-8|—|
|dead-full-b2 → b2|distributed|0|6|-8|—|
|dead-full-b3 → b3|distributed|0|5|-8|—|
|dead-full-b4 → b4, dead-full-b5 → b5|distributed|0|2|-8|—|
|dead-fourth-midpoint → n4|nodal|—|—|—|-16|

Applies to every listed row: reference_frame = global.

## Input tables — Load cases — L

|Field|Value|
|---|---|
|id|L|
|type|live|

## Input tables — Load cases — L — Loads

|Load ID → element / node|end|
|---|---|
|live-second-b2 → b2|6|
|live-fourth-b4 → b4, live-fourth-b5 → b5|2|

Applies to every listed row: reference_frame = global; type = distributed; start = 0; wz = -10.

## Input tables — Load combinations

|id|factors · L|
|---|---|
|C1|—|
|C2|1|

Applies to every listed row: factors · D = 1.

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
|b1|[0, 0, 4]|
|b2|[0, 0, 6]|
|b3|[0, 0, 5]|
|b4|[0, 0, 2]|
|b5|[0, 0, 2]|
