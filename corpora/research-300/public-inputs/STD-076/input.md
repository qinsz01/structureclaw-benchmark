## Numerical inputs

|Field|Value|
|---|---|
|title|Complete numerical input appendix|
|linearCombinations|[]|
|floorTable|[]|

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
|n1-0|5|0|0|true|true|true|true|true|true|
|n2-0|12|0|0|true|true|true|true|true|true|
|n0-1|0|0|3.6|false|true|false|true|false|true|
|n1-1|5|0|3.6|false|true|false|true|false|true|
|n2-1|12|0|3.6|false|true|false|true|false|true|
|n0-2|0|0|7.2|false|true|false|true|false|true|
|n1-2|5|0|7.2|false|true|false|true|false|true|
|n2-2|12|0|7.2|false|true|false|true|false|true|
|mid-b0-1|2.5|0|3.6|false|true|false|true|false|true|
|mid-b1-1|8.5|0|3.6|false|true|false|true|false|true|
|mid-b0-2|2.5|0|7.2|false|true|false|true|false|true|
|mid-b1-2|8.5|0|7.2|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|C30|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|C30|C1|0|[0, 1, 0]|
|c2-1|column|n2-0|n2-1|C30|C1|0|[0, 1, 0]|
|b0-1-a|beam|n0-1|mid-b0-1|C30|B1|0|[0, 1, 0]|
|b0-1-b|beam|mid-b0-1|n1-1|C30|B1|0|[0, 1, 0]|
|b1-1-a|beam|n1-1|mid-b1-1|C30|B1|0|[0, 1, 0]|
|b1-1-b|beam|mid-b1-1|n2-1|C30|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|C30|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|C30|C1|0|[0, 1, 0]|
|c2-2|column|n2-1|n2-2|C30|C1|0|[0, 1, 0]|
|b0-2-a|beam|n0-2|mid-b0-2|C30|B1|0|[0, 1, 0]|
|b0-2-b|beam|mid-b0-2|n1-2|C30|B1|0|[0, 1, 0]|
|b1-2-a|beam|n1-2|mid-b1-2|C30|B1|0|[0, 1, 0]|
|b1-2-b|beam|mid-b1-2|n2-2|C30|B1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|type|E|G|nu|rho|
|---|---|---|---|---|---|
|C30|concrete|30000|12500.0|0.2|2500|

Applies to every listed row: name = id.

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

|Load ID → element / node|wz|
|---|---|
|D-1 → b0-1-a, D-2 → b0-1-b, D-5 → b0-2-a, D-6 → b0-2-b|-40|
|D-3 → b1-1-a, D-4 → b1-1-b, D-7 → b1-2-a, D-8 → b1-2-b|-60|

Applies to every listed row: reference_frame = global; type = distributed.

## Numerical inputs — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Numerical inputs — Continuity notes — Physical beams — B0 1

|Field|Value|
|---|---|
|nodes|["n0-1", "n1-1"]|
|segments|["b0-1-a", "b0-1-b"]|
|midpointNode|mid-b0-1|
|joint|continuous-rigid|
|addedMass|0|

## Numerical inputs — Continuity notes — Physical beams — B1 1

|Field|Value|
|---|---|
|nodes|["n1-1", "n2-1"]|
|segments|["b1-1-a", "b1-1-b"]|
|midpointNode|mid-b1-1|
|joint|continuous-rigid|
|addedMass|0|

## Numerical inputs — Continuity notes — Physical beams — B0 2

|Field|Value|
|---|---|
|nodes|["n0-2", "n1-2"]|
|segments|["b0-2-a", "b0-2-b"]|
|midpointNode|mid-b0-2|
|joint|continuous-rigid|
|addedMass|0|

## Numerical inputs — Continuity notes — Physical beams — B1 2

|Field|Value|
|---|---|
|nodes|["n1-2", "n2-2"]|
|segments|["b1-2-a", "b1-2-b"]|
|midpointNode|mid-b1-2|
|joint|continuous-rigid|
|addedMass|0|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · id|component|unit|
|---|---|---|---|
|case-D-node-n0-1-ux|n0-1|ux|m|
|case-D-node-n0-1-uz|n0-1|uz|m|
|case-D-node-n0-1-ry|n0-1|ry|rad|
|case-D-node-n1-1-ux|n1-1|ux|m|
|case-D-node-n1-1-uz|n1-1|uz|m|
|case-D-node-n1-1-ry|n1-1|ry|rad|
|case-D-node-n2-1-ux|n2-1|ux|m|
|case-D-node-n2-1-uz|n2-1|uz|m|
|case-D-node-n2-1-ry|n2-1|ry|rad|
|case-D-node-n0-2-ux|n0-2|ux|m|
|case-D-node-n0-2-uz|n0-2|uz|m|
|case-D-node-n0-2-ry|n0-2|ry|rad|
|case-D-node-n1-2-ux|n1-2|ux|m|
|case-D-node-n1-2-uz|n1-2|uz|m|
|case-D-node-n1-2-ry|n1-2|ry|rad|
|case-D-node-n2-2-ux|n2-2|ux|m|
|case-D-node-n2-2-uz|n2-2|uz|m|
|case-D-node-n2-2-ry|n2-2|ry|rad|
|case-D-node-mid-b0-1-ux|mid-b0-1|ux|m|
|case-D-node-mid-b0-1-uz|mid-b0-1|uz|m|
|case-D-node-mid-b0-1-ry|mid-b0-1|ry|rad|
|case-D-node-mid-b1-1-ux|mid-b1-1|ux|m|
|case-D-node-mid-b1-1-uz|mid-b1-1|uz|m|
|case-D-node-mid-b1-1-ry|mid-b1-1|ry|rad|
|case-D-node-mid-b0-2-ux|mid-b0-2|ux|m|
|case-D-node-mid-b0-2-uz|mid-b0-2|uz|m|
|case-D-node-mid-b0-2-ry|mid-b0-2|ry|rad|
|case-D-node-mid-b1-2-ux|mid-b1-2|ux|m|
|case-D-node-mid-b1-2-uz|mid-b1-2|uz|m|
|case-D-node-mid-b1-2-ry|mid-b1-2|ry|rad|
|case-D-node-n0-0-Fx|n0-0|Fx|kN|
|case-D-node-n0-0-Fz|n0-0|Fz|kN|
|case-D-node-n0-0-My|n0-0|My|kN.m|
|case-D-node-n1-0-Fx|n1-0|Fx|kN|
|case-D-node-n1-0-Fz|n1-0|Fz|kN|
|case-D-node-n1-0-My|n1-0|My|kN.m|
|case-D-node-n2-0-Fx|n2-0|Fx|kN|
|case-D-node-n2-0-Fz|n2-0|Fz|kN|
|case-D-node-n2-0-My|n2-0|My|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.
