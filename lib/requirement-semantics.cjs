/** Polarity is local to each engineering clause. A prohibited default is not a requested capability. */
const FEATURES = [
  ['load.member-distribution', /局部均布|线载|均布载|分段荷载|分布荷载/g],
  ['load.point', /点载|集中力|节点力|节点侧力/g],
  ['geometry.actual-connectivity', /共节点|缺梁|缺柱|退台|斜柱|不连接|不相连/g],
  ['properties.assignments', /截面|材料|局部轴/g],
  ['interaction.edit', /撤销|修订|修改|替换|改为|补全/g],
  ['result.position', /跨中|跨内|左右剪力|观测|指定位置/g],
  ['member.end-release', /端部释放|梁端释放|构件端释放|内铰/g],
  ['member.rigid-offset', /刚域|刚臂|无限刚|刚性偏心/g],
  ['analysis.second-order', /P-Delta|P-Δ|二阶/gi],
  ['analysis.full-nonlinear', /非线性/g],
  ['analysis.shell-wall', /墙壳|剪力墙|壳单元/g],
  ['analysis.construction-stage', /施工阶段/g],
  ['gravity.self-weight', /自重/g],
  ['diaphragm.rigid-floor', /刚性楼板|楼板约束/g],
];
const NEGATION = /(?:不(?:得|能|要|应|再|自动|额外|默认|新增|启用|采用|套|计|做|进行|设|把|产生)?|无|禁止|关闭|而非|不是)[^，,；;。\n]{0,18}$/;
const FEATURE_ATOMS = {
  'member.partial-point-and-piecewise-load': ['load.member-distribution','load.point'],
  'member.response-stations': ['result.position'],
  'gravity.explicit-self-weight': ['gravity.self-weight'],
  'diaphragm.rigid-floor': ['diaphragm.rigid-floor'],
  'member.release-offset-pdelta': ['member.end-release','member.rigid-offset','analysis.second-order','analysis.construction-stage'],
  'interaction.state-updates': ['interaction.edit'],
};

function linkedRoles(requirement, featureId) {
  const ids=FEATURE_ATOMS[featureId];
  const atoms=ids?requirement.semantics.atoms.filter(atom=>ids.includes(atom.featureId)):[];
  return [...new Set(atoms.length?atoms.map(atom=>atom.kind):[requirement.semantics.kind==='output'?'output':'review-required'])];
}

function classifyRequirement(text, field) {
  const output = /(?:expectedOutput|requiredEvidence|gradingFocus)$/.test(field);
  const atoms = [];
  for (const [featureId, expression] of FEATURES) {
    for (const match of text.matchAll(expression)) {
      const before = text.slice(0, match.index).split(/[，,；;。\n]/u).at(-1);
      const after = text.slice(match.index + match[0].length).split(/[，,；;。\n]/u)[0];
      const prohibited = NEGATION.test(before) || /^(?:OFF|关闭|不(?:开启|启用|考虑))/i.test(after)
        || /^(?:简化|替换)/.test(after) && /不|禁止|不得/.test(before);
      // “不将未验证能力记为失败” and planning adapter descriptions are not requirements.
      const kind = prohibited ? 'forbidden' : output ? 'output' : 'required';
      atoms.push({ featureId, kind, term: match[0], range: [match.index, match.index + match[0].length] });
    }
  }
  return { kind: output ? 'output' : atoms.some(a => a.kind === 'required') ? 'required'
    : atoms.length && atoms.every(a => a.kind === 'forbidden') ? 'forbidden' : 'review-required', atoms,
  reviewStatus: 'rule-classified-needs-case-review' };
}

function annotateCoverage(coverage) {
  for (const item of coverage.cases) {
    for (const requirement of item.requirements) {
      const text = item.sourceRequirements[requirement.sourceField].slice(...requirement.sourceRange);
      requirement.semantics = classifyRequirement(text, requirement.sourceField);
      if (requirement.candidateFeatures.includes('member.release-offset-pdelta')) {
        const relevant = requirement.semantics.atoms.filter(a => ['member.end-release','member.rigid-offset','analysis.second-order','analysis.construction-stage'].includes(a.featureId));
        if (!relevant.some(a => a.kind === 'required')) requirement.candidateFeatures = requirement.candidateFeatures.filter(id => id !== 'member.release-offset-pdelta');
      }
    }
    for (const feature of item.features) {
      const linked=item.requirements.filter(r => r.candidateFeatures.includes(feature.featureId));
      feature.referencedBy=linked.map(r=>r.id);
      for(const [field,role] of [['requiredBy','required'],['forbiddenBy','forbidden'],['outputBy','output'],['reviewRequiredBy','review-required']])
        feature[field]=linked.filter(r=>linkedRoles(r,feature.featureId).includes(role)).map(r=>r.id);
    }
    item.features = item.features.filter(f => f.mapping !== 'text-candidate-needs-review' || f.referencedBy.length);
    item.acceptance.unmappedRequirementIds = item.requirements.filter(r => !r.candidateFeatures.length).map(r => r.id);
  }
  coverage.summary.unmappedClauses = coverage.cases.reduce((n,c) => n + c.acceptance.unmappedRequirementIds.length, 0);
  coverage.summary.unknownRequirementClauses = coverage.summary.requirementClauses;
  coverage.summary.semantics = coverage.cases.flatMap(c => c.requirements).reduce((counts,r) => {
    counts[r.semantics.kind] = (counts[r.semantics.kind] || 0) + 1; return counts;
  }, {});
  coverage.policy.semanticPolarity = 'required / forbidden / output are clause-local review aids; no capability or case pass is inferred';
  return coverage;
}
module.exports = { classifyRequirement, annotateCoverage };
