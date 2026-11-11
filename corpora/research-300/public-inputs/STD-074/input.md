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
|n1-0|7|0|0|true|true|true|true|true|true|
|n0-1|0|0|3.6|false|true|false|true|false|true|
|n1-1|7|0|3.6|false|true|false|true|false|true|
|n0-2|0|0|7.2|false|true|false|true|false|true|
|n1-2|7|0|7.2|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|C30|CR|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|C30|CR|90|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|C30|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|C30|CR|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|C30|CR|90|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|C30|B1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|type|E|G|nu|rho|
|---|---|---|---|---|---|
|C30|concrete|30000|12500.0|0.2|2500|

Applies to every listed row: name = id.

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|B1|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|CR|350.0|500.0|0.175|0.003645833333333333|0.0017864583333333328|0.0040575733442708315|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|type|wz|fx|
|---|---|---|---|
|D-1 → b0-1, D-2 → b0-2|distributed|-10|—|
|D-3 → n1-2|nodal|—|20|

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
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-n0-1-ux|node|n0-1|ux|m|—|—|
|case-D-node-n1-1-ux|node|n1-1|ux|m|—|—|
|case-D-node-n0-2-ux|node|n0-2|ux|m|—|—|
|case-D-node-n1-2-ux|node|n1-2|ux|m|—|—|
|case-D-node-n0-0-ux|node|n0-0|ux|m|—|—|
|case-D-node-n1-0-ux|node|n1-0|ux|m|—|—|
|case-D-member-c0-1-s0-right-M2|member|c0-1|M2|kN.m|0|right|
|case-D-member-c0-1-s0-right-M3|member|c0-1|M3|kN.m|0|right|
|case-D-member-c0-1-s3.6-left-M2|member|c0-1|M2|kN.m|3.6|left|
|case-D-member-c0-1-s3.6-left-M3|member|c0-1|M3|kN.m|3.6|left|
|case-D-member-c1-1-s0-right-M2|member|c1-1|M2|kN.m|0|right|
|case-D-member-c1-1-s0-right-M3|member|c1-1|M3|kN.m|0|right|
|case-D-member-c1-1-s3.6-left-M2|member|c1-1|M2|kN.m|3.6|left|
|case-D-member-c1-1-s3.6-left-M3|member|c1-1|M3|kN.m|3.6|left|
|case-D-member-c0-2-s0-right-M2|member|c0-2|M2|kN.m|0|right|
|case-D-member-c0-2-s0-right-M3|member|c0-2|M3|kN.m|0|right|
|case-D-member-c0-2-s3.6-left-M2|member|c0-2|M2|kN.m|3.6|left|
|case-D-member-c0-2-s3.6-left-M3|member|c0-2|M3|kN.m|3.6|left|
|case-D-member-c1-2-s0-right-M2|member|c1-2|M2|kN.m|0|right|
|case-D-member-c1-2-s0-right-M3|member|c1-2|M3|kN.m|0|right|
|case-D-member-c1-2-s3.6-left-M2|member|c1-2|M2|kN.m|3.6|left|
|case-D-member-c1-2-s3.6-left-M3|member|c1-2|M3|kN.m|3.6|left|
|case-D-node-n0-0-Fx|node|n0-0|Fx|kN|—|—|
|case-D-node-n0-0-Fz|node|n0-0|Fz|kN|—|—|
|case-D-node-n0-0-My|node|n0-0|My|kN.m|—|—|
|case-D-node-n1-0-Fx|node|n1-0|Fx|kN|—|—|
|case-D-node-n1-0-Fz|node|n1-0|Fz|kN|—|—|
|case-D-node-n1-0-My|node|n1-0|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|D-drift-n0-0-n0-1-ux|["case-D-node-n0-1-ux", "case-D-node-n0-0-ux"]|n0-1 minus n0-0: ux; signed story displacement difference|
|D-drift-n1-0-n1-1-ux|["case-D-node-n1-1-ux", "case-D-node-n1-0-ux"]|n1-1 minus n1-0: ux; signed story displacement difference|
|D-drift-n0-1-n0-2-ux|["case-D-node-n0-2-ux", "case-D-node-n0-1-ux"]|n0-2 minus n0-1: ux; signed story displacement difference|
|D-drift-n1-1-n1-2-ux|["case-D-node-n1-2-ux", "case-D-node-n1-1-ux"]|n1-2 minus n1-1: ux; signed story displacement difference|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Column orientations

RECTANGULAR COLUMN ORIENTATION APPENDIX
All axes below are global XYZ unit vectors. Positive roll angles are in degrees.
For every member, local x points from the first listed node to the second.
At zero roll in the XZ plane, local y=(0,1,0) and local z=local x cross local y.
Roll theta transforms y_new=cos(theta)*y+sin(theta)*z and z_new=-sin(theta)*y+cos(theta)*z.
Both column lines use the identical CR section: B=350 mm along local y, H=500 mm along local z; A=0.175 m^2, Iy=0.003645833333333333 m^4, Iz=0.001786458333333333 m^4. J is listed in input.md.
Left columns c0-1 and c0-2: roll=0; x=(0,0,1), y=(0,1,0), z=(-1,0,0). Planar bending uses Iy about local y (strong axis); global My equals local M2.
Right columns c1-1 and c1-2: roll=90; x=(0,0,1), y=(-1,0,0), z=(0,-1,0). Planar bending uses Iz about local z (weak axis); global My equals minus local M3.
Beams b0-1 and b0-2: roll=0; x=(1,0,0), y=(0,1,0), z=(0,0,1).
Report both local M2 and M3 at both ends of every column and identify the nonzero in-plane component. Moment signs follow the cut convention in the general analysis appendix. No extra nodal couple is applied.
