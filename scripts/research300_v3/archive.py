"""Use the frozen verified volume format, adding v3's full source closure."""
import argparse
import json
from pathlib import Path
from .support import V2,ROOT,load

base=load('v3_frozen_archive_container',V2/'archive.py')
base.ENTRY='scripts/research300_v3/qualify.cjs'
original_closure=base.evaluator_closure
def closure(root=ROOT):
    sources=[p for p in (Path(root)/'scripts/research300_v3').rglob('*') if p.is_file() and p.suffix in ['.cjs','.py','.md','.json'] and '__pycache__' not in p.parts]
    return sorted(set(original_closure(root)+sources))
base.evaluator_closure=closure

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',required=True);p.add_argument('--work',required=True);p.add_argument('--qualification',required=True);p.add_argument('--output',required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--attempt',type=Path,action='append',default=[]);p.add_argument('--review-file',type=Path,action='append',default=[]);a=p.parse_args()
    print(json.dumps(base.archive(a.edition,a.work.split(','),a.qualification,a.output,a.sut,a.attempt,a.review_file),indent=2))
