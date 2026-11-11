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
|base|0|0|0|true|true|true|true|true|true|
|interface|0|0|3|false|true|false|true|false|true|
|top|0|0|8|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|lower-column|column|base|interface|M1|C1|0|[0, 1, 0]|
|upper-column|column|interface|top|M1|C2|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|shape · B|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|
|C1|500.0|0.25|0.005208333333333333|0.005208333333333333|0.008802083333333334|
|C2|350.0|0.175|0.003645833333333333|0.0017864583333333328|0.0040575733442708315|

Applies to every listed row: type = rectangular; shape · H = 500.0; name = id; shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|reference_frame|type|fx|fz|
|---|---|---|---|---|
|D-1 → top|global|nodal|25|-500|

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
|derived|[]|
|figures|[]|
|interactions|[]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-top-ux|node|top|ux|m|—|—|
|case-D-node-top-uz|node|top|uz|m|—|—|
|case-D-node-interface-ux|node|interface|ux|m|—|—|
|case-D-node-interface-uz|node|interface|uz|m|—|—|
|case-D-node-interface-ry|node|interface|ry|rad|—|—|
|case-D-member-lower-column-s3-left-N|member|lower-column|N|kN|3|left|
|case-D-member-lower-column-s3-left-V3|member|lower-column|V3|kN|3|left|
|case-D-member-lower-column-s3-left-M2|member|lower-column|M2|kN.m|3|left|
|case-D-member-upper-column-s0-right-N|member|upper-column|N|kN|0|right|
|case-D-member-upper-column-s0-right-V3|member|upper-column|V3|kN|0|right|
|case-D-member-upper-column-s0-right-M2|member|upper-column|M2|kN.m|0|right|
|case-D-node-base-Fx|node|base|Fx|kN|—|—|
|case-D-node-base-Fz|node|base|Fz|kN|—|—|
|case-D-node-base-My|node|base|My|kN.m|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Physical definitions

源表没有给定材料类别与 C1/C2 尺寸；本题明确补齐为 Q355 钢，C1=500×500 mm、C2=350×500 mm 实心矩形理想化截面，两段 E 相同而 A、Iy、Iz、J 各自不同。
下段长度为 3 m，上段长度为 5 m；截面界面仅一个共享节点，ux、uz、ry 连续且无释放。
界面端力明确为 lower-column 的位置 3 m、side=left，以及 upper-column 的位置 0 m、side=right；保持两侧标签及统一截面内力符号。
杆件采用一阶线弹性 Euler-Bernoulli 弯曲、轴向变形及有限 Saint-Venant 扭转刚度；不计剪切变形，自重关闭。本题不做二阶、屈曲、承载力或配筋分析。
截面 A、Iy、Iz、J 为附表中的显式 SI 数值，不以软件默认截面属性替换；采用矩形截面时 J 使用输入表给定的冻结近似值。

## Output scope — Required outputs

|id|description|quantityIds|
|---|---|---|
|column-top-displacements|柱顶全局 ux、uz|["case-D-node-top-ux", "case-D-node-top-uz"]|
|interface-displacement-and-rotation|z=3 m 共用界面节点的 ux、uz、ry|["case-D-node-interface-ux", "case-D-node-interface-uz", "case-D-node-interface-ry"]|
|interface-end-forces|下段 j 端及上段 i 端的局部 N、V3、M2|["case-D-member-lower-column-s3-left-N", "case-D-member-lower-column-s3-left-V3", "case-D-member-lower-column-s3-left-M2", "case-D-member-upper-column-s0-right-N", "case-D-member-upper-column-s0-right-V3", "case-D-member-upper-column-s0-right-M2"]|
|base-reactions|柱底全局反力 Fx、Fz 及反力矩 My|["case-D-node-base-Fx", "case-D-node-base-Fz", "case-D-node-base-My"]|

Applies to every listed row: state = 1; kind = numerical.
