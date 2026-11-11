## Source input

|Field|Value|
|---|---|
|analysisMethod|First-order linear elastic Euler-Bernoulli beam/column and axial-only truss analysis.|
|localAxes|Transform the source reference vector and each i-to-j member vector with the confirmed mapping; local x=i-to-j, local y=normalize(reference cross x), local z=x cross y; all section rolls zero.|
|sourceLoadPlacement|The roof force and equipment moment act at source (Xs,Ys,Zs)=(10,7,5) m. The moment is about +Ys, not +Zs.|
|outputLocations|Roof joint: largest global Z, then largest global X, then largest global Y. Base: source origin (0,0,0), on the leftmost column line.|
|documentType|Public engineering input tables|
|combinationTable|[]|

## Source input — Units

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

## Source input — Source coordinate system

|Field|Value|
|---|---|
|verticalAxis|Ys|
|sourceDOFOrder|["uXs", "uYs", "uZs", "rXs", "rYs", "rZs"]|
|SIGN|null|

## Source input — Source coordinate system — Mapping to global

|Field|Value|
|---|---|
|Xg|Xs|
|Yg|SIGN * Zs|
|Zg|Ys|

## Source input — Source reference vectors

|Field|Value|
|---|---|
|c0-0-1|[1, 0, 0]|
|x0-0-1|[0, 1, 0]|
|y0-0-1|[0, 1, 0]|
|c0-1-1|[1, 0, 0]|
|x0-1-1|[0, 1, 0]|
|c1-0-1|[1, 0, 0]|
|x1-0-1|[0, 1, 0]|
|y1-0-1|[0, 1, 0]|
|c1-1-1|[1, 0, 0]|
|x1-1-1|[0, 1, 0]|
|c2-0-1|[1, 0, 0]|
|y2-0-1|[0, 1, 0]|
|c2-1-1|[1, 0, 0]|
|c0-0-2|[1, 0, 0]|
|x0-0-2|[0, 1, 0]|
|y0-0-2|[0, 1, 0]|
|c0-1-2|[1, 0, 0]|
|x0-1-2|[0, 1, 0]|
|c1-0-2|[1, 0, 0]|
|x1-0-2|[0, 1, 0]|
|y1-0-2|[0, 1, 0]|
|c1-1-2|[1, 0, 0]|
|x1-1-2|[0, 1, 0]|
|c2-0-2|[1, 0, 0]|
|y2-0-2|[0, 1, 0]|
|c2-1-2|[1, 0, 0]|

## Source input — Nodes

|id|Xs|Ys|Zs|sourceRestraints|
|---|---|---|---|---|
|n0-0-0|0|0|0|[true, true, true, true, true, true]|
|n0-1-0|0|0|5|[true, true, true, true, true, true]|
|n1-0-0|4|0|0|[true, true, true, true, true, true]|
|n1-1-0|4|0|5|[true, true, true, true, true, true]|
|n2-0-0|10|0|0|[true, true, true, true, true, true]|
|n2-1-0|10|0|5|[true, true, true, true, true, true]|
|n0-0-1|0|3.5|0|[false, false, false, false, false, false]|
|n0-1-1|0|3.5|5|[false, false, false, false, false, false]|
|n1-0-1|4|3.5|0|[false, false, false, false, false, false]|
|n1-1-1|4|3.5|5|[false, false, false, false, false, false]|
|n2-0-1|10|3.5|0|[false, false, false, false, false, false]|
|n2-1-1|10|3.5|5|[false, false, false, false, false, false]|
|n0-0-2|0|7|0|[false, false, false, false, false, false]|
|n0-1-2|0|7|5|[false, false, false, false, false, false]|
|n1-0-2|4|7|0|[false, false, false, false, false, false]|
|n1-1-2|4|7|5|[false, false, false, false, false, false]|
|n2-0-2|10|7|0|[false, false, false, false, false, false]|
|n2-1-2|10|7|5|[false, false, false, false, false, false]|

## Source input — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-0-1|column|["n0-0-0", "n0-0-1"]|C1|
|x0-0-1|beam|["n0-0-1", "n1-0-1"]|BX|
|y0-0-1|beam|["n0-0-1", "n0-1-1"]|BY|
|c0-1-1|column|["n0-1-0", "n0-1-1"]|C1|
|x0-1-1|beam|["n0-1-1", "n1-1-1"]|BX|
|c1-0-1|column|["n1-0-0", "n1-0-1"]|C1|
|x1-0-1|beam|["n1-0-1", "n2-0-1"]|BX|
|y1-0-1|beam|["n1-0-1", "n1-1-1"]|BY|
|c1-1-1|column|["n1-1-0", "n1-1-1"]|C1|
|x1-1-1|beam|["n1-1-1", "n2-1-1"]|BX|
|c2-0-1|column|["n2-0-0", "n2-0-1"]|C1|
|y2-0-1|beam|["n2-0-1", "n2-1-1"]|BY|
|c2-1-1|column|["n2-1-0", "n2-1-1"]|C1|
|c0-0-2|column|["n0-0-1", "n0-0-2"]|C1|
|x0-0-2|beam|["n0-0-2", "n1-0-2"]|BX|
|y0-0-2|beam|["n0-0-2", "n0-1-2"]|BY|
|c0-1-2|column|["n0-1-1", "n0-1-2"]|C1|
|x0-1-2|beam|["n0-1-2", "n1-1-2"]|BX|
|c1-0-2|column|["n1-0-1", "n1-0-2"]|C1|
|x1-0-2|beam|["n1-0-2", "n2-0-2"]|BX|
|y1-0-2|beam|["n1-0-2", "n1-1-2"]|BY|
|c1-1-2|column|["n1-1-1", "n1-1-2"]|C1|
|x1-1-2|beam|["n1-1-2", "n2-1-2"]|BX|
|c2-0-2|column|["n2-0-1", "n2-0-2"]|C1|
|y2-0-2|beam|["n2-0-2", "n2-1-2"]|BY|
|c2-1-2|column|["n2-1-1", "n2-1-2"]|C1|

Applies to every listed row: material = M1.

## Source input — Material table

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|C35|concrete|31500|13125.0|0.2|2500|

## Source input — Section table

|id|shape · B|shape · H|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|
|BX|300.0|600.0|0.18|0.0053999999999999986|0.0013499999999999996|0.0037078593749999985|
|BY|300.0|500.0|0.15|0.0031249999999999997|0.001125|0.0028173707999999994|
|C1|400.0|500.0|0.2|0.004166666666666667|0.0026666666666666674|0.005474167466666667|

Applies to every listed row: type = rectangular; name = id; shape · kind = type.

## Source input — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Source input — Load case table — D — Loads

|Load ID → element / node|type|wYs|FXs|MYs|
|---|---|---|---|---|
|D-x0-0-1 → x0-0-1, D-y0-0-1 → y0-0-1, D-x0-1-1 → x0-1-1, D-x1-0-1 → x1-0-1, D-y1-0-1 → y1-0-1, D-x1-1-1 → x1-1-1, D-y2-0-1 → y2-0-1, D-x0-0-2 → x0-0-2, D-y0-0-2 → y0-0-2, D-x0-1-2 → x0-1-2, D-x1-0-2 → x1-0-2, D-y1-0-2 → y1-0-2, D-x1-1-2 → x1-1-2, D-y2-0-2 → y2-0-2|distributed|-6|—|—|
|roof-force → n2-1-2|nodal|—|12|—|
|equipment-moment → n2-1-2|nodal|—|—|6|

## Source input — Analysis settings

|Field|Value|
|---|---|
|self_weight|false|
|rigid_floor|false|
|p_delta|false|
|rigid_offsets|false|
|construction_stage|false|
