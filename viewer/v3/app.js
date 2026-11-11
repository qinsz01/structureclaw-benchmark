const $=id=>document.getElementById(id);
const origin={'original':'原创','source-adapted':'工程/文献改编','legacy-commercial':'保留商业题核'};
const bank=await fetch('catalogue.json').then(r=>{if(!r.ok)throw Error('题库目录不可用');return r.json();});
const full=bank.candidate.validationScope==='full-suite',hasAnswer=c=>c.turns.some(t=>t.candidate&&(t.candidate.answerPresent??Boolean(t.candidate.answer)));
$('candidate-score').textContent=`${bank.candidate.passed} / ${bank.candidate.turns}`;
$('candidate-label').textContent=`Codex${full?'全量验证':'开发试测'}通过轮次 · ${bank.candidate.cases}题`;
$('candidate-notice').textContent=full?`当前展示新版300题的Codex全量验证，含此前240道留出题。${bank.candidate.evaluationRevision==='v3.1'?`采用v3.1复核评分；冻结首评${bank.candidate.initialPassed}/560轮通过的记录已保留。`:''}未通过项保留实际交付和评分原因。StructureClaw正式对比尚未运行。此页含全部轮次与候选作答，仅用于维护者审查。`:`当前展示${bank.candidate.cases}道开发题、${bank.candidate.turns}轮实际作答，不能据此认定其余题目的表现或难度区分度。StructureClaw正式对比尚未运行。此页含全部轮次，仅用于维护者审查。`;
let chosen=null,turnIndex=0,assetVersion=0;
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function showTurn(){
 const c=chosen,t=c.turns[turnIndex],panel=$('detail');panel.replaceChildren();assetVersion++;
 panel.append(node('div',`${c.id} · ${c.family} / ${c.level} · ${c.engine} · ${c.analysis}${c.integration?' · '+c.integration:''}`,'meta'),node('h2',c.title));
 panel.append(node('p',`${origin[c.origin]}${c.sourceId?' · '+c.sourceId:''} · ${c.split} · ${c.turns.length}轮`,'muted'));
 const nav=node('div',undefined,'turns');c.turns.forEach((t,i)=>{const b=node('button',t.id);b.setAttribute('aria-pressed',String(i===turnIndex));b.onclick=()=>{turnIndex=i;showTurn();};nav.append(b);});panel.append(nav);
 panel.append(node('h3','本轮公开任务'),node('p',t.task.instruction,'instruction'));
 const task=node('details');task.append(node('summary','查看完整任务要求'),node('pre',JSON.stringify(t.task,null,2)));panel.append(task);
 panel.append(node('h3','公开附件'));
 const attachments=node('div',undefined,'attachments'),preview=node('div',undefined,'preview');
 async function display(file){
  const token=++assetVersion,url=t.base+'/'+file;preview.replaceChildren();const link=node('a','单独打开 '+file,'document-link');link.href=url;link.target='_blank';link.rel='noopener';preview.append(link);
  if(/\.png$/i.test(file)){const im=node('img');im.src=url;im.alt=file;im.loading='lazy';preview.append(im);}
  else{try{const r=await fetch(url);if(!r.ok)throw Error('附件不可用');const text=await r.text();if(token===assetVersion)preview.append(node('pre',text));}catch(error){if(token===assetVersion)preview.append(node('p',error.message));}}
 }
 (t.task.attachments||[]).forEach(file=>{const b=node('button',file);b.onclick=()=>display(file);attachments.append(b);});panel.append(attachments,preview);
 const files=t.task.attachments||[];
 const initial=(c.family==='MM'?files.find(f=>/layout-01\.png$/.test(f))||files.find(f=>/\.png$/i.test(f)):null)||files.find(f=>f==='engineering-brief.md')||files.find(f=>f==='load-zones.json');if(initial)display(initial);
 panel.append(node('h3','Codex实际作答'));
 if(t.candidate){panel.append(node('span',`${t.candidate.passed?'通过':'未通过'} · 本轮${t.candidate.jobs}次工具执行 · ${Math.round(t.candidate.seconds)}秒`,'status'));
  if(t.candidate.answerPresent??Boolean(t.candidate.answer)){
   if(t.candidate.answerFile){const link=node('a','下载原始作答文件','document-link');link.href=t.candidate.answerFile;link.download=t.candidate.answerFile.split('/').at(-1);panel.append(link);}
   panel.append(node('pre',t.candidate.answerRaw??JSON.stringify(t.candidate.answer,null,2)));
  }
  else panel.append(node('p','未收集到结构化交付。记录状态：'+t.candidate.status,'muted'));
  if(t.candidate.failures?.length||t.candidate.error){const detail=node('details');detail.append(node('summary','查看未通过原因'),node('pre',JSON.stringify(t.candidate.failures?.length?t.candidate.failures:t.candidate.error,null,2)));panel.append(detail);}
 }
 else panel.append(node('p','本轮尚未进行新版候选测试。维护者已知模型预检通过，不计为Codex作答或候选成绩。','muted'));
}
function select(c){chosen=c;turnIndex=0;history.replaceState(null,'','#'+c.id);showTurn();renderList();}
function renderList(){
 const query=$('search').value.trim().toLowerCase(),family=$('family').value,level=$('level').value,state=$('candidate').value;
 const list=bank.cases.filter(c=>(!query||[c.id,c.title,c.sourceId].join(' ').toLowerCase().includes(query))&&(!family||c.family===family)&&(!level||c.level===level)&&(!state||(state==='tested'?hasAnswer(c):state==='failed'?c.turns.some(t=>t.candidate&&!t.candidate.passed):state==='passed'?c.turns.every(t=>t.candidate?.passed):!hasAnswer(c))));
 $('count').textContent=list.length+' / 300题';$('cases').replaceChildren();
 for(const c of list){const b=node('button',undefined,'case');b.setAttribute('aria-current',String(chosen?.id===c.id));b.append(node('strong',`${c.id} · ${c.level}`),node('span',c.title,'case-title'),node('small',`${c.family} · ${c.engine} · ${origin[c.origin]}`),node('small',hasAnswer(c)?`已有Codex${full?'全量':'开发'}作答`:c.turns.some(t=>t.candidate)?'已有评测记录，尚无结构化作答':'尚未候选测试'));b.onclick=()=>select(c);$('cases').append(b);}
}
for(const id of ['search','family','level','candidate'])$(id).addEventListener(id==='search'?'input':'change',renderList);
chosen=bank.cases.find(c=>c.id===location.hash.slice(1))||bank.cases.find(c=>c.level==='L4'&&c.turns.some(t=>t.candidate));showTurn();renderList();
window.addEventListener('hashchange',()=>{
 const next=bank.cases.find(c=>c.id===location.hash.slice(1));
 if(next&&next!==chosen){chosen=next;turnIndex=0;showTurn();renderList();}
});
