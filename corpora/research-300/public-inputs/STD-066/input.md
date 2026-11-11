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
|n2-0|12|0|0|true|true|true|true|true|true|
|n0-1|0|0|3.6|false|true|false|true|false|true|
|n1-1|6|0|3.6|false|true|false|true|false|true|
|n2-1|12|0|3.6|false|true|false|true|false|true|
|n0-2|0|0|7.2|false|true|false|true|false|true|
|n1-2|6|0|7.2|false|true|false|true|false|true|
|n2-2|12|0|7.2|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|M1|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|M1|C2|0|[0, 1, 0]|
|c2-1|column|n2-0|n2-1|M1|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|M1|B1|0|[0, 1, 0]|
|b1-1|beam|n1-1|n2-1|M1|B2|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|M1|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|M1|C2|0|[0, 1, 0]|
|c2-2|column|n2-1|n2-2|M1|C1|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|M1|B1|0|[0, 1, 0]|
|b1-2|beam|n1-2|n2-2|M1|B2|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|C1|500.0|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|C2|350.0|500.0|0.175|0.003645833333333333|0.0017864583333333328|0.0040575733442708315|
|B2|300.0|700.0|0.21|0.008574999999999998|0.0015749999999999998|0.004603782069970844|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|type|wz|fx|
|---|---|---|---|
|D-1 → b0-1, D-2 → b1-1, D-3 → b0-2, D-4 → b1-2|distributed|-8|—|
|D-5 → n2-2|nodal|—|25|

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
|figures|[]|
|interactions|["Return the complete member-to-section schedule, preserving exterior C1, interior C2, left-bay B1 and right-bay B2 on both stories"]|

## Requested outputs — Quantities

|id|location · kind|location · id|location · positionM|location · side|component|unit|
|---|---|---|---|---|---|---|
|D-member-c0-1-i-N|member|c0-1|0|right|N|kN|
|D-member-c0-1-i-V3|member|c0-1|0|right|V3|kN|
|D-member-c0-1-i-M2|member|c0-1|0|right|M2|kN.m|
|D-member-c0-1-j-N|member|c0-1|3.6|left|N|kN|
|D-member-c0-1-j-V3|member|c0-1|3.6|left|V3|kN|
|D-member-c0-1-j-M2|member|c0-1|3.6|left|M2|kN.m|
|D-member-c1-1-i-N|member|c1-1|0|right|N|kN|
|D-member-c1-1-i-V3|member|c1-1|0|right|V3|kN|
|D-member-c1-1-i-M2|member|c1-1|0|right|M2|kN.m|
|D-member-c1-1-j-N|member|c1-1|3.6|left|N|kN|
|D-member-c1-1-j-V3|member|c1-1|3.6|left|V3|kN|
|D-member-c1-1-j-M2|member|c1-1|3.6|left|M2|kN.m|
|D-member-b0-1-i-N|member|b0-1|0|right|N|kN|
|D-member-b0-1-i-V3|member|b0-1|0|right|V3|kN|
|D-member-b0-1-i-M2|member|b0-1|0|right|M2|kN.m|
|D-member-b0-1-j-N|member|b0-1|6.0|left|N|kN|
|D-member-b0-1-j-V3|member|b0-1|6.0|left|V3|kN|
|D-member-b0-1-j-M2|member|b0-1|6.0|left|M2|kN.m|
|D-member-b1-1-i-N|member|b1-1|0|right|N|kN|
|D-member-b1-1-i-V3|member|b1-1|0|right|V3|kN|
|D-member-b1-1-i-M2|member|b1-1|0|right|M2|kN.m|
|D-member-b1-1-j-N|member|b1-1|6.0|left|N|kN|
|D-member-b1-1-j-V3|member|b1-1|6.0|left|V3|kN|
|D-member-b1-1-j-M2|member|b1-1|6.0|left|M2|kN.m|
|D-node-n0-1-ux|node|n0-1|—|—|ux|m|
|D-node-n0-0-ux|node|n0-0|—|—|ux|m|
|D-node-n0-1-uz|node|n0-1|—|—|uz|m|
|D-node-n0-0-uz|node|n0-0|—|—|uz|m|
|D-node-n1-1-ux|node|n1-1|—|—|ux|m|
|D-node-n1-0-ux|node|n1-0|—|—|ux|m|
|D-node-n1-1-uz|node|n1-1|—|—|uz|m|
|D-node-n1-0-uz|node|n1-0|—|—|uz|m|
|D-node-n2-1-ux|node|n2-1|—|—|ux|m|
|D-node-n2-0-ux|node|n2-0|—|—|ux|m|
|D-node-n2-1-uz|node|n2-1|—|—|uz|m|
|D-node-n2-0-uz|node|n2-0|—|—|uz|m|
|D-node-n0-2-ux|node|n0-2|—|—|ux|m|
|D-node-n0-2-uz|node|n0-2|—|—|uz|m|
|D-node-n1-2-ux|node|n1-2|—|—|ux|m|
|D-node-n1-2-uz|node|n1-2|—|—|uz|m|
|D-node-n2-2-ux|node|n2-2|—|—|ux|m|
|D-node-n2-2-uz|node|n2-2|—|—|uz|m|
|D-node-n0-0-Fx|node|n0-0|—|—|Fx|kN|
|D-node-n0-0-Fz|node|n0-0|—|—|Fz|kN|
|D-node-n0-0-My|node|n0-0|—|—|My|kN.m|
|D-node-n1-0-Fx|node|n1-0|—|—|Fx|kN|
|D-node-n1-0-Fz|node|n1-0|—|—|Fz|kN|
|D-node-n1-0-My|node|n1-0|—|—|My|kN.m|
|D-node-n2-0-Fx|node|n2-0|—|—|Fx|kN|
|D-node-n2-0-Fz|node|n2-0|—|—|Fz|kN|
|D-node-n2-0-My|node|n2-0|—|—|My|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|D-difference-n0-1-minus-n0-0-ux|["D-node-n0-1-ux", "D-node-n0-0-ux"]|n0-1.ux - n0-0.ux; upper minus lower, no division by story height|
|D-difference-n0-1-minus-n0-0-uz|["D-node-n0-1-uz", "D-node-n0-0-uz"]|n0-1.uz - n0-0.uz; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-ux|["D-node-n1-1-ux", "D-node-n1-0-ux"]|n1-1.ux - n1-0.ux; upper minus lower, no division by story height|
|D-difference-n1-1-minus-n1-0-uz|["D-node-n1-1-uz", "D-node-n1-0-uz"]|n1-1.uz - n1-0.uz; upper minus lower, no division by story height|
|D-difference-n2-1-minus-n2-0-ux|["D-node-n2-1-ux", "D-node-n2-0-ux"]|n2-1.ux - n2-0.ux; upper minus lower, no division by story height|
|D-difference-n2-1-minus-n2-0-uz|["D-node-n2-1-uz", "D-node-n2-0-uz"]|n2-1.uz - n2-0.uz; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-ux|["D-node-n0-2-ux", "D-node-n0-1-ux"]|n0-2.ux - n0-1.ux; upper minus lower, no division by story height|
|D-difference-n0-2-minus-n0-1-uz|["D-node-n0-2-uz", "D-node-n0-1-uz"]|n0-2.uz - n0-1.uz; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-ux|["D-node-n1-2-ux", "D-node-n1-1-ux"]|n1-2.ux - n1-1.ux; upper minus lower, no division by story height|
|D-difference-n1-2-minus-n1-1-uz|["D-node-n1-2-uz", "D-node-n1-1-uz"]|n1-2.uz - n1-1.uz; upper minus lower, no division by story height|
|D-difference-n2-2-minus-n2-1-ux|["D-node-n2-2-ux", "D-node-n2-1-ux"]|n2-2.ux - n2-1.ux; upper minus lower, no division by story height|
|D-difference-n2-2-minus-n2-1-uz|["D-node-n2-2-uz", "D-node-n2-1-uz"]|n2-2.uz - n2-1.uz; upper minus lower, no division by story height|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Output scope — Required outputs

|id|description|quantityIds|kind|
|---|---|---|---|
|member-end-forces|Both-end N, V3 and M2 of group representatives c0-1 (C1), c1-1 (C2), b0-1 (B1), and b1-1 (B2)|["D-member-c0-1-i-N", "D-member-c0-1-i-V3", "D-member-c0-1-i-M2", "D-member-c0-1-j-N", "D-member-c0-1-j-V3", "D-member-c0-1-j-M2", "D-member-c1-1-i-N", "D-member-c1-1-i-V3", "D-member-c1-1-i-M2", "D-member-c1-1-j-N", "D-member-c1-1-j-V3", "D-member-c1-1-j-M2", "D-member-b0-1-i-N", "D-member-b0-1-i-V3", "D-member-b0-1-i-M2", "D-member-b0-1-j-N", "D-member-b0-1-j-V3", "D-member-b0-1-j-M2", "D-member-b1-1-i-N", "D-member-b1-1-i-V3", "D-member-b1-1-i-M2", "D-member-b1-1-j-N", "D-member-b1-1-j-V3", "D-member-b1-1-j-M2"]|numerical|
|column-displacement-differences|Upper-minus-lower Δux and Δuz along each of the three column lines at both stories|["D-difference-n0-1-minus-n0-0-ux", "D-difference-n0-1-minus-n0-0-uz", "D-difference-n1-1-minus-n1-0-ux", "D-difference-n1-1-minus-n1-0-uz", "D-difference-n2-1-minus-n2-0-ux", "D-difference-n2-1-minus-n2-0-uz", "D-difference-n0-2-minus-n0-1-ux", "D-difference-n0-2-minus-n0-1-uz", "D-difference-n1-2-minus-n1-1-ux", "D-difference-n1-2-minus-n1-1-uz", "D-difference-n2-2-minus-n2-1-ux", "D-difference-n2-2-minus-n2-1-uz"]|derived|
|base-reactions|Global Fx, Fz and My at all three fixed column bases|["D-node-n0-0-Fx", "D-node-n0-0-Fz", "D-node-n0-0-My", "D-node-n1-0-Fx", "D-node-n1-0-Fz", "D-node-n1-0-My", "D-node-n2-0-Fx", "D-node-n2-0-Fz", "D-node-n2-0-My"]|numerical|
|member-section-schedule|Return the complete member-to-section schedule, preserving exterior C1, interior C2, left-bay B1 and right-bay B2 on both stories|[]|interaction|

Applies to every listed row: state = 1.

## Physical definitions

The appendix supplies four distinct rectangular section groups: C1=500x500 mm, C2=350x500 mm, B1=300x600 mm and B2=300x700 mm; these dimensions complete missing source appendices.
The required group representatives are frozen as c0-1, c1-1, b0-1 and b1-1, with both ends requested. The complete schedule still covers every member on both stories.
Column displacement differences are requested separately for every column line, without a rigid-floor constraint or averaging.
Frame members use linear elastic Euler-Bernoulli bending and axial deformation. No shear deformation, end releases, member mass or additional loads are introduced. Beam/column joints and supports follow the explicit input table.
The supplied torsion constant J is the frozen rectangular-section approximation in input.md. Use the numerical A, Iy, Iz and J values supplied, with local y and z as stated in input.md.
