"""Source-specific builders for STD-095..100, with no numerical reference values."""
from std_b_common import model, node, elem, load, section, Requests, emit


def _base_model(dimension="2d", concrete=False):
    m = model(dimension, concrete)
    m["sections"] = []
    if concrete:
        m["materials"][0].update(name="C30", E=30000, G=12500)
    return m


def _column(height, width, depth, *, concrete=False, dimension="2d"):
    m = _base_model(dimension, concrete)
    m["sections"] = [section("C1", width, depth)]
    node(m, "base", 0, 0, restraint=[True] * 6)
    node(m, "top", 0, height)
    elem(m, "column", "base", "top", "column", "C1")
    return m


def _scope(oid, description, ids, kind="numerical"):
    return dict(id=oid, description=description, state=1, quantityIds=ids, kind=kind)


def _emit(number, m, prompt, r, notes, scope, interactions=()):
    en = number % 2 == 0
    notes = list(notes) + ([
        "All members use first-order linear elastic Euler-Bernoulli bending, axial deformation and finite Saint-Venant torsion stiffness. Shear deformation and self-weight are disabled. No geometric stiffness, buckling, capacity or reinforcement assessment is requested.",
        "Section properties A, Iy, Iz and J are explicit inputs in SI units. Rectangular-section J uses the numerical approximation supplied in input-data.json; no default section properties may replace it."
    ] if en else [
        "杆件采用一阶线弹性 Euler-Bernoulli 弯曲、轴向变形及有限 Saint-Venant 扭转刚度；不计剪切变形，自重关闭。本题不做二阶、屈曲、承载力或配筋分析。",
        "截面 A、Iy、Iz、J 为附表中的显式 SI 数值，不以软件默认截面属性替换；采用矩形截面时 J 使用输入表给定的冻结近似值。"
    ])
    emit(number, m, prompt, r, notes=notes, interactions=interactions,
        extra_attachments={"appendix-decisions.txt": "\n".join(notes) + "\n",
                           "output-scope.json": dict(requiredOutputs=scope)})


def case095():
    m = _column(4.5, .4, .4, concrete=True)
    load(m, type="nodal", node="top", fz=-500)
    r = Requests(m)
    scope = [_scope("top-shortening", "柱顶竖向位移 uz", r.node("top", ("uz",))),
             _scope("column-axial-force", "柱两端截面轴力 N，拉为正、压为负", r.ends("column", ("N",))),
             _scope("vertical-base-reaction", "固定柱脚竖向反力 Fz", r.node("base", ("Fz",)))]
    sign = "说明全局 +Z 向上、uz 负值表示向下缩短，杆轴力 N 拉为正、压为负；本题为一阶静力压缩响应。"
    scope.append(_scope("compression-sign-convention", sign, [], "interaction"))
    _emit(95, m,
        "用 OpenSees 分析一根高 4.5 m、400×400 mm 的 C30 混凝土柱。柱底六自由度固定；柱顶在 XZ 平面内自由且没有侧向支座。D 工况下仅在柱顶施加竖直向下 500 kN。按附件 C30 弹性参数、截面及局部轴进行一阶线弹性静力分析，自重关闭。只报告柱顶 uz、柱两端轴力 N 和柱底竖向反力 Fz，并说明压缩轴力与向下位移的符号；不进行稳定或承载力验算。",
        r, ["C30 明确采用 E=30000 MPa、nu=0.2、G=12500 MPa、rho=2500 kg/m³；柱为题定的 400×400 mm 实心矩形。",
            "模型为 XZ 平面柱；柱顶仅有平面模型所需的 uy/rx/rz 约束，ux/uz/ry 自由。",
            "柱轴力在首端 0 m 的右侧与末端 4.5 m 的左侧分别请求，避免把支座反力符号当作压缩轴力符号。"], scope, [sign])


def case096():
    m = _column(4.2, .45, .45, concrete=True)
    load(m, type="nodal", node="top", fx=30, fz=-600)
    r = Requests(m)
    scope = [_scope("top-displacement-and-rotation", "Column-top global ux, uz and ry", r.node("top", ("ux", "uz", "ry"))),
             _scope("base-section-actions", "Local N, V3 and M2 immediately above the fixed column base", r.member("column", 0, ("N", "V3", "M2"))),
             _scope("base-reactions", "Global Fx, Fz and My at the fixed column base", r.node("base", ("Fx", "Fz", "My")))]
    _emit(96, m,
        "Analyze the attached 4.2 m concrete cantilever column in OpenSees. Its section is 450x450 mm, its base is fixed, and its top is free. In case D apply both loads at the top: 600 kN downward in global Z and 30 kN in global +X. Use the explicit C30 elastic properties supplied in the appendix. Report the top ux, uz and ry; local N, V3 and M2 at the column-base section; and the corresponding global base reactions Fx, Fz and My, preserving the stated local/global signs. Use first-order linear elastic static analysis with self-weight and P-Delta disabled.",
        r, ["The source leaves the concrete grade and elastic constants unspecified. The appendix freezes C30 with E=30000 MPa, nu=0.2, G=12500 MPa and rho=2500 kg/m³; the given 450x450 mm section is retained.",
            "The base-section result is located at member column, position 0 m, side right. Both local section forces and global support reactions are requested to disambiguate the source phrase 'base axial force/shear/moment'.",
            "The top axial and lateral forces are simultaneous components of case D. They do not activate P-Delta or change the prescribed first-order model."], scope)


def _welded_h300():
    # Idealized welded H: three rectangles, no fillets, centroid at mid-depth.
    b, h, tw, tf = .3, .3, .01, .015
    hw = h - 2 * tf
    return dict(id="HW300", name="HW300x300", type="H",
        shape=dict(kind="H", H=300, B=300, tw=10, tf=15),
        properties=dict(A=2 * b * tf + hw * tw,
            Iy=(b * h**3 - (b - tw) * hw**3) / 12,
            Iz=2 * tf * b**3 / 12 + hw * tw**3 / 12,
            J=(2 * b * tf**3 + hw * tw**3) / 3))


def case097():
    m = _base_model()
    m["sections"] = [_welded_h300()]
    node(m, "base", 0, 0, restraint=[True] * 6)
    node(m, "mid", 0, 2.5)
    node(m, "top", 0, 5)
    elem(m, "lower-column", "base", "mid", "column", "HW300")
    elem(m, "upper-column", "mid", "top", "column", "HW300")
    load(m, type="nodal", node="top", fz=-700)
    load(m, type="nodal", node="mid", fz=-200)
    r = Requests(m)
    scope = [_scope("mid-and-top-shortening", "z=2.5 m 中点和 z=5 m 顶点的全局竖向位移 uz", r.node("mid", ("uz",)) + r.node("top", ("uz",))),
             _scope("lower-column-axial-forces", "下柱段的首末端轴力 N，包含中点荷载下侧极限", r.ends("lower-column", ("N",))),
             _scope("upper-column-axial-forces", "上柱段的首末端轴力 N，包含中点荷载上侧极限", r.ends("upper-column", ("N",))),
             _scope("base-vertical-reaction", "固定柱底竖向反力 Fz", r.node("base", ("Fz",)))]
    interpretation = "说明结果为一阶线弹性静力压缩响应；N 拉正压负、uz 向上为正；分别标注中点荷载上下侧轴力，不作稳定或承载力推断。"
    scope.append(_scope("static-compression-interpretation", interpretation, [], "interaction"))
    _emit(97, m,
        "用 OpenSees 分析附件中的 5 m 钢柱：底固定，顶自由；z=2.5 m 处为上下两段共用的连续节点，无额外支承或铰。截面为 HW300×300，本题采用附表明确的理想化焊接 H 形（总高 300 mm、翼缘宽 300 mm、腹板厚 10 mm、翼缘厚 15 mm、无圆角）。D 工况下顶部向下 700 kN，中点另向下 200 kN。输出中点及顶点 uz、上下两柱段各两端的 N（注明中点上下侧）、柱底 Fz，并说明为静力压缩响应及符号。采用附件完整弹性参数，一阶线弹性、自重关闭，不作稳定验算。",
        r, ["源表未给 HW300×300 的腹板与翼缘厚度；本题补齐为理想化焊接 H：H=B=300 mm、tw=10 mm、tf=15 mm，无圆角和焊缝附加面积。名义外包尺寸保持题定值。",
            "截面 A=2Btf+(H-2tf)tw，Iy=[BH³-(B-tw)(H-2tf)³]/12，Iz=2tfB³/12+(H-2tf)tw³/12；J 采用开口薄壁近似 [2Btf³+(H-2tf)tw³]/3，数值完整列于输入表。",
            "钢材明确采用 Q355，E=206000 MPa、nu=0.3、G=E/[2(1+nu)]、rho=7850 kg/m³；本题没有屈曲或塑性计算。",
            "中点仅一个共享节点，200 kN 荷载施加于该节点；上下侧轴力分别在 lower-column 的 j 端和 upper-column 的 i 端读取，不能把中点荷载移到顶部。"], scope, [interpretation])


def _unequal_flange_h():
    """Three centered rectangles: one symmetry axis, unequal centroidal inertias."""
    height, tw = .4, .012
    bottom_width, bottom_thickness = .3, .02
    top_width, top_thickness = .2, .015
    web_height = height - bottom_thickness - top_thickness
    pieces = [(bottom_width, bottom_thickness, bottom_thickness / 2),
              (tw, web_height, bottom_thickness + web_height / 2),
              (top_width, top_thickness, height - top_thickness / 2)]
    area = sum(b * h for b, h, z in pieces)
    centroid = sum(b * h * z for b, h, z in pieces) / area
    iy = sum(b * h**3 / 12 + b * h * (z - centroid)**2 for b, h, z in pieces)
    iz = sum(h * b**3 / 12 for b, h, z in pieces)
    torsion = (bottom_width * bottom_thickness**3 + top_width * top_thickness**3 + web_height * tw**3) / 3
    return dict(id="C1", name="Unequal-flange welded H", type="custom",
        shape=dict(kind="custom", description="Welded H with unequal centered flange widths and thicknesses; no fillets",
                   total_depth_mm=400, bottom_flange_width_mm=300, bottom_flange_thickness_mm=20,
                   top_flange_width_mm=200, top_flange_thickness_mm=15, web_thickness_mm=12,
                   centroid_from_bottom_mm=centroid * 1000),
        properties=dict(A=area, Iy=iy, Iz=iz, J=torsion))


def case098():
    m = _base_model("3d")
    m["sections"] = [_unequal_flange_h()]
    node(m, "base", 0, 0, restraint=[True] * 6)
    node(m, "top", 0, 6)
    elem(m, "column", "base", "top", "column", "C1")
    load(m, type="nodal", node="top", fx=20, fy=15, fz=-400)
    r = Requests(m)
    scope = [_scope("top-six-displacements", "Column-top global ux, uy, uz, rx, ry and rz", r.node("top", ("ux", "uy", "uz", "rx", "ry", "rz"))),
             _scope("base-six-reactions", "Fixed-base global Fx, Fy, Fz, Mx, My and Mz", r.node("base", ("Fx", "Fy", "Fz", "Mx", "My", "Mz")))]
    axes = "Report the section-axis mapping: local x=global +Z, local y=global -Y and local z=global +X; global X bending uses Iy and global Y bending uses Iz. Include the numerical principal inertias from the appendix."
    scope.append(_scope("section-axis-mapping", axes, [], "interaction"))
    _emit(98, m,
        "Analyze the attached 6 m spatial cantilever column in OpenSees. All six base degrees of freedom are fixed and the top is free. In case D, apply the global top force (Fx,Fy,Fz)=(20,15,-400) kN at the centroidal reference axis. Use the supplied asymmetric unequal-flange welded H section, its distinct centroidal principal inertias, and its explicit local axes. Report all three top translations and all three top rotations, all six global base reactions, and the mapping between the two principal section inertias and the global bending directions. Use first-order linear elastic static analysis with self-weight and P-Delta disabled.",
        r, ["The unspecified material is completed as Q355 steel, E=206000 MPa, nu=0.3, G=E/[2(1+nu)] and rho=7850 kg/m³.",
            "The asymmetric section is an idealized welded H of total depth 400 mm, bottom flange 300x20 mm, top flange 200x15 mm and centered 12 mm web. Flanges have different widths and thicknesses, so reflection across local z=0 is not a symmetry. All dimensions and the centroid from the bottom outside face are given in the shape record.",
            "A and the centroidal Iy/Iz are computed from the three non-overlapping component rectangles with the parallel-axis theorem. Since every component is centered in local y, Iyz=0 and local y/z are principal axes. J is the explicit open thin-wall sum of length times thickness cubed divided by 3. Fillets, warping and shear-center eccentric coupling are outside the declared Euler-Bernoulli idealization.",
            "The reference vector is global +X. For the upward column, local x=+Z, local y=-Y and local z=+X, with zero section roll; Iy and Iz must not be interchanged.",
            "The custom section supplies explicit A/Iy/Iz/J. Native adapter support for this custom shape remains an acceptance gate; the properties must not be replaced by a rectangular section."], scope, [axes])


def case099():
    m = _base_model()
    m["sections"] = [section("C1", .5, .5), section("C2", .35, .5)]
    node(m, "base", 0, 0, restraint=[True] * 6)
    node(m, "interface", 0, 3)
    node(m, "top", 0, 8)
    elem(m, "lower-column", "base", "interface", "column", "C1")
    elem(m, "upper-column", "interface", "top", "column", "C2")
    load(m, type="nodal", node="top", fx=25, fz=-500)
    r = Requests(m)
    scope = [_scope("column-top-displacements", "柱顶全局 ux、uz", r.node("top", ("ux", "uz"))),
             _scope("interface-displacement-and-rotation", "z=3 m 共用界面节点的 ux、uz、ry", r.node("interface", ("ux", "uz", "ry"))),
             _scope("interface-end-forces", "下段 j 端及上段 i 端的局部 N、V3、M2", r.member("lower-column", 3, ("N", "V3", "M2"), side="left") + r.member("upper-column", 0, ("N", "V3", "M2"), side="right")),
             _scope("base-reactions", "柱底全局反力 Fx、Fz 及反力矩 My", r.node("base", ("Fx", "Fz", "My")))]
    _emit(99, m,
        "用 OpenSees 建立附件中的 8 m 分段截面悬臂柱：0≤z≤3 m 下段采用 C1，3≤z≤8 m 上段采用 C2，z=3 m 两段共用连续刚接节点，界面无铰；柱底固定，顶自由。D 工况下柱顶同时承受 +X 向 25 kN 与竖向 -Z 向 500 kN。输出顶点 ux、uz，界面节点 ux、uz、ry，界面下段末端及上段首端各自的 N/V3/M2，以及柱底 Fx/Fz/My。使用附件的分段 A/I/J、材料和局部轴进行一阶线弹性静力分析，自重关闭。",
        r, ["源表没有给定材料类别与 C1/C2 尺寸；本题明确补齐为 Q355 钢，C1=500×500 mm、C2=350×500 mm 实心矩形理想化截面，两段 E 相同而 A、Iy、Iz、J 各自不同。",
            "下段长度为 3 m，上段长度为 5 m；截面界面仅一个共享节点，ux、uz、ry 连续且无释放。",
            "界面端力明确为 lower-column 的位置 3 m、side=left，以及 upper-column 的位置 0 m、side=right；保持两侧标签及统一截面内力符号。"], scope)


def case100():
    m = _base_model("3d")
    m["sections"] = [section("C1", .4, .5), section("B1", .25, .4)]
    node(m, "base", 0, 0, restraint=[True] * 6)
    node(m, "top", 0, 5)
    node(m, "tip", 1, 5)
    elem(m, "column", "base", "top", "column", "C1")
    elem(m, "arm", "top", "tip", "beam", "B1")
    load(m, type="nodal", node="tip", fy=10, fz=-200)
    r = Requests(m)
    scope = [_scope("arm-tip-six-displacements", "Arm-tip global ux, uy, uz, rx, ry and rz", r.node("tip", ("ux", "uy", "uz", "rx", "ry", "rz"))),
             _scope("column-top-rotations", "Column-top global rx, ry and rz", r.node("top", ("rx", "ry", "rz"))),
             _scope("base-six-reactions", "Fixed-base global Fx, Fy, Fz, Mx, My and Mz", r.node("base", ("Fx", "Fy", "Fz", "Mx", "My", "Mz"))),
             _scope("column-end-forces", "Both column ends: local N, V2, V3, T, M2 and M3", r.ends("column")),
             _scope("arm-end-forces", "Both finite-stiffness arm ends: local N, V2, V3, T, M2 and M3", r.ends("arm"))]
    _emit(100, m,
        "Build and analyze the attached spatial column and short arm in OpenSees. The column runs from (0,0,0) to (0,0,5) m and is fixed in all six degrees of freedom at its base. A real 1 m elastic beam is rigidly connected from the column top to the free arm tip at (1,0,5) m. In case D apply the global arm-tip force (Fx,Fy,Fz)=(0,10,-200) kN. Use the separate explicit A/Iy/Iz/J properties for the column and arm, including their finite torsional stiffness. Report all three arm-tip translations and rotations, all three column-top rotations, all six base reactions, and all six local section-force components at both ends of both members. Use first-order linear elastic static analysis with self-weight disabled.",
        r, ["The appendix supplies Q355 steel and separate idealized rectangular sections: C1=400x500 mm for the column and B1=250x400 mm for the arm. Each has its own explicit finite A, Iy, Iz and J.",
            "The arm is a 1 m elastic beam element sharing all six joint degrees of freedom with the column top. It is not a rigid link or a concentrated moment substitute.",
            "For the column, local x=+Z, y=-Y, z=+X using reference +X. For the arm, local x=+X, y=+Y, z=+Z using reference +Z. Both have zero roll.",
            "All six end-force components are retained, including axial torsion T; the eccentric tip forces remain at the actual free node."], scope)


if __name__ == "__main__":
    for builder in (case095, case096, case097, case098, case099, case100):
        builder()
