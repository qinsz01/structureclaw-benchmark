"""Regenerate exactly INT-001..050, require byte-identical repeat, run author checks.

This does not generate numerical references, native receipts or corpus manifests.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
from int_a_common import ROOT
from int_a_check import check_case,mutation_smoke,check_distinct_initial
BATCHES=['001_010','011_020','021_026','027_036','037_040','041_050']

def generate():
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    for batch in BATCHES:
        result=subprocess.run([sys.executable,str(ROOT/f'scripts/research300/int_a_{batch}.py')],cwd=ROOT,env=env,text=True,capture_output=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)

def digests():
    result={}
    for n in range(1,51):
        p=ROOT/f'corpora/research-300/cases/INT-{n:03}';c=json.loads((p/'contract.json').read_text())
        for name in ['contract.json','prompt.txt','reference-requests.json','author-review.json',*c['modelStates'],*c['attachments']]:
            f=p/name;result[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
    return result


def central_validation(validator_root):
    """Use the requested current implementation, keeping its exact result and hashes."""
    validator_root=validator_root.resolve()
    files=['lib/research300-validation.cjs','lib/corpus-provider.cjs',
           'schemas/research300-contract.schema.json',
           'schemas/research300-reference-requests.schema.json',
           'schemas/research300-manifest.schema.json']
    def implementation_hashes():
        return {name:hashlib.sha256((validator_root/name).read_bytes()).hexdigest() for name in files}
    before=implementation_hashes()
    script="""
const path=require('node:path');
const {validateResearchCorpus}=require(path.join(process.argv[1],'lib/research300-validation.cjs'));
const result=validateResearchCorpus({root:process.argv[2],stage:'authored',allowPartial:true});
process.stdout.write(JSON.stringify({nodeVersion:process.version,result}));
"""
    completed=subprocess.run(['node','-e',script,str(validator_root),str(ROOT)],cwd=ROOT,text=True,capture_output=True)
    after=implementation_hashes()
    record=dict(validatorRoot=str(validator_root),corpusRoot=str(ROOT),stage='authored',allowPartial=True,
                implementationSha256=before,implementationChangedDuringRun=before!=after,exitCode=completed.returncode)
    if before!=after:record['implementationSha256After']=after
    if completed.stderr:record['stderr']=completed.stderr
    try:record.update(json.loads(completed.stdout))
    except json.JSONDecodeError:record['executionError']='Validator did not emit a JSON result';record['stdout']=completed.stdout
    result=record.get('result',{})
    expected={f'INT-{i:03}' for i in range(1,51)}
    cases=result.get('cases',[])
    record['passed']=(completed.returncode==0 and before==after and result.get('valid') is True
                      and result.get('errors')==[] and len(cases)==50
                      and {case.get('id') for case in cases}==expected
                      and all(case.get('authored') is True and case.get('errors')==[] for case in cases)
                      and result.get('summary',{}).get('discovered')==50
                      and result.get('summary',{}).get('authored')==50)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validator-root',type=Path,help='Run this checkout\'s CURRENT lib/research300-validation.cjs against the INT-A worktree and require 50/50 authored cases.')
    args=parser.parse_args()
    generate();before=digests();generate();after=digests()
    assert before==after,'authoring is not byte reproducible'
    results=[check_case(f'INT-{n:03}') for n in range(1,51)]
    for script,script_args in [('int_a_027_036.py',['--check']),('int_a_041_050_checks.py',[])]:
        completed=subprocess.run([sys.executable,str(ROOT/'scripts/research300'/script),*script_args],cwd=ROOT,text=True,capture_output=True)
        if completed.returncode:raise RuntimeError(completed.stdout+completed.stderr)
    cs=[json.loads((ROOT/f'corpora/research-300/cases/INT-{n:03}/contract.json').read_text()) for n in range(1,51)]
    report=dict(cases=50,turns=sum(len(c['turns']) for c in cs),states=sum(r['states'] for r in results),quantities=sum(r['quantities'] for r in results),derived=sum(sum(len(s["derived"]) for s in json.loads((ROOT/f'corpora/research-300/cases/INT-{n:03}/reference-requests.json').read_text())["states"]) for n in range(1,51)),distinctPhysicalInitialModels=check_distinct_initial(),filesReproduced=len(before),rejectedMutations=mutation_smoke(),sourceRequirementIds=sum(len(c['sourceMetadata']['requirements']) for c in cs),structuralChecks=results,claims=dict(authorChecks='passed',native='pending',independentNumericalTruth='pending',inputBlindReview='pending',llm='not-run'))
    if args.validator_root:
        report['centralValidation']=central_validation(args.validator_root)
        report['claims']['centralAuthoredValidation']='passed' if report['centralValidation']['passed'] else 'failed'
    print(json.dumps(report,indent=2))
    if args.validator_root and not report['centralValidation']['passed']:raise SystemExit(1)

if __name__=='__main__':main()
