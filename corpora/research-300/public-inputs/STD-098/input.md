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
|top|0|0|6|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|column|column|base|top|M1|C1|0|[1, 0, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|name|type|shape · description|shape · total_depth_mm|shape · bottom_flange_width_mm|shape · bottom_flange_thickness_mm|shape · top_flange_width_mm|shape · top_flange_thickness_mm|shape · web_thickness_mm|shape · centroid_from_bottom_mm|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|C1|Unequal-flange welded H|custom|Welded H with unequal centered flange widths and thicknesses; no fillets|400|300|20|200|15|12|158.7780269058296|0.01338|0.0003539435207399103|5.5052559999999986e-05|1.23524e-06|

Applies to every listed row: shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fy|fz|
|---|---|---|---|---|---|
|D-1 → top|global|nodal|20|15|-400|

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
|interactions|["Report the section-axis mapping: local x=global +Z, local y=global -Y and local z=global +X; global X bending uses Iy and global Y bending uses Iz. Include the numerical principal inertias from the appendix."]|

## Requested outputs — Quantities

|id|location · id|component|unit|
|---|---|---|---|
|case-D-node-top-ux|top|ux|m|
|case-D-node-top-uy|top|uy|m|
|case-D-node-top-uz|top|uz|m|
|case-D-node-top-rx|top|rx|rad|
|case-D-node-top-ry|top|ry|rad|
|case-D-node-top-rz|top|rz|rad|
|case-D-node-base-Fx|base|Fx|kN|
|case-D-node-base-Fy|base|Fy|kN|
|case-D-node-base-Fz|base|Fz|kN|
|case-D-node-base-Mx|base|Mx|kN.m|
|case-D-node-base-My|base|My|kN.m|
|case-D-node-base-Mz|base|Mz|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Physical definitions

The unspecified material is completed as Q355 steel, E=206000 MPa, nu=0.3, G=E/[2(1+nu)] and rho=7850 kg/m³.
The asymmetric section is an idealized welded H of total depth 400 mm, bottom flange 300x20 mm, top flange 200x15 mm and centered 12 mm web. Flanges have different widths and thicknesses, so reflection across local z=0 is not a symmetry. All dimensions and the centroid from the bottom outside face are given in the shape record.
A and the centroidal Iy/Iz are computed from the three non-overlapping component rectangles with the parallel-axis theorem. Since every component is centered in local y, Iyz=0 and local y/z are principal axes. J is the explicit open thin-wall sum of length times thickness cubed divided by 3. Fillets, warping and shear-center eccentric coupling are outside the declared Euler-Bernoulli idealization.
The reference vector is global +X. For the upward column, local x=+Z, local y=-Y and local z=+X, with zero section roll; Iy and Iz must not be interchanged.
The custom section supplies explicit A/Iy/Iz/J. Native adapter support for this custom shape remains an acceptance gate; the properties must not be replaced by a rectangular section.
All members use first-order linear elastic Euler-Bernoulli bending, axial deformation and finite Saint-Venant torsion stiffness. Shear deformation and self-weight are disabled. No geometric stiffness, buckling, capacity or reinforcement assessment is requested.
Section properties A, Iy, Iz and J are explicit inputs in SI units. Rectangular-section J uses the numerical approximation supplied in input.md; no default section properties may replace it.

## Output scope — Required outputs

|id|description|quantityIds|kind|
|---|---|---|---|
|top-six-displacements|Column-top global ux, uy, uz, rx, ry and rz|["case-D-node-top-ux", "case-D-node-top-uy", "case-D-node-top-uz", "case-D-node-top-rx", "case-D-node-top-ry", "case-D-node-top-rz"]|numerical|
|base-six-reactions|Fixed-base global Fx, Fy, Fz, Mx, My and Mz|["case-D-node-base-Fx", "case-D-node-base-Fy", "case-D-node-base-Fz", "case-D-node-base-Mx", "case-D-node-base-My", "case-D-node-base-Mz"]|numerical|
|section-axis-mapping|Report the section-axis mapping: local x=global +Z, local y=global -Y and local z=global +X; global X bending uses Iy and global Y bending uses Iz. Include the numerical principal inertias from the appendix.|[]|interaction|

Applies to every listed row: state = 1.
