## Numerical inputs

|Field|Value|
|---|---|
|title|完整数值输入附表|
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
|n0-1|0|0|3.6|false|true|false|true|false|true|
|n1-1|6|0|3.6|false|true|false|true|false|true|
|n0-2|0|0|7.2|false|true|false|true|false|true|
|n1-2|6|0|7.2|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|c0-1|column|n0-0|n0-1|M1|C1|0|[0, 1, 0]|
|c1-1|column|n1-0|n1-1|M1|C1|0|[0, 1, 0]|
|b0-1|beam|n0-1|n1-1|M1|B1|0|[0, 1, 0]|
|c0-2|column|n0-1|n0-2|M1|C1|0|[0, 1, 0]|
|c1-2|column|n1-1|n1-2|M1|C1|0|[0, 1, 0]|
|b0-2|beam|n0-2|n1-2|M1|B1|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

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

|Load ID → element / node|reference_frame|type|wz|
|---|---|---|---|
|D-1 → b0-1, D-2 → b0-2|global|distributed|-60|

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

|id|location · id|component|unit|
|---|---|---|---|
|case-D-node-n0-1-ux|n0-1|ux|m|
|case-D-node-n0-1-uz|n0-1|uz|m|
|case-D-node-n1-1-ux|n1-1|ux|m|
|case-D-node-n1-1-uz|n1-1|uz|m|
|case-D-node-n0-2-ux|n0-2|ux|m|
|case-D-node-n0-2-uz|n0-2|uz|m|
|case-D-node-n1-2-ux|n1-2|ux|m|
|case-D-node-n1-2-uz|n1-2|uz|m|
|case-D-node-n0-0-ux|n0-0|ux|m|
|case-D-node-n0-0-uz|n0-0|uz|m|
|case-D-node-n1-0-ux|n1-0|ux|m|
|case-D-node-n1-0-uz|n1-0|uz|m|
|case-D-node-n0-0-Fx|n0-0|Fx|kN|
|case-D-node-n0-0-Fz|n0-0|Fz|kN|
|case-D-node-n0-0-My|n0-0|My|kN.m|
|case-D-node-n1-0-Fx|n1-0|Fx|kN|
|case-D-node-n1-0-Fz|n1-0|Fz|kN|
|case-D-node-n1-0-My|n1-0|My|kN.m|

Applies to every listed row: selection · kind = case; selection · id = D; location · kind = node.

## Requested outputs — Derived

|id|operands|description|
|---|---|---|
|D-drift-n0-0-n0-1-ux|["case-D-node-n0-1-ux", "case-D-node-n0-0-ux"]|n0-1 minus n0-0: ux; signed story displacement difference|
|D-drift-n0-0-n0-1-uz|["case-D-node-n0-1-uz", "case-D-node-n0-0-uz"]|n0-1 minus n0-0: uz; signed story displacement difference|
|D-drift-n0-1-n0-2-ux|["case-D-node-n0-2-ux", "case-D-node-n0-1-ux"]|n0-2 minus n0-1: ux; signed story displacement difference|
|D-drift-n0-1-n0-2-uz|["case-D-node-n0-2-uz", "case-D-node-n0-1-uz"]|n0-2 minus n0-1: uz; signed story displacement difference|
|D-drift-n1-0-n1-1-ux|["case-D-node-n1-1-ux", "case-D-node-n1-0-ux"]|n1-1 minus n1-0: ux; signed story displacement difference|
|D-drift-n1-0-n1-1-uz|["case-D-node-n1-1-uz", "case-D-node-n1-0-uz"]|n1-1 minus n1-0: uz; signed story displacement difference|
|D-drift-n1-1-n1-2-ux|["case-D-node-n1-2-ux", "case-D-node-n1-1-ux"]|n1-2 minus n1-1: ux; signed story displacement difference|
|D-drift-n1-1-n1-2-uz|["case-D-node-n1-2-uz", "case-D-node-n1-1-uz"]|n1-2 minus n1-1: uz; signed story displacement difference|

Applies to every listed row: operation = difference; unit = m.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Input decisions

源规划未给定材料及截面数值，现将属性附表明确冻结：Q355钢，E=206000 MPa，nu=0.30，G=E/[2(1+nu)]，密度7850 kg/m^3。实心矩形截面，B为局部y方向宽度、H为局部z方向高度；A、Iy、Iz、J采用附表明示值。采用Euler-Bernoulli弯曲，不计剪切变形；全部构件材料M1。除下列逐题说明另有规定外，梁B1宽0.30m、高0.60m；柱C1为0.50m方形。平面杆局部x由首节点指向末节点，局部y为全局+Y，局部z=x叉乘y；平面内力分量为N、V3、M2。未指定分量的节点位移向量报告ux、uz及转角ry；杆件内力为input.md指定侧的有符号截面合力。跨中观测点通过分段构件真实接入，分段保持原截面和线载强度。除明确支座释放外，全部节点刚接。

梁B1、柱C1；层间位移差定义为同列上节点减下节点，单位m，X和Z分量均列出；它不是层间位移角。面载说明仅用于交代60kN/m的来源，不另施加面载。
