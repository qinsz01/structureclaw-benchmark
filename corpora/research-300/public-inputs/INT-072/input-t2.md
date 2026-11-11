## Geometry t2

|Field|Value|
|---|---|
|totalBays|2|
|bayLengthsM|[5, 7]|
|groupR|b1-1, b1-2, b1-3|
|documentType|Public engineering input tables|

## Geometry t2 — Nodes

|id|x|z|restraints|
|---|---|---|---|
|n0-0|0|0|[true, true, true, true, true, true]|
|n1-0|5|0|[true, true, true, true, true, true]|
|n2-0|12|0|[true, true, true, true, true, true]|
|n0-1|0|3.3|[false, true, false, true, false, true]|
|n1-1|5|3.3|[false, true, false, true, false, true]|
|n2-1|12|3.3|[false, true, false, true, false, true]|
|n0-2|0|7.3|[false, true, false, true, false, true]|
|n1-2|5|7.3|[false, true, false, true, false, true]|
|n2-2|12|7.3|[false, true, false, true, false, true]|
|n0-3|0|10.4|[false, true, false, true, false, true]|
|n1-3|5|10.4|[false, true, false, true, false, true]|
|n2-3|12|10.4|[false, true, false, true, false, true]|

Applies to every listed row: y = 0.

## Geometry t2 — Members

|id|type|nodes|section|
|---|---|---|---|
|c0-1|column|["n0-0", "n0-1"]|C1|
|c1-1|column|["n1-0", "n1-1"]|C1|
|c2-1|column|["n2-0", "n2-1"]|C1|
|b0-1|beam|["n0-1", "n1-1"]|B1|
|b1-1|beam|["n1-1", "n2-1"]|B1|
|c0-2|column|["n0-1", "n0-2"]|C1|
|c1-2|column|["n1-1", "n1-2"]|C1|
|c2-2|column|["n2-1", "n2-2"]|C1|
|b0-2|beam|["n0-2", "n1-2"]|B1|
|b1-2|beam|["n1-2", "n2-2"]|B1|
|c0-3|column|["n0-2", "n0-3"]|C1|
|c1-3|column|["n1-2", "n1-3"]|C1|
|c2-3|column|["n2-2", "n2-3"]|C1|
|b0-3|beam|["n0-3", "n1-3"]|B1|
|b1-3|beam|["n1-3", "n2-3"]|B1|

Applies to every listed row: material = M1; rotation_angle = 0.

## Geometry t2 — Load case table — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Geometry t2 — Load case table — D — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-udl-b0-1 → b0-1, D-udl-b1-1 → b1-1, D-udl-b0-2 → b0-2, D-udl-b1-2 → b1-2, D-udl-b0-3 → b0-3, D-udl-b1-3 → b1-3|global|distributed|-8|

## Geometry t2 — Load case table — L

|Field|Value|
|---|---|
|id|L|
|type|live|

## Geometry t2 — Load case table — L — Loads

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|L-udl-b1-1 → b1-1, L-udl-b1-2 → b1-2, L-udl-b1-3 → b1-3|global|distributed|-6|
