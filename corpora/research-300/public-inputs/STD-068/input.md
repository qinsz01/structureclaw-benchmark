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
|n0-0|0|0|-1.5|true|true|true|true|true|true|
|n1-0|6|0|-1.5|true|true|true|true|true|true|
|n0-1|0|0|0|false|true|false|true|false|true|
|n1-1|6|0|0|false|true|false|true|false|true|
|n0-2|0|0|2.1|false|true|false|true|false|true|
|n1-2|6|0|2.1|false|true|false|true|false|true|
|n0-3|0|0|5.7|false|true|false|true|false|true|
|n1-3|6|0|5.7|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|M1|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|M1|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|M1|T1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|M1|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|M1|C1|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|M1|B1|0|[0, 1, 0]|
|c0-3|column|n0-2|n0-3|M1|C1|0|[0, 1, 0]|
|c1-3|column|n1-2|n1-3|M1|C1|0|[0, 1, 0]|
|b0-3|beam|n0-3|n1-3|M1|B1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|T1|300.0|500.0|0.15|0.0031249999999999997|0.001125|0.0028173707999999994|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → b0-2, D-2 → b0-3|global|distributed|-10|

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
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|D-node-n0-1-ux|node|n0-1|ux|m|—|—|
|D-node-n0-1-uz|node|n0-1|uz|m|—|—|
|D-node-n0-1-ry|node|n0-1|ry|rad|—|—|
|D-node-n1-1-ux|node|n1-1|ux|m|—|—|
|D-node-n1-1-uz|node|n1-1|uz|m|—|—|
|D-node-n1-1-ry|node|n1-1|ry|rad|—|—|
|D-node-n0-2-ux|node|n0-2|ux|m|—|—|
|D-node-n0-2-uz|node|n0-2|uz|m|—|—|
|D-node-n0-2-ry|node|n0-2|ry|rad|—|—|
|D-node-n1-2-ux|node|n1-2|ux|m|—|—|
|D-node-n1-2-uz|node|n1-2|uz|m|—|—|
|D-node-n1-2-ry|node|n1-2|ry|rad|—|—|
|D-node-n0-3-ux|node|n0-3|ux|m|—|—|
|D-node-n0-3-uz|node|n0-3|uz|m|—|—|
|D-node-n0-3-ry|node|n0-3|ry|rad|—|—|
|D-node-n1-3-ux|node|n1-3|ux|m|—|—|
|D-node-n1-3-uz|node|n1-3|uz|m|—|—|
|D-node-n1-3-ry|node|n1-3|ry|rad|—|—|
|D-node-n0-0-ux|node|n0-0|ux|m|—|—|
|D-node-n0-0-uz|node|n0-0|uz|m|—|—|
|D-node-n1-0-ux|node|n1-0|ux|m|—|—|
|D-node-n1-0-uz|node|n1-0|uz|m|—|—|
|D-member-b0-1-i-N|member|b0-1|N|kN|0|right|
|D-member-b0-1-i-V3|member|b0-1|V3|kN|0|right|
|D-member-b0-1-i-M2|member|b0-1|M2|kN.m|0|right|
|D-member-b0-1-j-N|member|b0-1|N|kN|6.0|left|
|D-member-b0-1-j-V3|member|b0-1|V3|kN|6.0|left|
|D-member-b0-1-j-M2|member|b0-1|M2|kN.m|6.0|left|
|D-node-n0-0-Fx|node|n0-0|Fx|kN|—|—|
|D-node-n0-0-Fz|node|n0-0|Fz|kN|—|—|
|D-node-n0-0-My|node|n0-0|My|kN.m|—|—|
|D-node-n1-0-Fx|node|n1-0|Fx|kN|—|—|
|D-node-n1-0-Fz|node|n1-0|Fz|kN|—|—|
|D-node-n1-0-My|node|n1-0|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|D-difference-n0-1-minus-n0-0-ux|["D-node-n0-1-ux", "D-node-n0-0-ux"]|n0-1.ux - n0-0.ux; upper minus lower, no division by story height|
|D-difference-n0-1-minus-n0-0-uz|["D-node-n0-1-uz", "D-node-n0-0-uz"]|n0-1.uz - n0-0.uz; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-ux|["D-node-n1-1-ux", "D-node-n1-0-ux"]|n1-1.ux - n1-0.ux; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-uz|["D-node-n1-1-uz", "D-node-n1-0-uz"]|n1-1.uz - n1-0.uz; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-ux|["D-node-n0-2-ux", "D-node-n0-1-ux"]|n0-2.ux - n0-1.ux; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-uz|["D-node-n0-2-uz", "D-node-n0-1-uz"]|n0-2.uz - n0-1.uz; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-ux|["D-node-n1-2-ux", "D-node-n1-1-ux"]|n1-2.ux - n1-1.ux; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-uz|["D-node-n1-2-uz", "D-node-n1-1-uz"]|n1-2.uz - n1-1.uz; upper minus lower, no division by story height|
|D-difference-n0-3-minus-n0-2-ux|["D-node-n0-3-ux", "D-node-n0-2-ux"]|n0-3.ux - n0-2.ux; upper minus lower, no division by story height|
|D-difference-n0-3-minus-n0-2-uz|["D-node-n0-3-uz", "D-node-n0-2-uz"]|n0-3.uz - n0-2.uz; upper minus lower, no division by story height|
|D-difference-n1-3-minus-n1-2-ux|["D-node-n1-3-ux", "D-node-n1-2-ux"]|n1-3.ux - n1-2.ux; upper minus lower, no division by story height|
|D-difference-n1-3-minus-n1-2-uz|["D-node-n1-3-uz", "D-node-n1-2-uz"]|n1-3.uz - n1-2.uz; upper minus lower, no division by story height|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Output scope — Required outputs

|id|description|quantityIds|kind|
|---|---|---|---|
|joint-displacements|Global ux, uz and ry at both ground tie-beam joints and all four upper-floor joints|["D-node-n0-1-ux", "D-node-n0-1-uz", "D-node-n0-1-ry", "D-node-n1-1-ux", "D-node-n1-1-uz", "D-node-n1-1-ry", "D-node-n0-2-ux", "D-node-n0-2-uz", "D-node-n0-2-ry", "D-node-n1-2-ux", "D-node-n1-2-uz", "D-node-n1-2-ry", "D-node-n0-3-ux", "D-node-n0-3-uz", "D-node-n0-3-ry", "D-node-n1-3-ux", "D-node-n1-3-uz", "D-node-n1-3-ry"]|numerical|
|column-displacement-differences|Upper-minus-lower Δux and Δuz of every actual column segment: -1.5 to 0, 0 to 2.1, and 2.1 to 5.7 m, separately on both lines|["D-difference-n0-1-minus-n0-0-ux", "D-difference-n0-1-minus-n0-0-uz", "D-difference-n1-1-minus-n1-0-ux", "D-difference-n1-1-minus-n1-0-uz", "D-difference-n0-2-minus-n0-1-ux", "D-difference-n0-2-minus-n0-1-uz", "D-difference-n1-2-minus-n1-1-ux", "D-difference-n1-2-minus-n1-1-uz", "D-difference-n0-3-minus-n0-2-ux", "D-difference-n0-3-minus-n0-2-uz", "D-difference-n1-3-minus-n1-2-ux", "D-difference-n1-3-minus-n1-2-uz"]|derived|
|member-end-forces|Local N, V3 and M2 at both ends of the unloaded ground tie beam b0-1|["D-member-b0-1-i-N", "D-member-b0-1-i-V3", "D-member-b0-1-i-M2", "D-member-b0-1-j-N", "D-member-b0-1-j-V3", "D-member-b0-1-j-M2"]|numerical|
|base-reactions|Global Fx, Fz and My at both fixed bases at z=-1.5 m|["D-node-n0-0-Fx", "D-node-n0-0-Fz", "D-node-n0-0-My", "D-node-n1-0-Fx", "D-node-n1-0-Fz", "D-node-n1-0-My"]|numerical|

Applies to every listed row: state = 1.

## Physical definitions

The appendix supplies Q355 material, C1 column, B1 floor-beam and T1 ground tie-beam properties; T1 is an explicitly completed 300x500 mm idealized rectangle.
The absolute elevations are retained. The six actual column segments have heights 1.5, 2.1 and 3.6 m on the two column lines.
Ground nodes have only the planar out-of-plane constraints, with ux/uz/ry free. The tie beam has no external load and creates no ground support.
Frame members use linear elastic Euler-Bernoulli bending and axial deformation. No shear deformation, end releases, member mass or additional loads are introduced. Beam/column joints and supports follow the explicit input table.
The supplied torsion constant J is the frozen rectangular-section approximation in input.md. Use the numerical A, Iy, Iz and J values supplied, with local y and z as stated in input.md.
