## Geometry

|Field|Value|
|---|---|
|units|m|

## Geometry — Nodes

|id|x|y|z|restraints|
|---|---|---|---|---|
|A|0|0|0|[true, true, true, true, true, true]|
|B|4|0|0|[false, true, true, true, true, true]|
|C|2|3.4641016151377544|0|[false, false, true, true, true, true]|
|D|2|1.1547005383792515|3|[false, false, false, true, true, true]|

## Geometry — Elements

|id|nodes|
|---|---|
|AB|["A", "B"]|
|BC|["B", "C"]|
|CA|["C", "A"]|
|AD|["A", "D"]|
|BD|["B", "D"]|
|CD|["C", "D"]|

Applies to every listed row: type = truss; material = M1; section = T1.

## Properties

|Field|Value|
|---|---|
|load_combinations|[]|
|analysis|first-order linear elastic Euler-Bernoulli frame and axial-only truss|
|restraintConvention|[ux,uy,uz,rx,ry,rz]; true = zero prescribed displacement; false = free active DOF; planar inactive DOFs and truss rotations are explicitly suppressed|
|sectionRollConvention|ey_new=cos(theta)*ey+sin(theta)*ez; ez_new=-sin(theta)*ey+cos(theta)*ez; theta in degrees about i-to-j|

## Properties — Units

|Field|Value|
|---|---|
|E|MPa|
|G|MPa|
|rho|kg/m3|
|shape|mm|
|A|m2|
|Iy|m4|
|Iz|m4|
|J|m4|

## Properties — Coordinate system

|Field|Value|
|---|---|
|dimension|3d|
|plane|null|
|semantics|global-z-up|
|version|1|
|dof_order|["ux", "uy", "uz", "rx", "ry", "rz"]|

## Properties — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|steel|steel|206000|79230.76923076923|0.3|7850|

## Properties — Sections

|id|type|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|
|T1|rectangular|100.0|100.0|0.01|8.333333333333334e-06|8.333333333333334e-06|1.4083333333333335e-05|

Applies to every listed row: name = id; shape · kind = type.

## Properties — Analysis control

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|

## Properties — Local axes — Element reference vectors

|Field|Value|
|---|---|
|AB|[0, 0, 1]|
|BC|[0, 0, 1]|
|CA|[0, 0, 1]|
|AD|[0, 0, 1]|
|BD|[0, 0, 1]|
|CD|[0, 0, 1]|

## Loads

|Field|Value|
|---|---|
|load_combinations|[]|
|distributedLoadMeasure|per actual member length, global vector; start/end in metres from i unless units above specify mm|

## Loads — Units

|Field|Value|
|---|---|
|force|kN|
|moment|kN.m|
|lineLoad|kN/m|
|position|m|

## Loads — Load cases — LC1

|Field|Value|
|---|---|
|id|LC1|
|type|dead|

## Loads — Load cases — LC1 — Loads

|Load ID → element / node|type|reference_frame|fz|
|---|---|---|---|
|P-D → D|nodal|global|-30|

## Requested outputs

|Field|Value|
|---|---|
|derived|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case:LC1:node:D:ux|node|D|ux|m|—|—|
|case:LC1:node:D:uy|node|D|uy|m|—|—|
|case:LC1:node:D:uz|node|D|uz|m|—|—|
|case:LC1:member:AB:N@2:right|member|AB|N|kN|2.0|right|
|case:LC1:member:BC:N@2:right|member|BC|N|kN|1.9999999999999998|right|
|case:LC1:member:CA:N@2:right|member|CA|N|kN|1.9999999999999998|right|
|case:LC1:member:AD:N@1.8929694486:right|member|AD|N|kN|1.8929694486000912|right|
|case:LC1:member:BD:N@1.8929694486:right|member|BD|N|kN|1.8929694486000912|right|
|case:LC1:member:CD:N@1.8929694486:right|member|CD|N|kN|1.8929694486000912|right|
|case:LC1:node:A:Fx|node|A|Fx|kN|—|—|
|case:LC1:node:A:Fy|node|A|Fy|kN|—|—|
|case:LC1:node:A:Fz|node|A|Fz|kN|—|—|
|case:LC1:node:B:Fx|node|B|Fx|kN|—|—|
|case:LC1:node:B:Fy|node|B|Fy|kN|—|—|
|case:LC1:node:B:Fz|node|B|Fz|kN|—|—|
|case:LC1:node:C:Fx|node|C|Fx|kN|—|—|
|case:LC1:node:C:Fy|node|C|Fy|kN|—|—|
|case:LC1:node:C:Fz|node|C|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = LC1.
