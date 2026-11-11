## Input tables

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.
Every diagonal is a two-end axial-only element. Crossings are not connections. Only internal top nodes T1,T2,T3 carry 10 kN downward each; T0 and T4 have no load.

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
|T0|0|2.5|[false, true, false, true, true, true]|
|B1|3|0|[false, true, false, true, true, true]|
|T1|3|2.5|[false, true, false, true, true, true]|
|B2|6|0|[false, true, false, true, true, true]|
|T2|6|2.5|[false, true, false, true, true, true]|
|B3|9|0|[false, true, false, true, true, true]|
|T3|9|2.5|[false, true, false, true, true, true]|
|B4|12|0|[false, true, true, true, true, true]|
|T4|12|2.5|[false, true, false, true, true, true]|

Applies to every listed row: y = 0.

## Input tables — Elements

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
|V0|["B0", "T0"]|A|
|V1|["B1", "T1"]|A|
|V2|["B2", "T2"]|A|
|V3|["B3", "T3"]|A|
|V4|["B4", "T4"]|A|
|UP0|["B0", "T1"]|A|
|DOWN0|["T0", "B1"]|DOWN|
|UP1|["B1", "T2"]|A|
|DOWN1|["T1", "B2"]|DOWN|
|UP2|["B2", "T3"]|A|
|DOWN2|["T2", "B3"]|DOWN|
|UP3|["B3", "T4"]|A|
|DOWN3|["T3", "B4"]|DOWN|

Applies to every listed row: type = truss; material = M1.

## Input tables — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|steel|steel|205000|78846.15384615384|0.3|7850|

## Input tables — Sections

|id|properties · A|
|---|---|
|A|0.01|
|DOWN|0.015|

Applies to every listed row: type = rod; properties · Iy = 1e-05; properties · Iz = 1e-05; properties · J = 2e-05; name = id.

## Input tables — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input tables — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fy|fz|mx|my|mz|
|---|---|---|---|---|---|---|---|---|
|top-1 → T1, top-2 → T2, top-3 → T3|global|nodal|0|0|-10|0|0|0|

## Input tables — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
