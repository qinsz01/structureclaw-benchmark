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
|mid|0|0|2.5|false|true|false|true|false|true|
|top|0|0|5|false|true|false|true|false|true|

## Numerical inputs — Members

|id|kind|start_node|end_node|material_id|section_id|roll_degrees|axis_reference_vector|
|---|---|---|---|---|---|---|---|
|lower-column|column|base|mid|M1|HW300|0|[0, 1, 0]|
|upper-column|column|mid|top|M1|HW300|0|[0, 1, 0]|

## Numerical inputs — Materials

|id|name|type|E|G|nu|rho|
|---|---|---|---|---|---|---|
|M1|Q355|steel|206000|79230.76923076923|0.3|7850|

## Numerical inputs — Sections

|id|name|type|shape · H|shape · B|shape · tw|shape · tf|properties · A|properties · Iy|properties · Iz|properties · J|
|---|---|---|---|---|---|---|---|---|---|---|
|HW300|HW300x300|H|300|300|10|15|0.011699999999999999|0.00019932749999999983|6.752249999999999e-05|7.649999999999999e-07|

Applies to every listed row: shape · kind = type.

## Numerical inputs — Load cases — D

|Field|Value|
|---|---|
|id|D|
|type|dead|

## Numerical inputs — Load cases — D — Loads

|Load ID → element / node|fz|
|---|---|
|D-1 → top|-700|
|D-2 → mid|-200|

Applies to every listed row: reference_frame = global; type = nodal.

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
|interactions|["说明结果为一阶线弹性静力压缩响应；N 拉正压负、uz 向上为正；分别标注中点荷载上下侧轴力，不作稳定或承载力推断。"]|

## Requested outputs — Quantities

|id|location · kind|location · id|component|unit|location · positionM|location · side|
|---|---|---|---|---|---|---|
|case-D-node-mid-uz|node|mid|uz|m|—|—|
|case-D-node-top-uz|node|top|uz|m|—|—|
|case-D-member-lower-column-s0-right-N|member|lower-column|N|kN|0|right|
|case-D-member-lower-column-s2.5-left-N|member|lower-column|N|kN|2.5|left|
|case-D-member-upper-column-s0-right-N|member|upper-column|N|kN|0|right|
|case-D-member-upper-column-s2.5-left-N|member|upper-column|N|kN|2.5|left|
|case-D-node-base-Fz|node|base|Fz|kN|—|—|

Applies to every listed row: selection · kind = case; selection · id = D.

## Analysis conventions

按指定引擎进行一阶线弹性静力分析，采用Euler-Bernoulli弯曲（不计剪切变形）；关闭自重、P-Delta、刚性楼板、刚臂偏移及施工阶段。全局XYZ，Z向上；平面模型位于XZ平面。坐标/位移m，力kN，弯矩kN*m，线载kN/m（按真实杆长），E/G为MPa，密度kg/m^3，A为m^2，Iy/Iz/J为m^4，shape尺寸mm，转角rad。约束顺序ux,uy,uz,rx,ry,rz，true表示固定。梁柱共节点刚接，桁架杆仅传轴力；支座以输入表为准。局部x由构件首节点指向末节点；空间杆局部y为reference vector叉乘局部x的单位向量，局部z=x叉乘y，再按rotation_angle绕局部x转动；平面杆未转轴时局部y为全局+Y、局部z为局部x叉乘局部y，再绕局部x施加rotation_angle；Iy为绕局部y的惯性矩。平面metadata参考向量不采用上述空间叉乘公式。报告局部到全局的转换。杆件位置从首节点计量，side为截面左右极限。N以拉为正；对局部杆端抗力按N,V2,V3,T,M2,M3排序，首节点端乘(-1,+1,+1,-1,-1,-1)、末节点端乘(+1,-1,-1,+1,+1,+1)转换为要求的有符号截面内力，不能取无符号包络替代。逐项报告input.md中数值及派生量，保留符号、单位、工况/组合；绝对值控制量同时给出原符号和控制项/组合。保存可运行输入、引擎版本、/日志及带索引原始结果；这些属于待执行要求，并非已有证据。input.md为完整公开输入附表，不含答案。

## Physical definitions

源表未给 HW300×300 的腹板与翼缘厚度；本题补齐为理想化焊接 H：H=B=300 mm、tw=10 mm、tf=15 mm，无圆角和焊缝附加面积。名义外包尺寸保持题定值。
截面 A=2Btf+(H-2tf)tw，Iy=[BH³-(B-tw)(H-2tf)³]/12，Iz=2tfB³/12+(H-2tf)tw³/12；J 采用开口薄壁近似 [2Btf³+(H-2tf)tw³]/3，数值完整列于输入表。
钢材明确采用 Q355，E=206000 MPa、nu=0.3、G=E/[2(1+nu)]、rho=7850 kg/m³；本题没有屈曲或塑性计算。
中点仅一个共享节点，200 kN 荷载施加于该节点；上下侧轴力分别在 lower-column 的 j 端和 upper-column 的 i 端读取，不能把中点荷载移到顶部。
杆件采用一阶线弹性 Euler-Bernoulli 弯曲、轴向变形及有限 Saint-Venant 扭转刚度；不计剪切变形，自重关闭。本题不做二阶、屈曲、承载力或配筋分析。
截面 A、Iy、Iz、J 为附表中的显式 SI 数值，不以软件默认截面属性替换；采用矩形截面时 J 使用输入表给定的冻结近似值。

## Output scope — Required outputs

|id|description|quantityIds|kind|
|---|---|---|---|
|mid-and-top-shortening|z=2.5 m 中点和 z=5 m 顶点的全局竖向位移 uz|["case-D-node-mid-uz", "case-D-node-top-uz"]|numerical|
|lower-column-axial-forces|下柱段的首末端轴力 N，包含中点荷载下侧极限|["case-D-member-lower-column-s0-right-N", "case-D-member-lower-column-s2.5-left-N"]|numerical|
|upper-column-axial-forces|上柱段的首末端轴力 N，包含中点荷载上侧极限|["case-D-member-upper-column-s0-right-N", "case-D-member-upper-column-s2.5-left-N"]|numerical|
|base-vertical-reaction|固定柱底竖向反力 Fz|["case-D-node-base-Fz"]|numerical|
|static-compression-interpretation|说明结果为一阶线弹性静力压缩响应；N 拉正压负、uz 向上为正；分别标注中点荷载上下侧轴力，不作稳定或承载力推断。|[]|interaction|

Applies to every listed row: state = 1.
