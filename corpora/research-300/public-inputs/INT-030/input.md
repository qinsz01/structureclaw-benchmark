## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
The table lists V0 through V6, while the accompanying text says no verticals; the precedence of those conflicting statements is unresolved.

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
|T0|0|2|[false, true, false, true, true, true]|
|B1|2|0|[false, true, false, true, true, true]|
|T1|2|2|[false, true, false, true, true, true]|
|B2|4|0|[false, true, false, true, true, true]|
|T2|4|2|[false, true, false, true, true, true]|
|B3|6|0|[false, true, false, true, true, true]|
|T3|6|2|[false, true, false, true, true, true]|
|B4|8|0|[false, true, false, true, true, true]|
|T4|8|2|[false, true, false, true, true, true]|
|B5|10|0|[false, true, false, true, true, true]|
|T5|10|2|[false, true, false, true, true, true]|
|B6|12|0|[false, true, true, true, true, true]|
|T6|12|2|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Input tables — Elements

|id|nodes|
|---|---|
|BC0|["B0", "B1"]|
|TC0|["T0", "T1"]|
|BC1|["B1", "B2"]|
|TC1|["T1", "T2"]|
|BC2|["B2", "B3"]|
|TC2|["T2", "T3"]|
|BC3|["B3", "B4"]|
|TC3|["T3", "T4"]|
|BC4|["B4", "B5"]|
|TC4|["T4", "T5"]|
|BC5|["B5", "B6"]|
|TC5|["T5", "T6"]|
|V0|["B0", "T0"]|
|V1|["B1", "T1"]|
|V2|["B2", "T2"]|
|V3|["B3", "T3"]|
|V4|["B4", "T4"]|
|V5|["B5", "T5"]|
|V6|["B6", "T6"]|
|DG0|["B0", "T1"]|
|DG1|["T1", "B2"]|
|DG2|["B2", "T3"]|
|DG3|["T3", "B4"]|
|DG4|["B4", "T5"]|
|DG5|["T5", "B6"]|

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

|Load ID → element / node|fz|
|---|---|
|bottom-1 → B1, bottom-2 → B2, bottom-3 → B3, bottom-4 → B4, bottom-5 → B5|-8|
|additional-top → T3|-11|

Applies to every listed row: reference_frame = global; type = nodal; fx = 0; fy = 0; mx = 0; my = 0; mz = 0.

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
