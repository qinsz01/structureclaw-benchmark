"""Frozen v2 mechanics are a library; v3 never mutates the old editions."""
from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[2]
V2=ROOT/'scripts/research300_v2'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
if str(V2) not in sys.path:sys.path.insert(0,str(V2))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

legacy_tasks=load('v3_frozen_tasks',V2/'tasks.py')
legacy_refs=load('v3_frozen_references',V2/'references.py')
factory=load('v3_frozen_factory',V2/'models.py')
engineering=load('v3_frozen_engineering',V2/'engineering.py')
