## Input t1

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Author-completed appendix: the listed connectivity and all absolute section properties complete the source attachment. All elements are pin-ended, axial-only trusses; member axial force N is positive in tension. No nodal masses are added. E and G are in MPa; density is kg/m3; all section properties are explicit. Unused rotational degrees of freedom are fixed only as bookkeeping for axial elements. The appended panel layout is x=0,3,6,9,12,15 m, with top heights 1.5,1.8,2.1,2.4,2.7,3 m. The diagonal endpoints are explicitly listed and are not a mirrored template. A1 is a 0.10 by 0.10 m solid square. BC1 is the first lower member, L0 to L1.

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
|L0|0|0|[true, true, true, true, true, true]|
|U0|0|1.5|[false, true, false, true, true, true]|
|L1|3|0|[false, true, false, true, true, true]|
|U1|3|1.8|[false, true, false, true, true, true]|
|L2|6|0|[false, true, false, true, true, true]|
|U2|6|2.1|[false, true, false, true, true, true]|
|L3|9|0|[false, true, false, true, true, true]|
|U3|9|2.4|[false, true, false, true, true, true]|
|L4|12|0|[false, true, false, true, true, true]|
|U4|12|2.7|[false, true, false, true, true, true]|
|L5|15|0|[false, true, true, true, true, true]|
|U5|15|3|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Input t1 — Elements

|id|nodes|material|
|---|---|---|
|BC1|["L0", "L1"]|M1|
|TC1|["U0", "U1"]|M2|
|BC2|["L1", "L2"]|M1|
|TC2|["U1", "U2"]|M2|
|BC3|["L2", "L3"]|M1|
|TC3|["U2", "U3"]|M2|
|BC4|["L3", "L4"]|M1|
|TC4|["U3", "U4"]|M2|
|BC5|["L4", "L5"]|M1|
|TC5|["U4", "U5"]|M2|
|V0|["L0", "U0"]|M1|
|V1|["L1", "U1"]|M1|
|V2|["L2", "U2"]|M1|
|V3|["L3", "U3"]|M1|
|V4|["L4", "U4"]|M1|
|V5|["L5", "U5"]|M1|
|DG1|["L0", "U1"]|M1|
|DG2|["U1", "L2"]|M1|
|DG3|["L2", "U3"]|M1|
|DG4|["L3", "U4"]|M1|
|DG5|["U4", "L5"]|M1|

Applies to every listed row: type = truss; section = A1.

## Input t1 — Materials

|id|name|E|G|
|---|---|---|---|
|M1|lower-and-web|200000|76923.07692307692|
|M2|upper-chord|210000|80769.23076923077|

Applies to every listed row: type = steel; nu = 0.3; rho = 7850.

## Input t1 — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|A1|rectangular|100.0|100.0|0.010000000000000002|8.333333333333335e-06|8.333333333333335e-06|1.4083333333333338e-05|

Applies to every listed row: name = id; shape · kind = type.

## Input t1 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load cases — D — Loads

|Load ID → element / node|fz|
|---|---|
|force-U1 → U1|-8|
|force-U3 → U3|-12|
|force-U5 → U5|-6|

Applies to every listed row: reference_frame = global; type = nodal.

## Input t1 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
