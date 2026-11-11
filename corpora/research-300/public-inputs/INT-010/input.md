## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. Components other than the stated downward direction are zero; the left-half load case assignment is unresolved. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Section shape dimensions B and H are in mm; all section properties use the explicit SI units stated above. Use OpenSees. Report signed values with node/location, global direction, unit, load case and current turn. Rz means the support reaction in global +Z; fixed-end My means support reaction moment about global +Y by the right-hand rule. Each change to a physical model requires a fresh run. Save input, model snapshot, version/settings, successful log and result mapping. Reuse results for a query only when traceable to the same unchanged state. Do not produce numerical answers while essential input is unresolved. Do not introduce releases, extra supports, masses, rigid zones, automatic combinations or additional loads. Connected internal nodes have no added translational support. Only explicit later edits change this input.
An 8 m beam lies on global X with both ends fixed. The left half x=0–4 m uses B1 and the right half x=4–8 m uses B2. B2 Iy and Iz are twice B1, with all other properties identical. A full-span downward 8 kN/m UDL is labelled D. A separate downward 6 kN/m UDL on the left half is inconsistently labelled both D and L. Those two labels refer to one physical left-half load entry, whose case assignment remains unresolved.

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
|n0|0|[true, true, true, true, true, true]|
|n1|4|[false, true, false, true, false, true]|
|n2|8|[true, true, true, true, true, true]|

Applies to every listed row: y = 0; z = 0.

## Input tables — Elements

|id|nodes|section|
|---|---|---|
|b1|["n0", "n1"]|B1|
|b2|["n1", "n2"]|B2|

Applies to every listed row: type = beam; material = M1.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input tables — Sections

|id|type|shape · kind|shape · B|shape · H|properties · Iy|properties · Iz|
|---|---|---|---|---|---|---|
|B1|rectangular|rectangular|300.0|600.0|0.0053999999999999986|0.0013499999999999996|
|B2|general|—|—|—|0.010799999999999997|0.0026999999999999993|

Applies to every listed row: properties · A = 0.18; properties · J = 0.0037078593749999985; name = id.

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
|b2|[0, 0, 4]|
