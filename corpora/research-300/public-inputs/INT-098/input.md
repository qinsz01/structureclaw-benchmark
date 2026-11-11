## Input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|documentType|Public engineering input tables|
|combinationTable|[]|
|memberAxisData|{}|

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
|globalAxes|Right-handed XYZ, Z upward.|
|conflict|The Iy/Iz table and the local-axis annotation have interchanged labels. Which assignment and reference direction is authoritative has not yet been confirmed.|
|reactionNaming|Rz means vertical support reaction Fz.|

## Input — Section axis annotation

|Field|Value|
|---|---|
|candidateIy|0.0031249999999999997|
|candidateIz|0.001125|
|unit|m4|
|authoritative|null|

## Input — Nodes

|id|z|restraints|
|---|---|---|
|base|0|[true, true, true, true, true, true]|
|mid|3|[false, false, false, false, false, false]|
|top|6|[false, false, false, false, false, false]|

Applies to every listed row: x = 0; y = 0.

## Input — Members

|id|nodes|
|---|---|
|column1|["base", "mid"]|
|column2|["mid", "top"]|

Applies to every listed row: type = column; material = M1; section = C1.

## Input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Input — Section table

|id|type|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|
|C1|general|0.15|0.001125|0.0031249999999999997|0.0028173707999999994|

Applies to every listed row: name = id.

## Input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Input — Load case table — D — Loads

|Load ID → element / node|fx|fy|fz|
|---|---|---|---|
|top-load → top|20|15|-400|
|mid-lateral → mid|-8|—|—|

Applies to every listed row: reference_frame = global; type = nodal.

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
