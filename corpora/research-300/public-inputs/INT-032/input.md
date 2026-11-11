## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
null in DG1.nodes[1] means the endpoint has not been supplied; it is not permission to remove the member. There is no additional endpoint rule.

## Input tables

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|
|metadata|{}|

## Input tables — Coordinate system

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input tables — Nodes

|id|x|z|restraints|
|---|---|---|---|
|B0|0|0|[true, true, true, true, true, true]|
|B1|3|0|[false, true, false, true, true, true]|
|B2|6|0|[false, true, false, true, true, true]|
|B3|9|0|[false, true, false, true, true, true]|
|B4|12|0|[false, true, false, true, true, true]|
|B5|15|0|[false, true, true, true, true, true]|
|T1|3|1|[false, true, false, true, true, true]|
|T2|6|2|[false, true, false, true, true, true]|
|AP|7.5|2.5|[false, true, false, true, true, true]|
|T3|9|2|[false, true, false, true, true, true]|
|T4|12|1|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Input tables — Elements

|id|nodes|
|---|---|
|BC0|["B0", "B1"]|
|BC1|["B1", "B2"]|
|BC2|["B2", "B3"]|
|BC3|["B3", "B4"]|
|BC4|["B4", "B5"]|
|TC0|["B0", "T1"]|
|TC1|["T1", "T2"]|
|TC2|["T2", "AP"]|
|TC3|["AP", "T3"]|
|TC4|["T3", "T4"]|
|TC5|["T4", "B5"]|
|V1|["B1", "T1"]|
|V2|["B2", "T2"]|
|V3|["B3", "T3"]|
|V4|["B4", "T4"]|
|DG0|["B1", "T2"]|
|DG1|["B2", null]|
|DG2|["B3", "AP"]|
|DG3|["B4", "T3"]|

Applies to every listed row: type = truss; material = M1; section = A.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|steel|steel|205000|78846.15384615384|0.3|7850|

## Input tables — Sections

|id|type|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|
|A|rod|0.01|1e-05|1e-05|2e-05|

Applies to every listed row: name = id.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|fx|fz|
|---|---|---|
|roof-T1 → T1, roof-T2 → T2, roof-AP → AP, roof-T3 → T3, roof-T4 → T4|0|-10|
|apex-horizontal → AP|7|0|

Applies to every listed row: reference_frame = global; type = nodal; fy = 0; mx = 0; my = 0; mz = 0.

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
