## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; known force units are explicit in each prose entry; the downward tip-force value has NO supplied force unit; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. Unspecified components of fully specified loads are zero; the unresolved downward force remains unknown and is not zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Section shape dimensions B and H are in mm; all section properties use the explicit SI units stated above. Use OpenSees. Report signed values with node/location, global direction, unit, load case and current turn. Rz means the support reaction in global +Z; fixed-end My means support reaction moment about global +Y by the right-hand rule. Each change to a physical model requires a fresh run. Save input, model snapshot, version/settings, successful log and result mapping. Reuse results for a query only when traceable to the same unchanged state. Do not produce numerical answers while essential input is unresolved. Do not introduce releases, extra supports, masses, rigid zones, automatic combinations or additional loads. Connected internal nodes have no added translational support. Only explicit later edits change this input.
A 3 m cantilever lies on global X. The left end x=0 is fixed and the right end x=3 m is free. At the free end, an independent axial force is +5 kN in global X. A separate downward point force is written as 10, with its force unit omitted. No unit convention in this appendix applies to that unresolved value.

## Input tables

|Field|Value|
|---|---|
|schema_version|2.2.0|

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
|n1|3|[false, true, false, true, false, true]|

Applies to every listed row: y = 0; z = 0.

## Input tables — Elements

|id|type|nodes|material|section|
|---|---|---|---|---|
|b1|beam|["n0", "n1"]|M1|B1|

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Input tables — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|B1|rectangular|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|

Applies to every listed row: name = id; shape · kind = type.

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
|b1|[0, 0, 3]|
