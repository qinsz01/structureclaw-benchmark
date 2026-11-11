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
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Numerical inputs — Nodes

|id|X_m|Y_m|Z_m|fixed_ux|fixed_uy|fixed_uz|fixed_rx|fixed_ry|fixed_rz|
|---|---|---|---|---|---|---|---|---|---|
|n0-0-0|0|0|0|true|true|true|true|true|true|
|n0-1-0|0|5|0|true|true|true|true|true|true|
|n1-0-0|6|0|0|true|true|true|true|true|true|
|n1-1-0|6|5|0|true|true|true|true|true|true|
|n2-0-0|12|0|0|true|true|true|true|true|true|
|n2-1-0|12|5|0|true|true|true|true|true|true|
|n0-0-1|0|0|6|false|false|false|false|false|false|
|n0-1-1|0|5|8|false|false|false|false|false|false|
|n1-0-1|6|0|6|false|false|false|false|false|false|
|n1-1-1|6|5|8|false|false|false|false|false|false|
|n2-0-1|12|0|6|false|false|false|false|false|false|
|n2-1-1|12|5|8|false|false|false|false|false|false|
|mid-y0-0-1|0.0|2.5|7.0|false|false|false|false|false|false|
|mid-y1-0-1|6.0|2.5|7.0|false|false|false|false|false|false|
|mid-y2-0-1|12.0|2.5|7.0|false|false|false|false|false|false|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-0-1|column|n0-0-0|n0-0-1|M1|C1|0|[1, 0, 0]|
|x0-0-1|beam|n0-0-1|n1-0-1|M1|BX|0|[0, 0, 1]|
|y0-0-1-a|beam|n0-0-1|mid-y0-0-1|M1|BY|0|[0, 0, 1]|
|y0-0-1-b|beam|mid-y0-0-1|n0-1-1|M1|BY|0|[0, 0, 1]|
|c0-1-1|column|n0-1-0|n0-1-1|M1|C1|0|[1, 0, 0]|
|x0-1-1|beam|n0-1-1|n1-1-1|M1|BX|0|[0, 0, 1]|
|c1-0-1|column|n1-0-0|n1-0-1|M1|C1|0|[1, 0, 0]|
|x1-0-1|beam|n1-0-1|n2-0-1|M1|BX|0|[0, 0, 1]|
|y1-0-1-a|beam|n1-0-1|mid-y1-0-1|M1|BY|0|[0, 0, 1]|
|y1-0-1-b|beam|mid-y1-0-1|n1-1-1|M1|BY|0|[0, 0, 1]|
|c1-1-1|column|n1-1-0|n1-1-1|M1|C1|0|[1, 0, 0]|
|x1-1-1|beam|n1-1-1|n2-1-1|M1|BX|0|[0, 0, 1]|
|c2-0-1|column|n2-0-0|n2-0-1|M1|C1|0|[1, 0, 0]|
|y2-0-1-a|beam|n2-0-1|mid-y2-0-1|M1|BY|0|[0, 0, 1]|
|y2-0-1-b|beam|mid-y2-0-1|n2-1-1|M1|BY|0|[0, 0, 1]|
|c2-1-1|column|n2-1-0|n2-1-1|M1|C1|0|[1, 0, 0]|

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

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → x0-0-1, D-2 → y0-0-1-a, D-3 → y0-0-1-b, D-4 → x0-1-1, D-5 → x1-0-1, D-6 → y1-0-1-a, D-7 → y1-0-1-b, D-8 → x1-1-1, D-9 → y2-0-1-a, D-10 → y2-0-1-b|global|distributed|-5|

## Numerical inputs — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Numerical inputs — Continuity notes — Physical beams — Y0 0 1

|Field|Value|
|---|---|
|nodes|["n0-0-1", "n0-1-1"]|
|segments|["y0-0-1-a", "y0-0-1-b"]|
|midpointNode|mid-y0-0-1|
|addedMass|0|
|joint|continuous-rigid|

## Numerical inputs — Continuity notes — Physical beams — Y1 0 1

|Field|Value|
|---|---|
|nodes|["n1-0-1", "n1-1-1"]|
|segments|["y1-0-1-a", "y1-0-1-b"]|
|midpointNode|mid-y1-0-1|
|addedMass|0|
|joint|continuous-rigid|

## Numerical inputs — Continuity notes — Physical beams — Y2 0 1

|Field|Value|
|---|---|
|nodes|["n2-0-1", "n2-1-1"]|
|segments|["y2-0-1-a", "y2-0-1-b"]|
|midpointNode|mid-y2-0-1|
|addedMass|0|
|joint|continuous-rigid|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-n0-0-1-ux|node|n0-0-1|ux|m|—|—|
|case-D-node-n0-0-1-uy|node|n0-0-1|uy|m|—|—|
|case-D-node-n0-0-1-uz|node|n0-0-1|uz|m|—|—|
|case-D-node-n0-1-1-ux|node|n0-1-1|ux|m|—|—|
|case-D-node-n0-1-1-uy|node|n0-1-1|uy|m|—|—|
|case-D-node-n0-1-1-uz|node|n0-1-1|uz|m|—|—|
|case-D-node-n1-0-1-ux|node|n1-0-1|ux|m|—|—|
|case-D-node-n1-0-1-uy|node|n1-0-1|uy|m|—|—|
|case-D-node-n1-0-1-uz|node|n1-0-1|uz|m|—|—|
|case-D-node-n1-1-1-ux|node|n1-1-1|ux|m|—|—|
|case-D-node-n1-1-1-uy|node|n1-1-1|uy|m|—|—|
|case-D-node-n1-1-1-uz|node|n1-1-1|uz|m|—|—|
|case-D-node-n2-0-1-ux|node|n2-0-1|ux|m|—|—|
|case-D-node-n2-0-1-uy|node|n2-0-1|uy|m|—|—|
|case-D-node-n2-0-1-uz|node|n2-0-1|uz|m|—|—|
|case-D-node-n2-1-1-ux|node|n2-1-1|ux|m|—|—|
|case-D-node-n2-1-1-uy|node|n2-1-1|uy|m|—|—|
|case-D-node-n2-1-1-uz|node|n2-1-1|uz|m|—|—|
|case-D-node-mid-y0-0-1-ux|node|mid-y0-0-1|ux|m|—|—|
|case-D-node-mid-y0-0-1-uy|node|mid-y0-0-1|uy|m|—|—|
|case-D-node-mid-y0-0-1-uz|node|mid-y0-0-1|uz|m|—|—|
|case-D-node-mid-y1-0-1-ux|node|mid-y1-0-1|ux|m|—|—|
|case-D-node-mid-y1-0-1-uy|node|mid-y1-0-1|uy|m|—|—|
|case-D-node-mid-y1-0-1-uz|node|mid-y1-0-1|uz|m|—|—|
|case-D-node-mid-y2-0-1-ux|node|mid-y2-0-1|ux|m|—|—|
|case-D-node-mid-y2-0-1-uy|node|mid-y2-0-1|uy|m|—|—|
|case-D-node-mid-y2-0-1-uz|node|mid-y2-0-1|uz|m|—|—|
|case-D-member-y0-0-1-a-s0-right-N|member|y0-0-1-a|N|kN|0|right|
|case-D-member-y0-0-1-a-s0-right-V2|member|y0-0-1-a|V2|kN|0|right|
|case-D-member-y0-0-1-a-s0-right-V3|member|y0-0-1-a|V3|kN|0|right|
|case-D-member-y0-0-1-a-s0-right-T|member|y0-0-1-a|T|kN.m|0|right|
|case-D-member-y0-0-1-a-s0-right-M2|member|y0-0-1-a|M2|kN.m|0|right|
|case-D-member-y0-0-1-a-s0-right-M3|member|y0-0-1-a|M3|kN.m|0|right|
|case-D-member-y0-0-1-b-s2.69258240357-left-N|member|y0-0-1-b|N|kN|2.692582403567252|left|
|case-D-member-y0-0-1-b-s2.69258240357-left-V2|member|y0-0-1-b|V2|kN|2.692582403567252|left|
|case-D-member-y0-0-1-b-s2.69258240357-left-V3|member|y0-0-1-b|V3|kN|2.692582403567252|left|
|case-D-member-y0-0-1-b-s2.69258240357-left-T|member|y0-0-1-b|T|kN.m|2.692582403567252|left|
|case-D-member-y0-0-1-b-s2.69258240357-left-M2|member|y0-0-1-b|M2|kN.m|2.692582403567252|left|
|case-D-member-y0-0-1-b-s2.69258240357-left-M3|member|y0-0-1-b|M3|kN.m|2.692582403567252|left|
|case-D-member-y1-0-1-a-s0-right-N|member|y1-0-1-a|N|kN|0|right|
|case-D-member-y1-0-1-a-s0-right-V2|member|y1-0-1-a|V2|kN|0|right|
|case-D-member-y1-0-1-a-s0-right-V3|member|y1-0-1-a|V3|kN|0|right|
|case-D-member-y1-0-1-a-s0-right-T|member|y1-0-1-a|T|kN.m|0|right|
|case-D-member-y1-0-1-a-s0-right-M2|member|y1-0-1-a|M2|kN.m|0|right|
|case-D-member-y1-0-1-a-s0-right-M3|member|y1-0-1-a|M3|kN.m|0|right|
|case-D-member-y1-0-1-b-s2.69258240357-left-N|member|y1-0-1-b|N|kN|2.692582403567252|left|
|case-D-member-y1-0-1-b-s2.69258240357-left-V2|member|y1-0-1-b|V2|kN|2.692582403567252|left|
|case-D-member-y1-0-1-b-s2.69258240357-left-V3|member|y1-0-1-b|V3|kN|2.692582403567252|left|
|case-D-member-y1-0-1-b-s2.69258240357-left-T|member|y1-0-1-b|T|kN.m|2.692582403567252|left|
|case-D-member-y1-0-1-b-s2.69258240357-left-M2|member|y1-0-1-b|M2|kN.m|2.692582403567252|left|
|case-D-member-y1-0-1-b-s2.69258240357-left-M3|member|y1-0-1-b|M3|kN.m|2.692582403567252|left|
|case-D-member-y2-0-1-a-s0-right-N|member|y2-0-1-a|N|kN|0|right|
|case-D-member-y2-0-1-a-s0-right-V2|member|y2-0-1-a|V2|kN|0|right|
|case-D-member-y2-0-1-a-s0-right-V3|member|y2-0-1-a|V3|kN|0|right|
|case-D-member-y2-0-1-a-s0-right-T|member|y2-0-1-a|T|kN.m|0|right|
|case-D-member-y2-0-1-a-s0-right-M2|member|y2-0-1-a|M2|kN.m|0|right|
|case-D-member-y2-0-1-a-s0-right-M3|member|y2-0-1-a|M3|kN.m|0|right|
|case-D-member-y2-0-1-b-s2.69258240357-left-N|member|y2-0-1-b|N|kN|2.692582403567252|left|
|case-D-member-y2-0-1-b-s2.69258240357-left-V2|member|y2-0-1-b|V2|kN|2.692582403567252|left|
|case-D-member-y2-0-1-b-s2.69258240357-left-V3|member|y2-0-1-b|V3|kN|2.692582403567252|left|
|case-D-member-y2-0-1-b-s2.69258240357-left-T|member|y2-0-1-b|T|kN.m|2.692582403567252|left|
|case-D-member-y2-0-1-b-s2.69258240357-left-M2|member|y2-0-1-b|M2|kN.m|2.692582403567252|left|
|case-D-member-y2-0-1-b-s2.69258240357-left-M3|member|y2-0-1-b|M3|kN.m|2.692582403567252|left|
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

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.
