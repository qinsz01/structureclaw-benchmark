## Table a

Input tables. X horizontal, Z upward; Y completes the right-handed system. Section shape dimensions B,H are mm; listed section properties are authoritative. Coordinates m; nodal forces kN; nodal moments kN*m; line loads kN/m; E,G MPa; A m2; Iy,Iz,J m4; density kg/m3. Restraints ordered ux,uy,uz,rx,ry,rz; true=fixed. Member local x follows the ordered end nodes. For planar XZ members local y is global +Y and local z=x cross y; bending about local y uses Iy. For spatial members the explicit reference vector defines local z by its projection normal to local x, local y=z cross x. Linear elastic first-order static analysis, self-weight OFF, no automatic loads/combinations, diaphragm, rigid offsets or P-delta. Distributed load intervals are measured in m along the actual member unless this turn explicitly leaves that basis unresolved. All omitted load components are zero. Beam-column joints are rigid unless explicitly restrained; truss elements are axial-only. Truss rotational restraints eliminate inactive bookkeeping DOFs and do not add rotational stiffness. Use OpenSees for every calculable state; rerun after a physical edit, and reuse a result for a pure query only when its state is unchanged. Retain solver version/settings, successful log, model snapshot and raw result mapping.

## Table a

|Field|Value|
|---|---|
|schema_version|2.2.0|
|unit_system|SI|
|load_combinations|[]|

## Table a — Coordinate system

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Table a — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|A0|0|0|0|[true, true, true, true, true, true]|
|B0|4|0|0|[true, true, true, true, true, true]|
|C0|2|3.4641016151377544|0|[true, true, true, true, true, true]|
|A1|0|0|3|[false, false, false, true, true, true]|
|B1|4|0|3|[false, false, false, true, true, true]|
|C1|2|3.4641016151377544|3|[false, false, false, true, true, true]|
|A2|0|0|6|[false, false, false, true, true, true]|
|B2|4|0|6|[false, false, false, true, true, true]|
|C2|2|3.4641016151377544|6|[false, false, false, true, true, true]|

## Table a — Elements

|id|nodes|section|
|---|---|---|
|hAB0|["A0", "B0"]|A1|
|hBC0|["B0", "C0"]|A1|
|hCA0|["C0", "A0"]|A1|
|hAB1|["A1", "B1"]|A1|
|hBC1|["B1", "C1"]|A1|
|hCA1|["C1", "A1"]|A1|
|hAB2|["A2", "B2"]|A1|
|hBC2|["B2", "C2"]|A1|
|hCA2|["C2", "A2"]|A1|
|vA1|["A0", "A1"]|A2|
|vB1|["B0", "B1"]|A2|
|vC1|["C0", "C1"]|A2|
|dAB1|["A0", "B1"]|A1|
|dBC1|["B0", "C1"]|A1|
|dCA1|["C0", "A1"]|A1|
|vA2|["A1", "A2"]|A1|
|vB2|["B1", "B2"]|A1|
|vC2|["C1", "C2"]|A1|
|dAB2|["A1", "B2"]|A1|
|dBC2|["B1", "C2"]|A1|
|dCA2|["C1", "A2"]|A1|

Applies to every listed row: type = truss; material = M1.

## Table a — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Table a — Sections

|id|properties · A|
|---|---|
|A1|0.01|
|A2|0.02|

Applies to every listed row: type = general; properties · Iy = 1e-05; properties · Iz = 1e-05; properties · J = 2e-05; name = id.

## Table a — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Table a — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|
|---|---|---|---|
|D-1 → A2, D-2 → B2, D-3 → C2|global|nodal|10|

## Table a — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Table a — Metadata — Element reference vectors

|Field|Value|
|---|---|
|hAB0|[0, 0, 1]|
|hBC0|[0, 0, 1]|
|hCA0|[0, 0, 1]|
|hAB1|[0, 0, 1]|
|hBC1|[0, 0, 1]|
|hCA1|[0, 0, 1]|
|hAB2|[0, 0, 1]|
|hBC2|[0, 0, 1]|
|hCA2|[0, 0, 1]|
|vA1|[1, 0, 0]|
|vB1|[1, 0, 0]|
|vC1|[1, 0, 0]|
|dAB1|[0, 0, 1]|
|dBC1|[0, 0, 1]|
|dCA1|[0, 0, 1]|
|vA2|[1, 0, 0]|
|vB2|[1, 0, 0]|
|vC2|[1, 0, 0]|
|dAB2|[0, 0, 1]|
|dBC2|[0, 0, 1]|
|dCA2|[0, 0, 1]|
