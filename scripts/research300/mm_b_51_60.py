"""Explicit source-based authoring for MM-051 through MM-060.

This module produces candidate inputs and requests, never numerical truth.
Public drawings, tables and contracts are written by mm_b_common.
"""
from mm_b_common import p


_PROPERTY_DECISION = (
    "The planning source specifies material/section identifiers but no numerical appendix. "
    "Freeze M1 as elastic steel: E=206000 MPa, nu=0.3, G=E/[2(1+nu)], rho=7850 kg/m3. "
    "Freeze solid rectangular sections in metres: B1=0.30 x 0.60, B2=0.30 x 0.70, "
    "C1=0.50 x 0.50 and C2=0.35 x 0.50 wherever assigned. A, Iy, Iz and J are explicit "
    "in the appendix; J uses the frozen rectangular Saint-Venant approximation. "
    "These are authored input values, not default stiffnesses or validated truth."
)


def _model(section_ids):
    m = p.model()
    sizes = {'B1': (.30, .60), 'B2': (.30, .70), 'C1': (.50, .50), 'C2': (.35, .50)}
    m['sections'] = [p.section(sid, *sizes[sid]) for sid in section_ids]
    return m


def _nq(qid, node_id, component, description, selection=None):
    q = dict(id=qid, location=dict(kind='node', id=node_id), component=component,
             unit='kN' if component in ('Fx', 'Fy', 'Fz') else 'kN*m' if component in ('Mx', 'My', 'Mz') else 'm',
             description=description)
    if selection:
        q['selection'] = selection
    return q


def _mq(qid, member_id, position, side, component, description, selection=None):
    q = dict(id=qid, location=dict(kind='member', id=member_id, positionM=position, side=side),
             component=component, unit='kN' if component == 'N' else 'kN*m', description=description)
    if selection:
        q['selection'] = selection
    return q


def _spec(number, title, model, requests, notes=(), decisions=()):
    return dict(id=f'MM-{number:03d}', title_en=title, model=model, requests=requests,
                public_notes=list(notes), decisions=[_PROPERTY_DECISION, *decisions])


def _mm051():
    m = _model(['C1', 'B1'])
    p.node(m, 'A0', 0, 0, restraint=[True]*6)
    p.node(m, 'B0', 18, 0, restraint=[True]*6)
    p.node(m, 'A1', 0, 6)
    p.node(m, 'R', 9, 7.5)
    p.node(m, 'B1', 18, 6)
    p.node(m, 'E', 20, 6-2/6)
    p.elem(m, 'CL', 'A0', 'A1', 'column', 'C1')
    p.elem(m, 'CR', 'B0', 'B1', 'column', 'C1')
    p.elem(m, 'RL', 'A1', 'R')
    p.elem(m, 'RR', 'R', 'B1')
    p.elem(m, 'RE', 'B1', 'E')
    for member in ('RL', 'RR', 'RE'):
        p.load(m, 'D', type='distributed', element=member, wz=-6)
    p.load(m, 'W', type='distributed', element='RE', wz=10)
    m['load_combinations'] = [dict(id='D', factors={'D': 1}), dict(id='D+W', factors={'D': 1, 'W': 1})]
    req = []
    for combo in ('D', 'D+W'):
        selection = dict(kind='combination', id=combo)
        req.append(_nq(f'{combo}.E.uz', 'E', 'uz', f'{combo}：右自由檐端 E 的 Uz', selection))
        for component in ('Fx', 'Fz', 'My'):
            req.append(_nq(f'{combo}.B0.{component}', 'B0', component,
                           f'{combo}：右柱脚 B0 的支座反力 {component}', selection))
    return _spec(51, 'Pitched portal with wind suction on a right eave extension', m, req,
                 notes=['线荷载强度按构件实际长度计，方向沿全局 Z；组合 D 与 D+W 分别输出。',
                        '支座反力需输出平面内完整分量 Fx、Fz、My，正向遵循全局坐标。'],
                 decisions=['The source fixes the free end at x=20 m, so the stated 2 m extension is its horizontal projection. Its elevation follows the continuing 1:6 roof slope and loads act per actual member length.',
                            'Expand unspecified right-base reactions to all in-plane components Fx, Fz and My for both explicitly named combinations. Preserve a combination named D separately from the basic load case D.'])


def _mm052():
    m = _model(['C1', 'C2', 'B1', 'B2'])
    for prefix, x in [('A', 0), ('B', 22)]:
        p.node(m, prefix+'0', x, 0, restraint=[True]*6)
        p.node(m, prefix+'S', x, 3)
        p.node(m, prefix+'1', x, 7)
        p.elem(m, 'C'+prefix+'L', prefix+'0', prefix+'S', 'column', 'C1')
        p.elem(m, 'C'+prefix+'U', prefix+'S', prefix+'1', 'column', 'C2')
    p.node(m, 'P', 6, 7)
    p.node(m, 'M', 11, 7)
    p.node(m, 'Q', 16, 7)
    for eid, a, b, sec in [('R1', 'A1', 'P', 'B1'), ('R2a', 'P', 'M', 'B2'),
                            ('R2b', 'M', 'Q', 'B2'), ('R3', 'Q', 'B1', 'B1')]:
        p.elem(m, eid, a, b, sec=sec)
        p.load(m, type='distributed', element=eid, wz=-8)
    p.load(m, type='nodal', node='B1', fx=15)
    return _spec(52, 'Portal with segmented column and roof sections', m,
                 [_nq('D.M.uz', 'M', 'uz', 'D: roof midpoint M, vertical displacement Uz'),
                  _nq('D.B1.ux', 'B1', 'ux', 'D: right column top B1, horizontal displacement Ux')],
                 notes=['Section boundaries and the observation point retain rigid continuity. All applied loads belong to the single basic case D.'],
                 decisions=['The source names no separate lateral case or combination; the roof load and Fx=15 kN act together in basic case D.',
                            'The roof midpoint observation node is connected to the two B2 beam segments; subdivision adds neither support nor release.'])


def _mm053():
    m = _model(['C1', 'B1', 'B2'])
    for prefix, x in [('A', 0), ('B', 16)]:
        p.node(m, prefix+'0', x, 0, restraint=[True, True, True, True, False, True] if prefix == 'A' else [True]*6)
        p.node(m, prefix+'M', x, 3)
        p.node(m, prefix+'1', x, 6)
        p.elem(m, 'C'+prefix+'L', prefix+'0', prefix+'M', 'column', 'C1')
        p.elem(m, 'C'+prefix+'U', prefix+'M', prefix+'1', 'column', 'C1')
    p.elem(m, 'R', 'A1', 'B1', sec='B1')
    p.elem(m, 'T', 'AM', 'BM', sec='B2')
    p.load(m, type='distributed', element='R', wz=-8)
    p.load(m, type='nodal', node='B1', fx=12)
    return _spec(53, 'Pinned-fixed portal restrained by an unloaded midheight beam', m,
                 [_nq('D.B1.ux', 'B1', 'ux', 'D：右柱顶 B1 的 Ux'),
                  _mq('D.T.start.M2', 'T', 0, 'right', 'M2', 'D：中横梁 T 左端截面（从梁内侧取值）的 M2')],
                 notes=['弯矩采用构件局部 M2 分量；局部 1 轴由构件起点指向终点，局部 2 轴为全局 +Y。'],
                 decisions=['The requested midheight-beam left-end bending moment is the internal section M2 at member T station 0+, with local axis 2 equal to global +Y.',
                            'Both applied loads act simultaneously in basic case D; no new combination is introduced.'])


def _mm054():
    m = _model(['C1', 'C2', 'B1', 'B2'])
    for prefix, x, sec in [('A', 0, 'C1'), ('B', 12, 'C2'), ('C', 27, 'C1')]:
        p.node(m, prefix+'0', x, 0, restraint=[True]*6)
        p.node(m, prefix+'1', x, 7)
        p.elem(m, 'C'+prefix, prefix+'0', prefix+'1', 'column', sec)
    p.node(m, 'EL', -2, 7)
    p.node(m, 'ER', 30, 7)
    for eid, a, b, sec in [('OL', 'EL', 'A1', 'B2'), ('R1', 'A1', 'B1', 'B1'),
                            ('R2', 'B1', 'C1', 'B1'), ('OR', 'C1', 'ER', 'B2')]:
        p.elem(m, eid, a, b, sec=sec)
    for eid in ('R1', 'R2'):
        p.load(m, 'D', type='distributed', element=eid, wz=-6)
    for eid in ('OL', 'OR'):
        p.load(m, 'L', type='distributed', element=eid, wz=-7)
    p.load(m, 'W', type='nodal', node='C1', fx=12)
    m['load_combinations'] = [dict(id='D+L', factors={'D': 1, 'L': 1}), dict(id='D+W', factors={'D': 1, 'W': 1})]
    req = []
    for combo in ('D+L', 'D+W'):
        selection = dict(kind='combination', id=combo)
        req.extend([_nq(f'{combo}.EL.uz', 'EL', 'uz', f'{combo}: left free eave EL, displacement Uz', selection),
                    _nq(f'{combo}.ER.uz', 'ER', 'uz', f'{combo}: right free eave ER, displacement Uz', selection),
                    _nq(f'{combo}.C1.ux', 'C1', 'ux', f'{combo}: right column top C1, displacement Ux', selection)])
    return _spec(54, 'Unequal-span portal with two loaded eave extensions', m, req,
                 notes=['Report all three requested displacements separately for D+L and D+W.'],
                 decisions=['The requested outputs do not repeat a selection; apply every requested quantity to each source-specified combination D+L and D+W.'])


def _mm055():
    m = _model(['C1', 'B1'])
    for prefix, x in [('A', 0), ('B', 6), ('C', 10)]:
        p.node(m, prefix+'0', x, 0, restraint=[True]*6)
        p.node(m, prefix+'1', x, 3.6)
        p.elem(m, 'C'+prefix+'1', prefix+'0', prefix+'1', 'column', 'C1')
    for prefix, x in [('B', 6), ('C', 10)]:
        p.node(m, prefix+'2', x, 7.2)
        p.elem(m, 'C'+prefix+'2', prefix+'1', prefix+'2', 'column', 'C1')
    p.node(m, 'M2', 8, 7.2)
    for eid, a, b, q in [('B11', 'A1', 'B1', 60), ('B12', 'B1', 'C1', 60),
                          ('B2a', 'B2', 'M2', 48), ('B2b', 'M2', 'C2', 48)]:
        p.elem(m, eid, a, b)
        p.load(m, type='distributed', element=eid, wz=-q)
    return _spec(55, 'Steel setback frame with an upper storey only on the right', m,
                 [_nq('D.M2.uz', 'M2', 'uz', 'D：上层梁中点 M2 的 Uz'),
                  _mq('D.CB1.start.N', 'CB1', 0, 'right', 'N', 'D：中间底柱 CB1 下端截面 N（拉正压负）'),
                  _mq('D.CB1.end.N', 'CB1', 3.6, 'left', 'N', 'D：中间底柱 CB1 上端截面 N（拉正压负）')],
                 notes=['柱轴力采用局部 N，拉力为正；所指底柱的上下端均列出。'],
                 decisions=['The source requests axial force in the middle bottom-storey column without a station; report both internal end sections, tension positive.',
                            'A connected midpoint observation node subdivides only the existing upper beam. No upper-left column or beam is created.'])


def _mm056():
    m = _model(['C1', 'C2', 'B1'])
    p.node(m, 'A0', 0, 0, restraint=[True]*6)
    p.node(m, 'B0', 24, 0, restraint=[True]*6)
    p.node(m, 'A1', 0, 12)
    p.node(m, 'M', 12, 12)
    p.node(m, 'B1', 24, 12)
    p.node(m, 'H', 12, 9)
    p.elem(m, 'CL', 'A0', 'A1', 'column', 'C1')
    p.elem(m, 'CR', 'B0', 'B1', 'column', 'C1')
    p.elem(m, 'RL', 'A1', 'M')
    p.elem(m, 'RR', 'M', 'B1')
    p.elem(m, 'HC', 'M', 'H', 'column', 'C2')
    p.load(m, type='distributed', element='RL', wz=-36)
    p.load(m, type='distributed', element='RR', wz=-18)
    p.load(m, type='nodal', node='H', fz=-98, fx=10)
    return _spec(56, 'Industrial frame with a rigidly connected hanging column', m,
                 [_nq('D.H.ux', 'H', 'ux', 'D: hanging free end H, displacement Ux'),
                  _nq('D.H.uz', 'H', 'uz', 'D: hanging free end H, displacement Uz'),
                  _mq('D.RL.end.M2', 'RL', 12, 'left', 'M2', 'D: roof midpoint, section immediately left of joint M, M2'),
                  _mq('D.RR.start.M2', 'RR', 0, 'right', 'M2', 'D: roof midpoint, section immediately right of joint M, M2')],
                 notes=['Report roof midpoint bending moment on both sides of the joint because the connected member can transfer a concentrated moment. Local axis 2 is global +Y; member orientation follows the labelled start and end.'],
                 decisions=['The source roof-midpoint moment is ambiguous at the hanging-column joint. Preserve both one-sided internal M2 values instead of averaging the moment jump.',
                            'The hanging column is a finite-stiffness elastic member with section C2 and a free lower end. All applied loads act together in basic case D.'])


def _mm057():
    m = _model(['C1', 'B1'])
    for prefix, x in [('A', 0), ('B', 6), ('C', 12)]:
        for level, z in enumerate((0, 3.6, 7.2, 10.8)):
            p.node(m, prefix+str(level), x, z, restraint=[True]*6 if level == 0 else None)
        for level in (1, 2, 3):
            p.elem(m, 'C'+prefix+str(level), prefix+str(level-1), prefix+str(level), 'column', 'C1')
    for level, pairs in [(1, [('A', 'B'), ('B', 'C')]), (2, [('A', 'B')]), (3, [('A', 'B'), ('B', 'C')])]:
        for left, right in pairs:
            eid = 'B'+left+right+str(level)
            p.elem(m, eid, left+str(level), right+str(level))
            p.load(m, type='distributed', element=eid, wz=-10)
    for level, fx in [(1, 10), (2, 15), (3, 20)]:
        p.load(m, type='nodal', node='C'+str(level), fx=fx)
    return _spec(57, 'Three-storey frame with no right beam at the second floor', m,
                 [_nq('D.C3.ux', 'C3', 'ux', 'D：顶层右节点 C3 的 Ux'),
                  _mq('D.CC2.start.M2', 'CC2', 0, 'right', 'M2', 'D：第二层右柱 CC2 下端截面的 M2'),
                  _mq('D.CC2.end.M2', 'CC2', 3.6, 'left', 'M2', 'D：第二层右柱 CC2 上端截面的 M2')],
                 notes=['第二层右柱的端弯矩分别列下端和上端的构件内侧截面 M2；局部 2 轴沿全局 +Y。'],
                 decisions=['The source does not specify which end of the second-storey right column is meant. Request both end sections of the column between the first and second floors.',
                            'The right-side second-floor lateral load acts on the retained continuous-column node. All specified loads belong to basic case D.'])


def _mm058():
    m = _model(['C1', 'B1'])
    p.node(m, 'A0', 0, 0, restraint=[True]*6)
    p.node(m, 'B0', 6, 0, restraint=[True]*6)
    p.node(m, 'A1', 0, 4)
    p.node(m, 'B1', 6, 4)
    p.node(m, 'E', 8, 4)
    p.elem(m, 'CL', 'A0', 'A1', 'column', 'C1')
    p.elem(m, 'CR', 'B0', 'B1', 'column', 'C1')
    p.elem(m, 'R', 'A1', 'B1')
    p.elem(m, 'RE', 'B1', 'E')
    p.load(m, type='distributed', element='R', wz=-8)
    p.load(m, type='distributed', element='RE', wz=-8)
    p.load(m, type='nodal', node='E', fx=50)
    spec = _spec(58, 'Cropped frame drawing with a right roof extension', m,
                 [_nq('D.E.ux', 'E', 'ux', 'After clarification, D: right free end E, displacement Ux'),
                  _nq('D.E.uz', 'E', 'uz', 'After clarification, D: right free end E, displacement Uz'),
                  _nq('D.B0.My', 'B0', 'My', 'After clarification, D: right column base B0, reaction moment My')],
                 notes=['The requested base moment is the support reaction My in the global coordinate system.'],
                 decisions=['Turn 1 must omit both column-base support symbols and any textual support assignment. Reveal the completed support drawing only in turn 2; the final hidden model is not public input.',
                            'Interpret the requested right column-base bending moment as global support reaction My. All specified loads act simultaneously in basic case D.'])
    spec['clarify'] = dict(
        field='column-base-restraints',
        question='What restraints apply at the two column bases whose support symbols are missing from the cropped drawing?',
        instruction='Inspect the cropped drawing and identify the missing essential input before analysis. Ask a targeted clarification about the two column-base restraints.',
        resolution='The completed drawing confirms that both column bases are fixed. Use the newly supplied drawing to analyze case D and report the requested displacements and right-base moment.')
    return spec


def _mm059():
    m = _model(['C1', 'B1'])
    for prefix, x in [('A', 0), ('B', 6), ('C', 9)]:
        p.node(m, prefix+'0', x, 0, restraint=[True]*6)
        p.node(m, prefix+'1', x, 4.5)
        p.elem(m, 'C'+prefix, prefix+'0', prefix+'1', 'column', 'C1')
    p.node(m, 'M', 3, 4.5)
    p.elem(m, 'RLa', 'A1', 'M')
    p.elem(m, 'RLb', 'M', 'B1')
    p.elem(m, 'RR', 'B1', 'C1')
    for eid in ('RLa', 'RLb'):
        p.load(m, type='distributed', element=eid, wz=-48)
    return _spec(59, 'Single-storey two-span steel frame loaded on the left span', m,
                 [_nq('D.M.uz', 'M', 'uz', 'D：左跨中点 M 的 Uz'),
                  _nq('D.C1.ux', 'C1', 'ux', 'D：右柱顶 C1 的 Ux')],
                 decisions=['The left-span midpoint is a connected observation node with unchanged section and rigid continuity. The unloaded right span and its column remain in the stiffness model.'])


def _mm060():
    m = _model(['C1', 'B1'])
    for prefix, x, ztop in [('A', 0, 7.2), ('B', 5.4, 7.2), ('C', 11.4, 8.4)]:
        p.node(m, prefix+'0', x, 0, restraint=[True]*6)
        p.node(m, prefix+'1', x, 3.6)
        p.node(m, prefix+'2', x, ztop)
        p.elem(m, 'C'+prefix+'1', prefix+'0', prefix+'1', 'column', 'C1')
        p.elem(m, 'C'+prefix+'2', prefix+'1', prefix+'2', 'column', 'C1')
    p.node(m, 'M', 8.4, 7.8)
    for eid, a, b in [('B11', 'A1', 'B1'), ('B12', 'B1', 'C1'), ('B21', 'A2', 'B2'),
                       ('B22a', 'B2', 'M'), ('B22b', 'M', 'C2')]:
        p.elem(m, eid, a, b)
        p.load(m, 'D', type='distributed', element=eid, wz=-10)
        p.load(m, 'L', type='distributed', element=eid, wz=-8)
    m['load_combinations'] = [dict(id='1.2D+1.4L', factors={'D': 1.2, 'L': 1.4})]
    selection = dict(kind='combination', id='1.2D+1.4L')
    return _spec(60, 'Two-storey steel frame with a partially sloping roof', m,
                 [_nq('1.2D+1.4L.M.uz', 'M', 'uz', '1.2D+1.4L: right roof-beam midpoint M, displacement Uz', selection),
                  _nq('1.2D+1.4L.C2.ux', 'C2', 'ux', '1.2D+1.4L: right column top C2, displacement Ux', selection)],
                 notes=['Distributed loads act along global -Z per metre of actual member length. Report the explicit combination 1.2D+1.4L.'],
                 decisions=['The right roof-beam midpoint is an actual connected node halfway along the sloping member. The two collinear segments retain the same section and rigid continuity.'])


def build_specs():
    return [_mm051(), _mm052(), _mm053(), _mm054(), _mm055(),
            _mm056(), _mm057(), _mm058(), _mm059(), _mm060()]


if __name__ == '__main__':
    from mm_b_common import export_specs
    export_specs(build_specs())
