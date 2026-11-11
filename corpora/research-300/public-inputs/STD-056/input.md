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
|roof-n0|0|0|12|false|true|false|true|false|true|
|roof-n1|12|0|12|false|true|false|true|false|true|
|roof-n2|24|0|12|false|true|false|true|false|true|
|base-L|0|0|0|true|true|true|true|true|true|
|base-R|24|0|0|true|true|true|true|true|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|roof-1|beam|roof-n0|roof-n1|M1|B1|0|[0, 1, 0]|
|roof-2|beam|roof-n1|roof-n2|M1|B1|0|[0, 1, 0]|
|column-L|column|base-L|roof-n0|M1|C1|0|[0, 1, 0]|
|column-R|column|base-R|roof-n2|M1|C1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|
|B1|400.0|1200.0|0.05759999999999999|0.006400000000000002|0.020229530864197535|
|C1|600.0|800.0|0.025600000000000008|0.014399999999999998|0.03110160937499999|

Applies to every listed row: type = rectangular; properties · A = 0.48; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|type|wz|fx|fz|
|---|---|---|---|---|
|D-1 → roof-1, D-2 → roof-2|distributed|-36|—|—|
|D-3 → roof-n2|nodal|—|10|-98|

Applies to every listed row: reference_frame = global.

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
|case-D-node-roof-n0-ux|node|roof-n0|ux|m|—|—|
|case-D-node-roof-n0-uz|node|roof-n0|uz|m|—|—|
|case-D-node-roof-n0-ry|node|roof-n0|ry|rad|—|—|
|case-D-node-roof-n1-ux|node|roof-n1|ux|m|—|—|
|case-D-node-roof-n1-uz|node|roof-n1|uz|m|—|—|
|case-D-node-roof-n1-ry|node|roof-n1|ry|rad|—|—|
|case-D-node-roof-n2-ux|node|roof-n2|ux|m|—|—|
|case-D-node-roof-n2-uz|node|roof-n2|uz|m|—|—|
|case-D-node-roof-n2-ry|node|roof-n2|ry|rad|—|—|
|case-D-node-base-L-Fx|node|base-L|Fx|kN|—|—|
|case-D-node-base-L-Fz|node|base-L|Fz|kN|—|—|
|case-D-node-base-L-My|node|base-L|My|kN.m|—|—|
|case-D-node-base-R-Fx|node|base-R|Fx|kN|—|—|
|case-D-node-base-R-Fz|node|base-R|Fz|kN|—|—|
|case-D-node-base-R-My|node|base-R|My|kN.m|—|—|
|case-D-member-column-R-s0-right-M2|member|column-R|M2|kN.m|0|right|
|case-D-member-column-R-s12-left-M2|member|column-R|M2|kN.m|12.0|left|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Input decisions

The source plan left material and section appendices unspecified. The supplied appendix freezes Q355 steel with E = 206000 MPa, nu = 0.30, G = E/[2(1+nu)] and density = 7850 kg/m^3. Sections are solid rectangles: B is the local-y width and H the local-z depth. A, Iy, Iz and J are explicitly tabulated; use these properties, with Euler-Bernoulli bending (no shear deformation). Every member uses M1. Unless a case-specific decision below states otherwise, beam B1 is 0.30 m by 0.60 m and column C1 is 0.50 m by 0.50 m. Planar local x points from the first node to the second, local y = global +Y, local z = local x cross local y. In-plane member forces are N, V3 and M2. Report in-plane translations ux and uz and rotation ry when a displacement vector is requested. Member forces are signed section resultants at the limiting cut specified in input.md. The additional midpoint nodes are connected through split members, with the same section and line-load intensity on both parts. All joints are rigid except the explicitly declared support release.

The unspecified heavy-frame sections are frozen as beam B1 = 0.40 m wide by 1.20 m deep and column C1 = 0.60 m by 0.80 m. The public section properties define the physical stiffness; these values are author-completed inputs.
Only the converted 36 kN/m roof load enters the model. Its two 12 m segments share a connected midpoint, and the 98/10 kN nodal force acts only at roof-n2.
