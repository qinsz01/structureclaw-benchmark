## Numerical inputs

|Field|Value|
|---|---|
|title|Complete numerical input appendix|
|linearCombinations|[]|
|floorTable|[]|
|continuityNotes|{}|

## Numerical inputs — Units

|Field|Value|
|---|---|
|coordinates|m|
|forces|kN|
|moments|kN.m|
|lineLoads|kN/m|
|E|MPa|
|G|MPa|
|density|kg/m^3|
|A|m^2|
|Iy|m^4|
|Iz|m^4|
|J|m^4|
|shapeDimensions|mm|
|rotations|rad|
|sectionRoll|degree|

## Numerical inputs — Coordinate convention

|Field|Value|
|---|---|
|dimension|2d|
|plane|xz|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Numerical inputs — Nodes

|id|X_m|Y_m|Z_m|fixed_ux|fixed_uy|fixed_uz|fixed_rx|fixed_ry|fixed_rz|
|---|---|---|---|---|---|---|---|---|---|
|n0-0|0|0|0|true|true|true|true|true|true|
|n1-0|6|0|0|true|true|true|true|true|true|
|n0-1|0|0|4|false|true|false|true|false|true|
|n1-1|6|0|4|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|M1|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|M1|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|M1|B1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|
|---|---|---|---|
|D-1 → n1-1|global|nodal|50|

## Numerical inputs — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-n0-1-ux|node|n0-1|ux|m|—|—|
|case-D-node-n1-1-ux|node|n1-1|ux|m|—|—|
|case-D-member-b0-1-s0-right-N|member|b0-1|N|kN|0|right|
|case-D-member-b0-1-s0-right-V3|member|b0-1|V3|kN|0|right|
|case-D-member-b0-1-s0-right-M2|member|b0-1|M2|kN.m|0|right|
|case-D-member-b0-1-s6-left-N|member|b0-1|N|kN|6.0|left|
|case-D-member-b0-1-s6-left-V3|member|b0-1|V3|kN|6.0|left|
|case-D-member-b0-1-s6-left-M2|member|b0-1|M2|kN.m|6.0|left|
|case-D-node-n0-0-Fx|node|n0-0|Fx|kN|—|—|
|case-D-node-n0-0-My|node|n0-0|My|kN.m|—|—|
|case-D-node-n1-0-Fx|node|n1-0|Fx|kN|—|—|
|case-D-node-n1-0-My|node|n1-0|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Input decisions

The source plan left material and section appendices unspecified. The supplied appendix freezes Q355 steel with E = 206000 MPa, nu = 0.30, G = E/[2(1+nu)] and density = 7850 kg/m^3. Sections are solid rectangles: B is the local-y width and H the local-z depth. A, Iy, Iz and J are explicitly tabulated; use these properties, with Euler-Bernoulli bending (no shear deformation). Every member uses M1. Unless a case-specific decision below states otherwise, beam B1 is 0.30 m by 0.60 m and column C1 is 0.50 m by 0.50 m. Planar local x points from the first node to the second, local y = global +Y, local z = local x cross local y. In-plane member forces are N, V3 and M2. Report in-plane translations ux and uz and rotation ry when a displacement vector is requested. Member forces are signed section resultants at the limiting cut specified in input.md. The additional midpoint nodes are connected through split members, with the same section and line-load intensity on both parts. All joints are rigid except the explicitly declared support release.

Beam B1 is 0.30 m by 0.60 m and columns C1 are 0.50 m square. The single static case is named D as a case label even though its only load is lateral. There is no gravitational load or roof diaphragm.
