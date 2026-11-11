## Input t1

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Author-completed appendix: the listed connectivity and all absolute section properties complete the source attachment. All elements are pin-ended, axial-only trusses; member axial force N is positive in tension. No nodal masses are added. E and G are in MPa; density is kg/m3; all section properties are explicit. Unused rotational degrees of freedom are fixed only as bookkeeping for axial elements. The coordinate expressions in the instruction define the exact geometry; the table uses their floating-point values. B restraint uy=null is unspecified, not free or fixed. A1 area is 0.01 m2; AD area is 0.015 m2. The first bottom-edge member AB is directed A to B. Rotations are inactive for all truss members.

## Input t1

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|

## Input t1 — Coordinate system

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input t1 — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|A|0|0|0|[true, true, true, true, true, true]|
|B|4|0|0|[false, null, true, true, true, true]|
|C|2|3.4641016151377544|0|[false, false, true, true, true, true]|
|D|2|1.1547005383792515|3|[false, false, false, true, true, true]|

## Input t1 — Elements

|id|nodes|section|
|---|---|---|
|AB|["A", "B"]|A1|
|BC|["B", "C"]|A1|
|CA|["C", "A"]|A1|
|AD|["A", "D"]|A_AD|
|BD|["B", "D"]|A1|
|CD|["C", "D"]|A1|

Applies to every listed row: type = truss; material = M1.

## Input t1 — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input t1 — Sections

|id|type|shape · kind|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|
|A1|rectangular|rectangular|100.0|100.0|0.010000000000000002|8.333333333333335e-06|8.333333333333335e-06|1.4083333333333338e-05|
|A_AD|general|—|—|—|0.015000000000000003|1.2500000000000002e-05|1.2500000000000002e-05|2.1125000000000005e-05|

Applies to every listed row: name = id.

## Input t1 — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input t1 — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fz|
|---|---|---|---|
|apex-force → D|global|nodal|-20|

## Input t1 — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input t1 — Metadata — Element reference vectors

|Field|Value|
|---|---|
|AB|[0, 0, 1]|
|BC|[0, 0, 1]|
|CA|[0, 0, 1]|
|AD|[0, 0, 1]|
|BD|[0, 0, 1]|
|CD|[0, 0, 1]|
