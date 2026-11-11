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
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Numerical inputs — Nodes

|id|X_m|Y_m|Z_m|fixed_ux|fixed_uy|fixed_uz|fixed_rx|fixed_ry|fixed_rz|
|---|---|---|---|---|---|---|---|---|---|
|base|0|0|0|true|true|true|true|true|true|
|top|0|0|5|false|false|false|false|false|false|
|tip|1|0|5|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|column|column|base|top|M1|C1|0|[1, 0, 0]|
|arm|beam|top|tip|M1|B1|0|[0, 0, 1]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|C1|400.0|500.0|0.2|0.004166666666666667|0.0026666666666666674|0.005474167466666667|
|B1|250.0|400.0|0.1|0.0013333333333333337|0.0005208333333333333|0.0012734516461690268|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fy|fz|
|---|---|---|---|---|
|D-1 → tip|global|nodal|10|-200|

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
|case-D-node-tip-ux|node|tip|ux|m|—|—|
|case-D-node-tip-uy|node|tip|uy|m|—|—|
|case-D-node-tip-uz|node|tip|uz|m|—|—|
|case-D-node-tip-rx|node|tip|rx|rad|—|—|
|case-D-node-tip-ry|node|tip|ry|rad|—|—|
|case-D-node-tip-rz|node|tip|rz|rad|—|—|
|case-D-node-top-rx|node|top|rx|rad|—|—|
|case-D-node-top-ry|node|top|ry|rad|—|—|
|case-D-node-top-rz|node|top|rz|rad|—|—|
|case-D-node-base-Fx|node|base|Fx|kN|—|—|
|case-D-node-base-Fy|node|base|Fy|kN|—|—|
|case-D-node-base-Fz|node|base|Fz|kN|—|—|
|case-D-node-base-Mx|node|base|Mx|kN.m|—|—|
|case-D-node-base-My|node|base|My|kN.m|—|—|
|case-D-node-base-Mz|node|base|Mz|kN.m|—|—|
|case-D-member-column-s0-right-N|member|column|N|kN|0|right|
|case-D-member-column-s0-right-V2|member|column|V2|kN|0|right|
|case-D-member-column-s0-right-V3|member|column|V3|kN|0|right|
|case-D-member-column-s0-right-T|member|column|T|kN.m|0|right|
|case-D-member-column-s0-right-M2|member|column|M2|kN.m|0|right|
|case-D-member-column-s0-right-M3|member|column|M3|kN.m|0|right|
|case-D-member-column-s5-left-N|member|column|N|kN|5.0|left|
|case-D-member-column-s5-left-V2|member|column|V2|kN|5.0|left|
|case-D-member-column-s5-left-V3|member|column|V3|kN|5.0|left|
|case-D-member-column-s5-left-T|member|column|T|kN.m|5.0|left|
|case-D-member-column-s5-left-M2|member|column|M2|kN.m|5.0|left|
|case-D-member-column-s5-left-M3|member|column|M3|kN.m|5.0|left|
|case-D-member-arm-s0-right-N|member|arm|N|kN|0|right|
|case-D-member-arm-s0-right-V2|member|arm|V2|kN|0|right|
|case-D-member-arm-s0-right-V3|member|arm|V3|kN|0|right|
|case-D-member-arm-s0-right-T|member|arm|T|kN.m|0|right|
|case-D-member-arm-s0-right-M2|member|arm|M2|kN.m|0|right|
|case-D-member-arm-s0-right-M3|member|arm|M3|kN.m|0|right|
|case-D-member-arm-s1-left-N|member|arm|N|kN|1.0|left|
|case-D-member-arm-s1-left-V2|member|arm|V2|kN|1.0|left|
|case-D-member-arm-s1-left-V3|member|arm|V3|kN|1.0|left|
|case-D-member-arm-s1-left-T|member|arm|T|kN.m|1.0|left|
|case-D-member-arm-s1-left-M2|member|arm|M2|kN.m|1.0|left|
|case-D-member-arm-s1-left-M3|member|arm|M3|kN.m|1.0|left|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Physical definitions

The appendix supplies Q355 steel and separate idealized rectangular sections: C1=400x500 mm for the column and B1=250x400 mm for the arm. Each has its own explicit finite A, Iy, Iz and J.
The arm is a 1 m elastic beam element sharing all six joint degrees of freedom with the column top. It is not a rigid link or a concentrated moment substitute.
For the column, local x=+Z, y=-Y, z=+X using reference +X. For the arm, local x=+X, y=+Y, z=+Z using reference +Z. Both have zero roll.
All six end-force components are retained, including axial torsion T; the eccentric tip forces remain at the actual free node.
All members use first-order linear elastic Euler-Bernoulli bending, axial deformation and finite Saint-Venant torsion stiffness. Shear deformation and self-weight are disabled. No geometric stiffness, buckling, capacity or reinforcement assessment is requested.
Section properties A, Iy, Iz and J are explicit inputs in SI units. Rectangular-section J uses the numerical approximation supplied in input.md; no default section properties may replace it.

## Output scope — Required outputs

|id|description|quantityIds|
|---|---|---|
|arm-tip-six-displacements|Arm-tip global ux, uy, uz, rx, ry and rz|["case-D-node-tip-ux", "case-D-node-tip-uy", "case-D-node-tip-uz", "case-D-node-tip-rx", "case-D-node-tip-ry", "case-D-node-tip-rz"]|
|column-top-rotations|Column-top global rx, ry and rz|["case-D-node-top-rx", "case-D-node-top-ry", "case-D-node-top-rz"]|
|base-six-reactions|Fixed-base global Fx, Fy, Fz, Mx, My and Mz|["case-D-node-base-Fx", "case-D-node-base-Fy", "case-D-node-base-Fz", "case-D-node-base-Mx", "case-D-node-base-My", "case-D-node-base-Mz"]|
|column-end-forces|Both column ends: local N, V2, V3, T, M2 and M3|["case-D-member-column-s0-right-N", "case-D-member-column-s0-right-V2", "case-D-member-column-s0-right-V3", "case-D-member-column-s0-right-T", "case-D-member-column-s0-right-M2", "case-D-member-column-s0-right-M3", "case-D-member-column-s5-left-N", "case-D-member-column-s5-left-V2", "case-D-member-column-s5-left-V3", "case-D-member-column-s5-left-T", "case-D-member-column-s5-left-M2", "case-D-member-column-s5-left-M3"]|
|arm-end-forces|Both finite-stiffness arm ends: local N, V2, V3, T, M2 and M3|["case-D-member-arm-s0-right-N", "case-D-member-arm-s0-right-V2", "case-D-member-arm-s0-right-V3", "case-D-member-arm-s0-right-T", "case-D-member-arm-s0-right-M2", "case-D-member-arm-s0-right-M3", "case-D-member-arm-s1-left-N", "case-D-member-arm-s1-left-V2", "case-D-member-arm-s1-left-V3", "case-D-member-arm-s1-left-T", "case-D-member-arm-s1-left-M2", "case-D-member-arm-s1-left-M3"]|

Applies to every listed row: state = 1; kind = numerical.
