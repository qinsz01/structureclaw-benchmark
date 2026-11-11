## Numerical inputs

|Field|Value|
|---|---|
|title|Complete numerical input appendix|
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
|n0-1|0|0|3.3|false|true|false|true|false|true|
|n1-1|6|0|3.3|false|true|false|true|false|true|
|n0-2|0|0|6.6|false|true|false|true|false|true|
|n1-2|6|0|6.6|false|true|false|true|false|true|
|n0-3|0|0|9.9|false|true|false|true|false|true|
|n1-3|6|0|9.9|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|C30|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|C30|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|C30|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|C30|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|C30|C1|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|C30|B1|0|[0, 1, 0]|
|c0-3|column|n0-2|n0-3|C30|C1|0|[0, 1, 0]|
|c1-3|column|n1-2|n1-3|C30|C1|0|[0, 1, 0]|
|b0-3|beam|n0-3|n1-3|C30|B1|0|[0, 1, 0]|

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
|D-1 → b0-1|-12|
|D-2 → b0-2|-10|
|D-3 → b0-3|-8|

Applies to every listed row: reference_frame = global; type = distributed.

## Numerical inputs — Load cases — W+

|Field|Value|
|---|---|
|id|W+|
|type|wind|

## Numerical inputs — Load cases — W+ — Loads

|Load ID → element / node|fx|
|---|---|
|W+-1 → n1-1|10|
|W+-2 → n1-2|15|
|W+-3 → n1-3|20|

Applies to every listed row: reference_frame = global; type = nodal.

## Numerical inputs — Load cases — W-

|Field|Value|
|---|---|
|id|W-|
|type|wind|

## Numerical inputs — Load cases — W- — Loads

|Load ID → element / node|fx|
|---|---|
|W--1 → n1-1|-10|
|W--2 → n1-2|-15|
|W--3 → n1-3|-20|

Applies to every listed row: reference_frame = global; type = nodal.

## Numerical inputs — Load combinations

|id|factors · W+|factors · W-|
|---|---|---|
|C0|—|—|
|C+|1|—|
|C-|—|1|

Applies to every listed row: factors · D = 1.

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

|id|selection · id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|---|
|combination-C0-node-n0-1-ux|C0|node|n0-1|ux|m|—|—|
|combination-C0-node-n1-1-ux|C0|node|n1-1|ux|m|—|—|
|combination-C0-node-n0-2-ux|C0|node|n0-2|ux|m|—|—|
|combination-C0-node-n1-2-ux|C0|node|n1-2|ux|m|—|—|
|combination-C0-node-n0-3-ux|C0|node|n0-3|ux|m|—|—|
|combination-C0-node-n1-3-ux|C0|node|n1-3|ux|m|—|—|
|combination-C0-node-n0-0-ux|C0|node|n0-0|ux|m|—|—|
|combination-C0-node-n1-0-ux|C0|node|n1-0|ux|m|—|—|
|combination-C0-node-n0-0-Fx|C0|node|n0-0|Fx|kN|—|—|
|combination-C0-node-n0-0-Fz|C0|node|n0-0|Fz|kN|—|—|
|combination-C0-node-n0-0-My|C0|node|n0-0|My|kN.m|—|—|
|combination-C0-node-n1-0-Fx|C0|node|n1-0|Fx|kN|—|—|
|combination-C0-node-n1-0-Fz|C0|node|n1-0|Fz|kN|—|—|
|combination-C0-node-n1-0-My|C0|node|n1-0|My|kN.m|—|—|
|combination-C0-member-c0-1-s0-right-M2|C0|member|c0-1|M2|kN.m|0|right|
|combination-C0-member-c0-1-s3.3-left-M2|C0|member|c0-1|M2|kN.m|3.3|left|
|combination-C0-member-c1-1-s0-right-M2|C0|member|c1-1|M2|kN.m|0|right|
|combination-C0-member-c1-1-s3.3-left-M2|C0|member|c1-1|M2|kN.m|3.3|left|
|combination-C+-node-n0-1-ux|C+|node|n0-1|ux|m|—|—|
|combination-C+-node-n1-1-ux|C+|node|n1-1|ux|m|—|—|
|combination-C+-node-n0-2-ux|C+|node|n0-2|ux|m|—|—|
|combination-C+-node-n1-2-ux|C+|node|n1-2|ux|m|—|—|
|combination-C+-node-n0-3-ux|C+|node|n0-3|ux|m|—|—|
|combination-C+-node-n1-3-ux|C+|node|n1-3|ux|m|—|—|
|combination-C+-node-n0-0-ux|C+|node|n0-0|ux|m|—|—|
|combination-C+-node-n1-0-ux|C+|node|n1-0|ux|m|—|—|
|combination-C+-node-n0-0-Fx|C+|node|n0-0|Fx|kN|—|—|
|combination-C+-node-n0-0-Fz|C+|node|n0-0|Fz|kN|—|—|
|combination-C+-node-n0-0-My|C+|node|n0-0|My|kN.m|—|—|
|combination-C+-node-n1-0-Fx|C+|node|n1-0|Fx|kN|—|—|
|combination-C+-node-n1-0-Fz|C+|node|n1-0|Fz|kN|—|—|
|combination-C+-node-n1-0-My|C+|node|n1-0|My|kN.m|—|—|
|combination-C+-member-c0-1-s0-right-M2|C+|member|c0-1|M2|kN.m|0|right|
|combination-C+-member-c0-1-s3.3-left-M2|C+|member|c0-1|M2|kN.m|3.3|left|
|combination-C+-member-c1-1-s0-right-M2|C+|member|c1-1|M2|kN.m|0|right|
|combination-C+-member-c1-1-s3.3-left-M2|C+|member|c1-1|M2|kN.m|3.3|left|
|combination-C--node-n0-1-ux|C-|node|n0-1|ux|m|—|—|
|combination-C--node-n1-1-ux|C-|node|n1-1|ux|m|—|—|
|combination-C--node-n0-2-ux|C-|node|n0-2|ux|m|—|—|
|combination-C--node-n1-2-ux|C-|node|n1-2|ux|m|—|—|
|combination-C--node-n0-3-ux|C-|node|n0-3|ux|m|—|—|
|combination-C--node-n1-3-ux|C-|node|n1-3|ux|m|—|—|
|combination-C--node-n0-0-ux|C-|node|n0-0|ux|m|—|—|
|combination-C--node-n1-0-ux|C-|node|n1-0|ux|m|—|—|
|combination-C--node-n0-0-Fx|C-|node|n0-0|Fx|kN|—|—|
|combination-C--node-n0-0-Fz|C-|node|n0-0|Fz|kN|—|—|
|combination-C--node-n0-0-My|C-|node|n0-0|My|kN.m|—|—|
|combination-C--node-n1-0-Fx|C-|node|n1-0|Fx|kN|—|—|
|combination-C--node-n1-0-Fz|C-|node|n1-0|Fz|kN|—|—|
|combination-C--node-n1-0-My|C-|node|n1-0|My|kN.m|—|—|
|combination-C--member-c0-1-s0-right-M2|C-|member|c0-1|M2|kN.m|0|right|
|combination-C--member-c0-1-s3.3-left-M2|C-|member|c0-1|M2|kN.m|3.3|left|
|combination-C--member-c1-1-s0-right-M2|C-|member|c1-1|M2|kN.m|0|right|
|combination-C--member-c1-1-s3.3-left-M2|C-|member|c1-1|M2|kN.m|3.3|left|

Applies to every listed row: selection · kind = combination.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|C0-drift-n0-0-n0-1-ux|["combination-C0-node-n0-1-ux", "combination-C0-node-n0-0-ux"]|n0-1 minus n0-0: ux; signed story displacement difference|
|C0-drift-n1-0-n1-1-ux|["combination-C0-node-n1-1-ux", "combination-C0-node-n1-0-ux"]|n1-1 minus n1-0: ux; signed story displacement difference|
|C0-drift-n0-1-n0-2-ux|["combination-C0-node-n0-2-ux", "combination-C0-node-n0-1-ux"]|n0-2 minus n0-1: ux; signed story displacement difference|
|C0-drift-n1-1-n1-2-ux|["combination-C0-node-n1-2-ux", "combination-C0-node-n1-1-ux"]|n1-2 minus n1-1: ux; signed story displacement difference|
|C0-drift-n0-2-n0-3-ux|["combination-C0-node-n0-3-ux", "combination-C0-node-n0-2-ux"]|n0-3 minus n0-2: ux; signed story displacement difference|
|C0-drift-n1-2-n1-3-ux|["combination-C0-node-n1-3-ux", "combination-C0-node-n1-2-ux"]|n1-3 minus n1-2: ux; signed story displacement difference|
|C+-drift-n0-0-n0-1-ux|["combination-C+-node-n0-1-ux", "combination-C+-node-n0-0-ux"]|n0-1 minus n0-0: ux; signed story displacement difference|
|C+-drift-n1-0-n1-1-ux|["combination-C+-node-n1-1-ux", "combination-C+-node-n1-0-ux"]|n1-1 minus n1-0: ux; signed story displacement difference|
|C+-drift-n0-1-n0-2-ux|["combination-C+-node-n0-2-ux", "combination-C+-node-n0-1-ux"]|n0-2 minus n0-1: ux; signed story displacement difference|
|C+-drift-n1-1-n1-2-ux|["combination-C+-node-n1-2-ux", "combination-C+-node-n1-1-ux"]|n1-2 minus n1-1: ux; signed story displacement difference|
|C+-drift-n0-2-n0-3-ux|["combination-C+-node-n0-3-ux", "combination-C+-node-n0-2-ux"]|n0-3 minus n0-2: ux; signed story displacement difference|
|C+-drift-n1-2-n1-3-ux|["combination-C+-node-n1-3-ux", "combination-C+-node-n1-2-ux"]|n1-3 minus n1-2: ux; signed story displacement difference|
|C--drift-n0-0-n0-1-ux|["combination-C--node-n0-1-ux", "combination-C--node-n0-0-ux"]|n0-1 minus n0-0: ux; signed story displacement difference|
|C--drift-n1-0-n1-1-ux|["combination-C--node-n1-1-ux", "combination-C--node-n1-0-ux"]|n1-1 minus n1-0: ux; signed story displacement difference|
|C--drift-n0-1-n0-2-ux|["combination-C--node-n0-2-ux", "combination-C--node-n0-1-ux"]|n0-2 minus n0-1: ux; signed story displacement difference|
|C--drift-n1-1-n1-2-ux|["combination-C--node-n1-2-ux", "combination-C--node-n1-1-ux"]|n1-2 minus n1-1: ux; signed story displacement difference|
|C--drift-n0-2-n0-3-ux|["combination-C--node-n0-3-ux", "combination-C--node-n0-2-ux"]|n0-3 minus n0-2: ux; signed story displacement difference|
|C--drift-n1-2-n1-3-ux|["combination-C--node-n1-3-ux", "combination-C--node-n1-2-ux"]|n1-3 minus n1-2: ux; signed story displacement difference|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

Use the specified engine for first-order linear elastic static analysis with Euler-Bernoulli bending (no shear deformation). Self weight, P-Delta, rigid floors, rigid offsets and construction stages are OFF. Coordinates: global XYZ, Z upward; planar models lie in XZ. Length/displacement m; forces kN; moments kN*m; distributed force kN/m of actual member length; E/G MPa; density kg/m^3; A m^2; Iy/Iz/J m^4; shape dimensions mm; rotations rad. Restraint order ux,uy,uz,rx,ry,rz; true means fixed. All beam/column joints are rigid unless explicit supports say otherwise; truss members carry axial force only. Local x follows ordered member nodes. For 3D, local y = normalized(reference vector cross local x); local z = local x cross local y, then apply the stated rotation_angle about local x. For 2D before any section roll, local y = global +Y and local z = local x cross local y; apply rotation_angle about local x when present. Iy is the inertia about local y. Planar metadata reference vectors are not the 3D cross-product vectors. State local-to-global transforms in results. Member station is measured from the first node; side selects the limiting cut. Preserve signed results and case/combination labels. N is positive in tension. For local member-end resisting actions ordered N,V2,V3,T,M2,M3, the requested signed section resultants use multipliers (-1,+1,+1,-1,-1,-1) at the first-node end and (+1,-1,-1,+1,+1,+1) at the second-node end; do not replace section resultants by unsigned extrema. Report every item in input.md, including derived quantities and governing signed operand/selection for max_abs. Save executable input, engine/version, /log and raw indexed results. These are execution requirements, not supplied evidence. The complete input.md is a public numerical appendix, not a result file.
