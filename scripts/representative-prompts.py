"""User-facing instructions. Hidden model snapshots and numerical truth are never attachments."""

ENGLISH = {
    'STD-026': [
        'Analyze the four-span continuous beam (4, 6, 5, 4 m). The left support is pinned and the other four supports are vertical rollers. Middle spans use B2, outer spans B1. D = 8 kN/m over all spans; L = 10 kN/m over spans 2 and 4 only. Use C0 = D and C1 = 1.2D + 1.4L.',
        'For both combinations, report every support reaction, all four midspan vertical displacements and the three interior support moments. Identify each span, support and combination.'
    ],
    'STD-036': [
        'Analyze the 12 m long, 2.5 m high, four-panel pin-jointed truss. Both diagonal bars in every panel cross without a connection at the crossing. The left bottom support is pinned; the right bottom support is a vertical roller. Apply 10 kN downward at each of the three interior upper nodes. Use the explicit member table and properties.',
        'Report upper-node displacements, forces in both sets of diagonal bars and support reactions. Explain that diagonal crossings are not connected.'
    ],
    'STD-086': [
        'Analyze the two-story L-shaped space frame in the actual member table. Grid X = 0, 6, 12 m; Y = 0, 5, 10 m; story heights 3.6 m. The upper-right plan corner cell is absent. All actual column bases are fixed in six degrees of freedom. Apply 8 kN/m downward to each existing beam only.',
        'Report the outer and re-entrant corner node displacements in all three directions on each floor, interstory displacement differences along each actual column line, and all base reactions.'
    ],
    'STD-088': [
        'Analyze the two-story space frame with X spans 6 + 6 m, Y span 5 m and 3.6 m story heights. All bases are fully fixed. D applies 8 kN/m downward on all beams. At the right rear corner, Wx applies +X forces 10 and 20 kN on floors 1 and 2; Wy applies +Y forces 8 and 16 kN. Keep all three cases separate. Evaluate D, D + Wx and D + Wy.',
        'Report corner displacements in X/Y on both floors, interstory differences in both directions along all column lines, base reaction vectors and the controlling combination for each requested response.'
    ],
    'INT-008': [
        'Build and analyze the 9 m beam, left end fixed and right end a vertical roller. Apply 12 kN/m downward only between x = 2 and 7 m.',
        'Report vertical displacement Uz at x = 4.5 m and the left fixed-end reaction moment My for each turn.'
    ],
    'INT-074': [
        'Build the two-story concrete frame from the input tables: columns at X = 0 and 7 m; levels Z = 0, 3.6, 7.2 m. Both bases are fixed in the XZ plane. Left columns are 500 x 350 mm; right columns 350 x 500 mm, with section axes defined in the appendix. Beams carry 10 kN/m downward. The upper-right node carries +X 20 kN and global +Y moment 12 kN.m.',
        'Report upper-right-node Ux/Uz and the left base My/Rz with the current turn, case and units. Preserve every non-target field during edits.'
    ],
    'INT-084': [
        'Build the two-story concrete space frame from the input tables: X spans 6 + 6 m, Y span 5 m, story heights 3.6 m. All column bases are fully fixed. Floor pressures are 12 and 10 kN/m2, carried only by X beams using half the adjacent Y span. The roof node (6,5,7.2) m also carries 30 kN downward in separate equipment case D_eq. Initially use the explicit C30 record. Evaluate the supplied cases and TOTAL combination.',
        'Report the upper-right rear node Ux/Uy/Uz and the left base My/Rz in each turn; retain the different floor loads and separate equipment case.'
    ],
    'MM-004': ['Reconstruct the model from the supplied drawing and tagged property/load tables. Do not use an imagined support or connect a merely observed station as a support.', 'Report Uz at global x = 6 m and signed shear immediately left/right of the point load at x = 4 m. Include model/result figures consistent with the numbers.'],
    'MM-058': ['Read the supplied drawing and tagged tables. Ask for missing support information before any computation.', 'After the complete drawing is supplied, report Ux/Uz at the right free tip and the right column-base moment. Include consistent model/result figures.'],
    'MM-070': ['Reconstruct the concrete frame from the drawing and tagged tables, keeping the actual inclined middle-story column and different beam lengths.', 'Report Ux/Uz at the upper end of the inclined column and the left column-base moment. Include consistent model/result figures.'],
    'MM-100': ['Reconstruct the three-dimensional support from all supplied projections and tables. Both short arms are actual elastic beam members. Retain their different lengths, directions and section properties.', 'Report Uz at each free arm tip and Mx/My/Mz at the column base. Include consistent model/result figures.'],
}

FOLLOW_UP = {
    'INT-001': ['在跨中 x=3m 追加向下30kN点力，保留原x=1.5m的12kN。重算并报告。', '只撤销上轮追加的30kN点力；保留其余全部荷载并重算。'],
    'INT-008': ['Change only the loaded interval from x = 2–7 m to x = 3–8 m, retaining its intensity and load ID. Recompute the two requested values.'],
    'INT-019': ['仅将C2中的L1系数改为1.4；保持D系数与其他组合不变并重算。', '仅将C2中的D系数改为1.2；保持L1=1.4与其他组合不变并重算。'],
    'INT-074': ['Rotate only the two left-column section axes +90 degrees about their local member axes, using the appendix roll convention. Keep the right columns, all loads and the +Y 12 kN.m nodal moment unchanged. Recompute.', 'Undo only the previous left-column section-axis rotation and recompute.'],
    'INT-084': ['Replace the material record for every beam and column with C35: E = 31500 MPa, G = 13125 MPa, nu = 0.2, rho = 2500 kg/m3. Keep geometry, supports, all floor loads, D_eq and combinations unchanged. Recompute.'],
}

def instructions(case, planned):
    source=planned['sourceRequirements']
    if planned['language']=='英文':
        first,output=ENGLISH[case]
        context='Use the explicit node/member tables for text tasks and the drawings for image tasks. First-order linear elasticity; self-weight, rigid diaphragms, rigid offsets, P-delta and construction stages are OFF. Use only the stated loads and combinations. Units: m, kN, kN.m, MPa. Report signed values with location, component, case/combination and run ID.'
    else:
        first='请从图纸与标签表重建模型，不猜测缺失支座。' if case.startswith('MM') else source['task.scenario']
        output=source['task.expectedOutput']
        context='按显式节点/构件输入表或图纸建立模型。一阶线弹性；关闭自重、刚性楼板、刚域、二阶与施工阶段；只用题定荷载和组合。单位m、kN、kN.m、MPa；输出附位置、分量、工况/组合与runId。'
    return [first+'\n'+output+'\n'+context]+[x+'\n'+output for x in FOLLOW_UP.get(case,[])]
