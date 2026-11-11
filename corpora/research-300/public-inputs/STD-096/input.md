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
|base|0|0|0|true|true|true|true|true|true|
|top|0|0|4.2|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|column|column|base|top|M1|C1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C30|concrete|30000|12500|0.2|2500|

## Numerical inputs — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|C1|rectangular|450.0|450.0|0.2025|0.0034171875000000005|0.0034171875000000005|0.005775046875000001|

Applies to every listed row: name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fz|
|---|---|---|---|---|
|D-1 → top|global|nodal|30|-600|

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
|case-D-node-top-ux|node|top|ux|m|—|—|
|case-D-node-top-uz|node|top|uz|m|—|—|
|case-D-node-top-ry|node|top|ry|rad|—|—|
|case-D-member-column-s0-right-N|member|column|N|kN|0|right|
|case-D-member-column-s0-right-V3|member|column|V3|kN|0|right|
|case-D-member-column-s0-right-M2|member|column|M2|kN.m|0|right|
|case-D-node-base-Fx|node|base|Fx|kN|—|—|
|case-D-node-base-Fz|node|base|Fz|kN|—|—|
|case-D-node-base-My|node|base|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Physical definitions

The source leaves the concrete grade and elastic constants unspecified. The appendix freezes C30 with E=30000 MPa, nu=0.2, G=12500 MPa and rho=2500 kg/m³; the given 450x450 mm section is retained.
The base-section result is located at member column, position 0 m, side right. Both local section forces and global support reactions are requested to disambiguate the source phrase 'base axial force/shear/moment'.
The top axial and lateral forces are simultaneous components of case D. They do not activate P-Delta or change the prescribed first-order model.
All members use first-order linear elastic Euler-Bernoulli bending, axial deformation and finite Saint-Venant torsion stiffness. Shear deformation and self-weight are disabled. No geometric stiffness, buckling, capacity or reinforcement assessment is requested.
Section properties A, Iy, Iz and J are explicit inputs in SI units. Rectangular-section J uses the numerical approximation supplied in input.md; no default section properties may replace it.

## Output scope — Required outputs

|id|description|quantityIds|
|---|---|---|
|top-displacement-and-rotation|Column-top global ux, uz and ry|["case-D-node-top-ux", "case-D-node-top-uz", "case-D-node-top-ry"]|
|base-section-actions|Local N, V3 and M2 immediately above the fixed column base|["case-D-member-column-s0-right-N", "case-D-member-column-s0-right-V3", "case-D-member-column-s0-right-M2"]|
|base-reactions|Global Fx, Fz and My at the fixed column base|["case-D-node-base-Fx", "case-D-node-base-Fz", "case-D-node-base-My"]|

Applies to every listed row: state = 1; kind = numerical.
