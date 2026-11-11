"""Check frozen edition/source bindings and public/private packaging boundaries."""
import argparse
import os
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def audit(edition,tools):
    manifest=read(edition/'manifest.json');guard=read(Path(os.environ.get('SCLAW_BENCH_ARCHIVE', ROOT)).expanduser()/'docs/implementation/reviews/codex-diversity300-20261027/source-integrity.json')['files']
    for f in guard:assert sha(ROOT/f['path'])==f['sha256'],f['path']
    for f in manifest['files']:assert sha(edition/f['path'])==f['sha256'],f['path']
    old=ROOT/'.bench-work/section-diversity-v1-final-20261027/corpora/research-300/cases'
    public_files=0;legacy=0;new=0;dimensions={};engines={};rows=[]
    for c in manifest['cases']:
        engines[c['engine']]=engines.get(c['engine'],0)+1
        if c['origin']=='legacy':
            legacy+=1;b=read(edition/'cases'/c['id']/'private/legacy-binding.json');folder=old/c['legacyId'];contract=read(folder/'contract.json')
            assert sha(folder/'contract.json')==b['contractSha256']
            assert sha(folder/'independent-reference.json')==b['referenceSha256']
            assert [sha(folder/f) for f in contract['modelStates']]==b['modelHashes']
        else:new+=1
        counted_dimension=False
        for i,t in enumerate(c['turns']):
            public=edition/t['public'];ref=read(edition/t['private']);task=read(public/'task.json')
            if ref.get('model') and not counted_dimension:
                dim=ref['model']['coordinate_system']['dimension'];dimensions[dim]=dimensions.get(dim,0)+1;counted_dimension=True
            for q in task.get('requests',[]):
                assert not set(q)&{'value','tolerance','time','rawTrace','nativeStatus'},(c['id'],t['id'])
            for q in task.get('derived',[]):assert not set(q)&{'value','governingOperand','governingSelection','coGoverningOperands'}
            for p in public.iterdir():
                assert p.is_file() and not p.is_symlink()
                assert p.suffix.lower()!='.svg','Authoring vector must not bypass raster reconstruction'
                assert not any(s in p.name.lower() for s in ['reference','answer','private','truth'])
                public_files+=1
            if c['origin']=='new' and c['family']=='MM':
                assert (public/'geometry.png').is_file() and not (public/'nodes.csv').exists()
            if c['origin']=='new' and i:
                assert not any((public/n).exists() for n in ['nodes.csv','members.csv','loads.json','sections.json','analysis-control.json'])
            rows.append({'caseId':c['id'],'turnId':t['id'],'passed':True})
    pub=read(tools/'manifest.json');allowed={'analyze.py','tool-contract.md','structure_protocol/__init__.py',
        'structure_protocol/structure_model_v2.py','structure_protocol/design_properties.py','structure_protocol/section_properties.py','structure_protocol/load_contract.py'}
    assert {f['path'] for f in pub['files']}==allowed
    for f in pub['files']:assert sha(tools/f['path'])==f['sha256']
    return {'manifestSha256':sha(edition/'manifest.json'),'publicToolsManifestSha256':sha(tools/'manifest.json'),
        'cases':len(manifest['cases']),'turns':len(rows),'legacy':legacy,'new':new,'publicFiles':public_files,
        'frozenImplementationFilesUnchanged':len(guard),'engineCases':engines,'dimensionsAtFirstComputedTurn':dimensions,
        'scope':'Local static packaging/source audit; not a candidate sandbox or external blind review',
        'allPassed':True,'rows':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',type=Path,required=True);p.add_argument('--tools',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit(a.edition.resolve(),a.tools.resolve())
    with a.output.open('x') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
