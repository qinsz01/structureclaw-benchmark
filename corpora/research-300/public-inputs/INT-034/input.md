## Attachment a

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Chord A=0.01 m2; VERT=0.8A; DIAG=1.2A. Only T1,T2,T3 have the 12 kN downward loads; end top nodes have no load.

## Attachment a

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|
|metadata|{}|

## Attachment a — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Attachment a — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|T0|0|2.4|[false, true, false, true, true, true]|
|B1|4|0|[false, true, false, true, true, true]|
|T1|4|2.4|[false, true, false, true, true, true]|
|B2|8|0|[false, true, false, true, true, true]|
|T2|8|2.4|[false, true, false, true, true, true]|
|B3|12|0|[false, true, false, true, true, true]|
|T3|12|2.4|[false, true, false, true, true, true]|
|B4|16|0|[false, true, true, true, true, true]|
|T4|16|2.4|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Attachment a — Elements

|id|nodes|section|
|---|---|---|
|BC0|["B0", "B1"]|A|
|TC0|["T0", "T1"]|A|
|BC1|["B1", "B2"]|A|
|TC1|["T1", "T2"]|A|
|BC2|["B2", "B3"]|A|
|TC2|["T2", "T3"]|A|
|BC3|["B3", "B4"]|A|
|TC3|["T3", "T4"]|A|
|V0|["B0", "T0"]|VERT|
|V1|["B1", "T1"]|VERT|
|V2|["B2", "T2"]|VERT|
|V3|["B3", "T3"]|VERT|
|V4|["B4", "T4"]|VERT|
|DG0|["B0", "T1"]|DIAG|
|DG1|["B1", "T2"]|DIAG|
|DG2|["T2", "B3"]|DIAG|
|DG3|["T3", "B4"]|DIAG|

Applies to every listed row: type = truss; material = M1.

## Attachment a — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|steel|steel|205000|78846.15384615384|0.3|7850|

## Attachment a — Sections

|id|properties · A|
|---|---|
|A|0.01|
|VERT|0.008|
|DIAG|0.012|

Applies to every listed row: type = rod; properties · Iy = 1e-05; properties · Iz = 1e-05; properties · J = 2e-05; name = id.

## Attachment a — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Attachment a — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fy|fz|mx|my|mz|
|---|---|---|---|---|---|---|---|---|
|top-1 → T1, top-2 → T2, top-3 → T3|global|nodal|0|0|-12|0|0|0|

## Attachment a — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
