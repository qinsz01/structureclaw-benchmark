## Input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Timoshenko beam/column and axial-only truss analysis.|
|roofLoadMembers|["y0-0-1", "y1-0-1", "y2-0-1"]|
|loadBasis|Global -Z 5 kN/m of actual member length on the three sloping Y beams; X roof edge beams have no added line load.|
|documentType|Public engineering input tables|
|combinationTable|[]|

## Input — Units

|Field|Value|
|---|---|
|coordinates|m|
|member_length|m|
|E|MPa|
|G|MPa|
|rho|kg/m3|
|A|m2|
|Iy|m4|
|Iz|m4|
|J|m4|
|shape|mm|
|force|kN|
|moment|kN.m|
|line_load|kN/m of actual member length|
|rotation_angle|degree|
|displacement|m|

## Input — Axis definitions

|Field|Value|
|---|---|
|globalAxes|Right-handed XYZ; Z upward.|
|planarAxes|XZ plane: local x = i to j, local y = global +Y, local z = x cross y.|
|spatialAxes|local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.|
|sectionRoll|y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.|
|reactionNaming|Rz in the task means vertical support force Fz, not nodal rotation rz.|

## Input — Missing column

|Field|Value|
|---|---|
|x|6|
|y|0|
|roofJoint|n1-0-1|

## Input — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|n0-0-0|0|0|0|[true, true, true, true, true, true]|
|n0-0-1|0|0|6|[false, false, false, false, false, false]|
|n0-1-0|0|5|0|[true, true, true, true, true, true]|
|n0-1-1|0|5|8|[false, false, false, false, false, false]|
|n1-0-1|6|0|6|[false, false, false, false, false, false]|
|n1-1-0|6|5|0|[true, true, true, true, true, true]|
|n1-1-1|6|5|8|[false, false, false, false, false, false]|
|n2-0-0|12|0|0|[true, true, true, true, true, true]|
|n2-0-1|12|0|6|[false, false, false, false, false, false]|
|n2-1-0|12|5|0|[true, true, true, true, true, true]|
|n2-1-1|12|5|8|[false, false, false, false, false, false]|

## Input — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-0-1|column|["n0-0-0", "n0-0-1"]|C1|
|c0-1-1|column|["n0-1-0", "n0-1-1"]|C1|
|c1-1-1|column|["n1-1-0", "n1-1-1"]|C1|
|c2-0-1|column|["n2-0-0", "n2-0-1"]|C1|
|c2-1-1|column|["n2-1-0", "n2-1-1"]|C1|
|y0-0-1|beam|["n0-0-1", "n0-1-1"]|BY|
|x0-0-1|beam|["n0-0-1", "n1-0-1"]|BX|
|x0-1-1|beam|["n0-1-1", "n1-1-1"]|BX|
|y1-0-1|beam|["n1-0-1", "n1-1-1"]|BY|
|x1-0-1|beam|["n1-0-1", "n2-0-1"]|BX|
|x1-1-1|beam|["n1-1-1", "n2-1-1"]|BX|
|y2-0-1|beam|["n2-0-1", "n2-1-1"]|BY|

Applies to every listed row: material = M1.

## Input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Input — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|BX|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|BY|300.0|500.0|0.15|0.0031249999999999997|0.001125|0.0028173707999999994|
|C1|400.0|500.0|0.2|0.004166666666666667|0.0026666666666666674|0.005474167466666667|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load case table — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-y0-0-1 → y0-0-1, D-y1-0-1 → y1-0-1, D-y2-0-1 → y2-0-1|global|distributed|-5|

## Input — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Input — Coordinate contract

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Input — Member axis data — Element reference vectors

|Field|Value|
|---|---|
|c0-0-1|[1, 0, 0]|
|c0-1-1|[1, 0, 0]|
|c1-1-1|[1, 0, 0]|
|c2-0-1|[1, 0, 0]|
|c2-1-1|[1, 0, 0]|
|y0-0-1|[0, 0, 1]|
|x0-0-1|[0, 0, 1]|
|x0-1-1|[0, 0, 1]|
|y1-0-1|[0, 0, 1]|
|x1-0-1|[0, 0, 1]|
|x1-1-1|[0, 0, 1]|
|y2-0-1|[0, 0, 1]|

## Native analysis conventions

Commercial elastic analysis convention: commercial-linear-static-v2

Use the specified native engine for first-order, small-displacement, linear
elastic static analysis with Timoshenko bending. For every beam and column,
the prescribed effective shear areas are Asy = Asz = 5*A/6, in m^2. A is the
explicit cross-sectional area in the currently available property appendix;
Asy acts for local-y shear V2 and Asz for local-z shear V3. This is a prescribed
benchmark idealization, including generalized numerical sections, rather than
an inference from a section name. Apply it to each newly supplied or edited
section. Truss/brace members retain their specified axial-only behavior.

Retain the supplied E, G, A, Iy, Iz and J, geometry, connectivity, supports,
loads and load selections. Use gross uncracked concrete stiffness where stated.
Preserve the stated local axes, member-end cut signs and units. Self-weight,
rigid floors, rigid offsets, P-Delta and construction stages remain off.

Use explicit elastic stiffness rather than silently substituting a native
material grade's defaults. A native representation using equivalent EA,
G*Asy, G*Asz, GJ, E*Iy and E*Iz must retain the supplied physical definitions
and report the actual native material/section values, modifiers and numerical
serialization differences. Equivalent elastic stiffness does not assert
identical literal material fields or qualify stress/design calculations.
Retain native input, settings, engine/version, logs and raw result evidence.
This appendix supplies analysis inputs, not computed answers or acceptance.
