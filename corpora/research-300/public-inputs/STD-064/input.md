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
|n0-1|0|0|3.6|false|true|false|true|false|true|
|n1-1|6|0|3.6|false|true|false|true|false|true|
|n0-2|0|0|7.2|false|true|false|true|false|true|
|n1-2|6|0|7.2|false|true|false|true|false|true|
|tip-1|7.5|0|3.6|false|true|false|true|false|true|
|tip-2|7.5|0|7.2|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|M1|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|M1|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|M1|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|M1|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|M1|C1|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|M1|B1|0|[0, 1, 0]|
|overhang-1|beam|n1-1|tip-1|M1|B1|0|[0, 1, 0]|
|overhang-2|beam|n1-2|tip-2|M1|B1|0|[0, 1, 0]|

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

|Load ID → element / node|wz|
|---|---|
|D-1 → b0-1, D-3 → b0-2|-10|
|D-2 → overhang-1, D-4 → overhang-2|-5|

Applies to every listed row: reference_frame = global; type = distributed.

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
|D-node-tip-1-uz|node|tip-1|uz|m|—|—|
|D-node-tip-2-uz|node|tip-2|uz|m|—|—|
|D-member-overhang-1-i-M2|member|overhang-1|M2|kN.m|0|right|
|D-member-overhang-2-i-M2|member|overhang-2|M2|kN.m|0|right|
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
|D-node-n0-0-Fx|node|n0-0|Fx|kN|—|—|
|D-node-n0-0-Fz|node|n0-0|Fz|kN|—|—|
|D-node-n0-0-My|node|n0-0|My|kN.m|—|—|
|D-node-n1-0-Fx|node|n1-0|Fx|kN|—|—|
|D-node-n1-0-Fz|node|n1-0|Fz|kN|—|—|
|D-node-n1-0-My|node|n1-0|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Output scope — Required outputs

|id|description|quantityIds|
|---|---|---|
|cantilever-tip-displacements|Vertical uz at the free end of each 1.5 m overhang|["D-node-tip-1-uz", "D-node-tip-2-uz"]|
|cantilever-root-moments|Local M2 at the overhang side of both rigid roots|["D-member-overhang-1-i-M2", "D-member-overhang-2-i-M2"]|
|joint-displacements|Global ux, uz and ry at the left and right column tops on both floors|["D-node-n0-1-ux", "D-node-n0-1-uz", "D-node-n0-1-ry", "D-node-n1-1-ux", "D-node-n1-1-uz", "D-node-n1-1-ry", "D-node-n0-2-ux", "D-node-n0-2-uz", "D-node-n0-2-ry", "D-node-n1-2-ux", "D-node-n1-2-uz", "D-node-n1-2-ry"]|
|base-reactions|Global Fx, Fz and My at both fixed column bases|["D-node-n0-0-Fx", "D-node-n0-0-Fz", "D-node-n0-0-My", "D-node-n1-0-Fx", "D-node-n1-0-Fz", "D-node-n1-0-My"]|

Applies to every listed row: state = 1; kind = numerical.

## Physical definitions

The appendix supplies Q355 material and explicit B1 beam/overhang and C1 column properties.
Root moment means the local M2 section force on the overhang side at position 0 m, side right; each overhang is rigidly connected to its own floor joint.
The 10 and 5 kN/m loads are applied once to their respective 6 m and 1.5 m member regions.
Frame members use linear elastic Euler-Bernoulli bending and axial deformation. No shear deformation, end releases, member mass or additional loads are introduced. Beam/column joints and supports follow the explicit input table.
The supplied torsion constant J is the frozen rectangular-section approximation in input.md. Use the numerical A, Iy, Iz and J values supplied, with local y and z as stated in input.md.
