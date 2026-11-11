## Mapping confirmed — Mapping

|Field|Value|
|---|---|
|Xg|Xs|
|Yg|-Zs|
|Zg|Ys|

## Mapping confirmed — Matrix

[[1, 0, 0], [0, 0, -1], [0, 1, 0]]

## Mapping confirmed — Local axes

|Field|Value|
|---|---|
|globalAxes|Right-handed XYZ; Z upward.|
|planarAxes|XZ plane: local x = i to j, local y = global +Y, local z = x cross y.|
|spatialAxes|local x = i to j; y = normalize(reference cross x); z = x cross y; reference vectors are explicit per member.|
|sectionRoll|y_new=cos(theta)*y+sin(theta)*z; z_new=-sin(theta)*y+cos(theta)*z; theta in degrees.|
|reactionNaming|Rz in the task means vertical support force Fz, not nodal rotation rz.|

## Mapping confirmed — Global output nodes

|Field|Value|
|---|---|
|roof|n2-0-2|
|base|n0-0-0|
