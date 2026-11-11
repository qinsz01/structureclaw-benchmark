## Numerical inputs

|Field|Value|
|---|---|
|title|Complete numerical input appendix|
|linearCombinations|[]|
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
|n0-0-0|0|0|0|true|true|true|true|true|true|
|n0-1-0|0|-5|0|true|true|true|true|true|true|
|n1-0-0|6|0|0|true|true|true|true|true|true|
|n1-1-0|6|-5|0|true|true|true|true|true|true|
|n2-0-0|10|0|0|true|true|true|true|true|true|
|n2-1-0|10|-5|0|true|true|true|true|true|true|
|n0-0-1|0|0|3|false|false|false|false|false|false|
|n0-1-1|0|-5|3|false|false|false|false|false|false|
|n1-0-1|6|0|3|false|false|false|false|false|false|
|n1-1-1|6|-5|3|false|false|false|false|false|false|
|n2-0-1|10|0|3|false|false|false|false|false|false|
|n2-1-1|10|-5|3|false|false|false|false|false|false|
|n0-0-2|0|0|7|false|false|false|false|false|false|
|n0-1-2|0|-5|7|false|false|false|false|false|false|
|n1-0-2|6|0|7|false|false|false|false|false|false|
|n1-1-2|6|-5|7|false|false|false|false|false|false|
|n2-0-2|10|0|7|false|false|false|false|false|false|
|n2-1-2|10|-5|7|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-0-1|column|n0-0-0|n0-0-1|M1|C1|0|[1, 0, 0]|
|x0-0-1|beam|n0-0-1|n1-0-1|M1|BX|0|[0, 0, 1]|
|y0-0-1|beam|n0-0-1|n0-1-1|M1|BY|0|[0, 0, 1]|
|c0-1-1|column|n0-1-0|n0-1-1|M1|C1|0|[1, 0, 0]|
|x0-1-1|beam|n0-1-1|n1-1-1|M1|BX|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C1|0|[1, 0, 0]|
|x1-0-1|beam|n1-0-1|n2-0-1|M1|BX|0|[0, 0, 1]|
|y1-0-1|beam|n1-0-1|n1-1-1|M1|BY|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C1|0|[1, 0, 0]|
|x1-1-1|beam|n1-1-1|n2-1-1|M1|BX|0|[0, 0, 1]|
|c2-0-1|column|n2-0-0|n2-0-1|M1|C1|0|[1, 0, 0]|
|y2-0-1|beam|n2-0-1|n2-1-1|M1|BY|0|[0, 0, 1]|
|c2-1-1|column|n2-1-0|n2-1-1|M1|C1|0|[1, 0, 0]|
|c0-0-2|column|n0-0-1|n0-0-2|M1|C1|0|[1, 0, 0]|
|x0-0-2|beam|n0-0-2|n1-0-2|M1|BX|0|[0, 0, 1]|
|y0-0-2|beam|n0-0-2|n0-1-2|M1|BY|0|[0, 0, 1]|
|c0-1-2|column|n0-1-1|n0-1-2|M1|C1|0|[1, 0, 0]|
|x0-1-2|beam|n0-1-2|n1-1-2|M1|BX|0|[0, 0, 1]|
|c1-0-2|column|n1-0-1|n1-0-2|M1|C1|0|[1, 0, 0]|
|x1-0-2|beam|n1-0-2|n2-0-2|M1|BX|0|[0, 0, 1]|
|y1-0-2|beam|n1-0-2|n1-1-2|M1|BY|0|[0, 0, 1]|
|c1-1-2|column|n1-1-1|n1-1-2|M1|C1|0|[1, 0, 0]|
|x1-1-2|beam|n1-1-2|n2-1-2|M1|BX|0|[0, 0, 1]|
|c2-0-2|column|n2-0-1|n2-0-2|M1|C1|0|[1, 0, 0]|
|y2-0-2|beam|n2-0-2|n2-1-2|M1|BY|0|[0, 0, 1]|
|c2-1-2|column|n2-1-1|n2-1-2|M1|C1|0|[1, 0, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|BX|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|BY|250.0|500.0|0.125|0.0026041666666666665|0.0006510416666666666|0.0017881266276041667|
|C1|400.0|500.0|0.2|0.004166666666666667|0.0026666666666666674|0.005474167466666667|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fy|fz|
|---|---|---|---|---|---|
|D-1 → n2-1-2|global|nodal|20|-10|-30|

## Numerical inputs — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Numerical inputs — Floor table

|id|elevation|height|
|---|---|---|
|s1|0|3|
|s2|3|4|

Applies to every listed row: rigid_diaphragm = false.

## Requested outputs

|Field|Value|
|---|---|
|figures|[]|
|interactions|["Supply the transformed coordinate and nodal-load tables, including original source IDs and values, together with transformed restraints and section local axes."]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-n2-1-2-ux|node|n2-1-2|ux|m|—|—|
|case-D-node-n2-1-2-uy|node|n2-1-2|uy|m|—|—|
|case-D-node-n2-1-2-uz|node|n2-1-2|uz|m|—|—|
|case-D-node-n0-0-0-ux|node|n0-0-0|ux|m|—|—|
|case-D-node-n0-0-0-uy|node|n0-0-0|uy|m|—|—|
|case-D-node-n0-0-0-uz|node|n0-0-0|uz|m|—|—|
|case-D-member-c0-0-1-s0-right-N|member|c0-0-1|N|kN|0|right|
|case-D-member-c0-0-1-s0-right-V2|member|c0-0-1|V2|kN|0|right|
|case-D-member-c0-0-1-s0-right-V3|member|c0-0-1|V3|kN|0|right|
|case-D-member-c0-0-1-s0-right-T|member|c0-0-1|T|kN.m|0|right|
|case-D-member-c0-0-1-s0-right-M2|member|c0-0-1|M2|kN.m|0|right|
|case-D-member-c0-0-1-s0-right-M3|member|c0-0-1|M3|kN.m|0|right|
|case-D-member-c0-0-1-s3-left-N|member|c0-0-1|N|kN|3.0|left|
|case-D-member-c0-0-1-s3-left-V2|member|c0-0-1|V2|kN|3.0|left|
|case-D-member-c0-0-1-s3-left-V3|member|c0-0-1|V3|kN|3.0|left|
|case-D-member-c0-0-1-s3-left-T|member|c0-0-1|T|kN.m|3.0|left|
|case-D-member-c0-0-1-s3-left-M2|member|c0-0-1|M2|kN.m|3.0|left|
|case-D-member-c0-0-1-s3-left-M3|member|c0-0-1|M3|kN.m|3.0|left|
|case-D-member-c2-1-1-s0-right-N|member|c2-1-1|N|kN|0|right|
|case-D-member-c2-1-1-s0-right-V2|member|c2-1-1|V2|kN|0|right|
|case-D-member-c2-1-1-s0-right-V3|member|c2-1-1|V3|kN|0|right|
|case-D-member-c2-1-1-s0-right-T|member|c2-1-1|T|kN.m|0|right|
|case-D-member-c2-1-1-s0-right-M2|member|c2-1-1|M2|kN.m|0|right|
|case-D-member-c2-1-1-s0-right-M3|member|c2-1-1|M3|kN.m|0|right|
|case-D-member-c2-1-1-s3-left-N|member|c2-1-1|N|kN|3.0|left|
|case-D-member-c2-1-1-s3-left-V2|member|c2-1-1|V2|kN|3.0|left|
|case-D-member-c2-1-1-s3-left-V3|member|c2-1-1|V3|kN|3.0|left|
|case-D-member-c2-1-1-s3-left-T|member|c2-1-1|T|kN.m|3.0|left|
|case-D-member-c2-1-1-s3-left-M2|member|c2-1-1|M2|kN.m|3.0|left|
|case-D-member-c2-1-1-s3-left-M3|member|c2-1-1|M3|kN.m|3.0|left|
|case-D-member-c2-1-2-s0-right-N|member|c2-1-2|N|kN|0|right|
|case-D-member-c2-1-2-s0-right-V2|member|c2-1-2|V2|kN|0|right|
|case-D-member-c2-1-2-s0-right-V3|member|c2-1-2|V3|kN|0|right|
|case-D-member-c2-1-2-s0-right-T|member|c2-1-2|T|kN.m|0|right|
|case-D-member-c2-1-2-s0-right-M2|member|c2-1-2|M2|kN.m|0|right|
|case-D-member-c2-1-2-s0-right-M3|member|c2-1-2|M3|kN.m|0|right|
|case-D-member-c2-1-2-s4-left-N|member|c2-1-2|N|kN|4.0|left|
|case-D-member-c2-1-2-s4-left-V2|member|c2-1-2|V2|kN|4.0|left|
|case-D-member-c2-1-2-s4-left-V3|member|c2-1-2|V3|kN|4.0|left|
|case-D-member-c2-1-2-s4-left-T|member|c2-1-2|T|kN.m|4.0|left|
|case-D-member-c2-1-2-s4-left-M2|member|c2-1-2|M2|kN.m|4.0|left|
|case-D-member-c2-1-2-s4-left-M3|member|c2-1-2|M3|kN.m|4.0|left|
|case-D-member-x0-0-2-s0-right-N|member|x0-0-2|N|kN|0|right|
|case-D-member-x0-0-2-s0-right-V2|member|x0-0-2|V2|kN|0|right|
|case-D-member-x0-0-2-s0-right-V3|member|x0-0-2|V3|kN|0|right|
|case-D-member-x0-0-2-s0-right-T|member|x0-0-2|T|kN.m|0|right|
|case-D-member-x0-0-2-s0-right-M2|member|x0-0-2|M2|kN.m|0|right|
|case-D-member-x0-0-2-s0-right-M3|member|x0-0-2|M3|kN.m|0|right|
|case-D-member-x0-0-2-s6-left-N|member|x0-0-2|N|kN|6.0|left|
|case-D-member-x0-0-2-s6-left-V2|member|x0-0-2|V2|kN|6.0|left|
|case-D-member-x0-0-2-s6-left-V3|member|x0-0-2|V3|kN|6.0|left|
|case-D-member-x0-0-2-s6-left-T|member|x0-0-2|T|kN.m|6.0|left|
|case-D-member-x0-0-2-s6-left-M2|member|x0-0-2|M2|kN.m|6.0|left|
|case-D-member-x0-0-2-s6-left-M3|member|x0-0-2|M3|kN.m|6.0|left|
|case-D-member-x1-1-2-s0-right-N|member|x1-1-2|N|kN|0|right|
|case-D-member-x1-1-2-s0-right-V2|member|x1-1-2|V2|kN|0|right|
|case-D-member-x1-1-2-s0-right-V3|member|x1-1-2|V3|kN|0|right|
|case-D-member-x1-1-2-s0-right-T|member|x1-1-2|T|kN.m|0|right|
|case-D-member-x1-1-2-s0-right-M2|member|x1-1-2|M2|kN.m|0|right|
|case-D-member-x1-1-2-s0-right-M3|member|x1-1-2|M3|kN.m|0|right|
|case-D-member-x1-1-2-s4-left-N|member|x1-1-2|N|kN|4.0|left|
|case-D-member-x1-1-2-s4-left-V2|member|x1-1-2|V2|kN|4.0|left|
|case-D-member-x1-1-2-s4-left-V3|member|x1-1-2|V3|kN|4.0|left|
|case-D-member-x1-1-2-s4-left-T|member|x1-1-2|T|kN.m|4.0|left|
|case-D-member-x1-1-2-s4-left-M2|member|x1-1-2|M2|kN.m|4.0|left|
|case-D-member-x1-1-2-s4-left-M3|member|x1-1-2|M3|kN.m|4.0|left|
|case-D-member-y2-0-2-s0-right-N|member|y2-0-2|N|kN|0|right|
|case-D-member-y2-0-2-s0-right-V2|member|y2-0-2|V2|kN|0|right|
|case-D-member-y2-0-2-s0-right-V3|member|y2-0-2|V3|kN|0|right|
|case-D-member-y2-0-2-s0-right-T|member|y2-0-2|T|kN.m|0|right|
|case-D-member-y2-0-2-s0-right-M2|member|y2-0-2|M2|kN.m|0|right|
|case-D-member-y2-0-2-s0-right-M3|member|y2-0-2|M3|kN.m|0|right|
|case-D-member-y2-0-2-s5-left-N|member|y2-0-2|N|kN|5.0|left|
|case-D-member-y2-0-2-s5-left-V2|member|y2-0-2|V2|kN|5.0|left|
|case-D-member-y2-0-2-s5-left-V3|member|y2-0-2|V3|kN|5.0|left|
|case-D-member-y2-0-2-s5-left-T|member|y2-0-2|T|kN.m|5.0|left|
|case-D-member-y2-0-2-s5-left-M2|member|y2-0-2|M2|kN.m|5.0|left|
|case-D-member-y2-0-2-s5-left-M3|member|y2-0-2|M3|kN.m|5.0|left|
|case-D-node-n0-0-0-Fx|node|n0-0-0|Fx|kN|—|—|
|case-D-node-n0-0-0-Fy|node|n0-0-0|Fy|kN|—|—|
|case-D-node-n0-0-0-Fz|node|n0-0-0|Fz|kN|—|—|
|case-D-node-n0-0-0-Mx|node|n0-0-0|Mx|kN.m|—|—|
|case-D-node-n0-0-0-My|node|n0-0-0|My|kN.m|—|—|
|case-D-node-n0-0-0-Mz|node|n0-0-0|Mz|kN.m|—|—|
|case-D-node-n0-1-0-Fx|node|n0-1-0|Fx|kN|—|—|
|case-D-node-n0-1-0-Fy|node|n0-1-0|Fy|kN|—|—|
|case-D-node-n0-1-0-Fz|node|n0-1-0|Fz|kN|—|—|
|case-D-node-n0-1-0-Mx|node|n0-1-0|Mx|kN.m|—|—|
|case-D-node-n0-1-0-My|node|n0-1-0|My|kN.m|—|—|
|case-D-node-n0-1-0-Mz|node|n0-1-0|Mz|kN.m|—|—|
|case-D-node-n1-0-0-Fx|node|n1-0-0|Fx|kN|—|—|
|case-D-node-n1-0-0-Fy|node|n1-0-0|Fy|kN|—|—|
|case-D-node-n1-0-0-Fz|node|n1-0-0|Fz|kN|—|—|
|case-D-node-n1-0-0-Mx|node|n1-0-0|Mx|kN.m|—|—|
|case-D-node-n1-0-0-My|node|n1-0-0|My|kN.m|—|—|
|case-D-node-n1-0-0-Mz|node|n1-0-0|Mz|kN.m|—|—|
|case-D-node-n1-1-0-Fx|node|n1-1-0|Fx|kN|—|—|
|case-D-node-n1-1-0-Fy|node|n1-1-0|Fy|kN|—|—|
|case-D-node-n1-1-0-Fz|node|n1-1-0|Fz|kN|—|—|
|case-D-node-n1-1-0-Mx|node|n1-1-0|Mx|kN.m|—|—|
|case-D-node-n1-1-0-My|node|n1-1-0|My|kN.m|—|—|
|case-D-node-n1-1-0-Mz|node|n1-1-0|Mz|kN.m|—|—|
|case-D-node-n2-0-0-Fx|node|n2-0-0|Fx|kN|—|—|
|case-D-node-n2-0-0-Fy|node|n2-0-0|Fy|kN|—|—|
|case-D-node-n2-0-0-Fz|node|n2-0-0|Fz|kN|—|—|
|case-D-node-n2-0-0-Mx|node|n2-0-0|Mx|kN.m|—|—|
|case-D-node-n2-0-0-My|node|n2-0-0|My|kN.m|—|—|
|case-D-node-n2-0-0-Mz|node|n2-0-0|Mz|kN.m|—|—|
|case-D-node-n2-1-0-Fx|node|n2-1-0|Fx|kN|—|—|
|case-D-node-n2-1-0-Fy|node|n2-1-0|Fy|kN|—|—|
|case-D-node-n2-1-0-Fz|node|n2-1-0|Fz|kN|—|—|
|case-D-node-n2-1-0-Mx|node|n2-1-0|Mx|kN.m|—|—|
|case-D-node-n2-1-0-My|node|n2-1-0|My|kN.m|—|—|
|case-D-node-n2-1-0-Mz|node|n2-1-0|Mz|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|case-D-source-displacement-X|["case-D-node-n2-1-2-ux", "case-D-node-n0-0-0-ux"]|Source X displacement at source (10,7,5) m = global ux; subtract fixed base ux=0.|
|case-D-source-displacement-Y|["case-D-node-n2-1-2-uz", "case-D-node-n0-0-0-uz"]|Source Y displacement at source (10,7,5) m = global uz; subtract fixed base uz=0.|
|case-D-source-displacement-Z|["case-D-node-n0-0-0-uy", "case-D-node-n2-1-2-uy"]|Source Z displacement at source (10,7,5) m = -global uy; fixed base uy=0 minus top uy.|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.

## Coordinate transform

|Field|Value|
|---|---|
|sourceUpAxis|Y|
|globalUpAxis|Z|
|equation|(global X, global Y, global Z)=(source X, -source Z, source Y)|
|sourceDofOrder|["ux_source", "uy_source", "uz_source", "rx_source", "ry_source", "rz_source"]|
|globalDofOrder|["ux", "uy", "uz", "rx", "ry", "rz"]|
|displacementInverse|ux_source=ux; uy_source=uz; uz_source=-uy|
|analysis|First-order linear elastic Euler-Bernoulli; no self weight, diaphragm, rigid offsets or P-Delta.|

## Coordinate transform — Source to global

[[1, 0, 0], [0, 0, -1], [0, 1, 0]]

## Coordinate transform — Vector units

|Field|Value|
|---|---|
|coordinates|m|
|forces|kN|
|displacements|m|
|rotations|rad|

## Coordinate transform — Nodes

|id|sourceCoordinates|globalCoordinates|sourceRestraints|globalRestraints|
|---|---|---|---|---|
|n0-0-0|[0, 0, 0]|[0, 0, 0]|[true, true, true, true, true, true]|[true, true, true, true, true, true]|
|n0-1-0|[0, 0, 5]|[0, -5, 0]|[true, true, true, true, true, true]|[true, true, true, true, true, true]|
|n1-0-0|[6, 0, 0]|[6, 0, 0]|[true, true, true, true, true, true]|[true, true, true, true, true, true]|
|n1-1-0|[6, 0, 5]|[6, -5, 0]|[true, true, true, true, true, true]|[true, true, true, true, true, true]|
|n2-0-0|[10, 0, 0]|[10, 0, 0]|[true, true, true, true, true, true]|[true, true, true, true, true, true]|
|n2-1-0|[10, 0, 5]|[10, -5, 0]|[true, true, true, true, true, true]|[true, true, true, true, true, true]|
|n0-0-1|[0, 3, 0]|[0, 0, 3]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n0-1-1|[0, 3, 5]|[0, -5, 3]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n1-0-1|[6, 3, 0]|[6, 0, 3]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n1-1-1|[6, 3, 5]|[6, -5, 3]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n2-0-1|[10, 3, 0]|[10, 0, 3]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n2-1-1|[10, 3, 5]|[10, -5, 3]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n0-0-2|[0, 7, 0]|[0, 0, 7]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n0-1-2|[0, 7, 5]|[0, -5, 7]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n1-0-2|[6, 7, 0]|[6, 0, 7]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n1-1-2|[6, 7, 5]|[6, -5, 7]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n2-0-2|[10, 7, 0]|[10, 0, 7]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|
|n2-1-2|[10, 7, 5]|[10, -5, 7]|[false, false, false, false, false, false]|[false, false, false, false, false, false]|

## Coordinate transform — Members

|id|orderedNodes|section|referenceSource|referenceGlobal|axesSource · x|axesSource · y|axesSource · z|axesGlobal · x|axesGlobal · y|axesGlobal · z|
|---|---|---|---|---|---|---|---|---|---|---|
|c0-0-1|["n0-0-0", "n0-0-1"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x0-0-1|["n0-0-1", "n1-0-1"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|y0-0-1|["n0-0-1", "n0-1-1"]|BY|[0, 1, 0]|[0, 0, 1]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, 1.0, 0.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, -0.0, 1.0]|
|c0-1-1|["n0-1-0", "n0-1-1"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x0-1-1|["n0-1-1", "n1-1-1"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|c1-0-1|["n1-0-0", "n1-0-1"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x1-0-1|["n1-0-1", "n2-0-1"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|y1-0-1|["n1-0-1", "n1-1-1"]|BY|[0, 1, 0]|[0, 0, 1]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, 1.0, 0.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, -0.0, 1.0]|
|c1-1-1|["n1-1-0", "n1-1-1"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x1-1-1|["n1-1-1", "n2-1-1"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|c2-0-1|["n2-0-0", "n2-0-1"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|y2-0-1|["n2-0-1", "n2-1-1"]|BY|[0, 1, 0]|[0, 0, 1]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, 1.0, 0.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, -0.0, 1.0]|
|c2-1-1|["n2-1-0", "n2-1-1"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|c0-0-2|["n0-0-1", "n0-0-2"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x0-0-2|["n0-0-2", "n1-0-2"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|y0-0-2|["n0-0-2", "n0-1-2"]|BY|[0, 1, 0]|[0, 0, 1]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, 1.0, 0.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, -0.0, 1.0]|
|c0-1-2|["n0-1-1", "n0-1-2"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x0-1-2|["n0-1-2", "n1-1-2"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|c1-0-2|["n1-0-1", "n1-0-2"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x1-0-2|["n1-0-2", "n2-0-2"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|y1-0-2|["n1-0-2", "n1-1-2"]|BY|[0, 1, 0]|[0, 0, 1]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, 1.0, 0.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, -0.0, 1.0]|
|c1-1-2|["n1-1-1", "n1-1-2"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|x1-1-2|["n1-1-2", "n2-1-2"]|BX|[0, 1, 0]|[0, 0, 1]|[1.0, 0.0, 0.0]|[0.0, 0.0, -1.0]|[-0.0, 1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, 1.0, 0.0]|[-0.0, -0.0, 1.0]|
|c2-0-2|["n2-0-1", "n2-0-2"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|
|y2-0-2|["n2-0-2", "n2-1-2"]|BY|[0, 1, 0]|[0, 0, 1]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, 1.0, 0.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|[0.0, -0.0, 1.0]|
|c2-1-2|["n2-1-1", "n2-1-2"]|C1|[1, 0, 0]|[1, 0, 0]|[0.0, 1.0, 0.0]|[0.0, 0.0, 1.0]|[1.0, 0.0, 0.0]|[0.0, -0.0, 1.0]|[0.0, -1.0, 0.0]|[1.0, -0.0, 0.0]|

Applies to every listed row: material = M1; rollDegrees = 0.

## Coordinate transform — Source loads

|case|node|sourceCoordinates|forceSource|momentSource|
|---|---|---|---|---|
|D|n2-1-2|[10, 7, 5]|[20, -30, 10]|[0, 0, 0]|

## Coordinate transform — Global loads

|case|node|globalCoordinates|forceGlobal|momentGlobal|
|---|---|---|---|---|
|D|n2-1-2|[10, -5, 7]|[20, -10, -30]|[0, 0, 0]|
