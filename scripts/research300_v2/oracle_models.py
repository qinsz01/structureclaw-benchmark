"""Maintainer representations, never a repair inside the candidate broker."""
from copy import deepcopy
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
pilot=module('frozen_pilot_representations',ROOT/'scripts/pilot30/oracle_models.py')
legacy=module('frozen_commercial_representations',ROOT/'scripts/research300/commercial_reference_inputs.py')

def canonical(model,engine):
    result=deepcopy(model)
    if engine=='YJK' and not result.get('stories'):
        # The legacy native references already used this explicit natural-story
        # representation. A sloping roof remains one natural story, with its
        # actual node elevations intact; never split at each roof Z coordinate.
        control=result.get('analysis_control',{})
        if any(control.get(k) for k in ('self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage')):
            raise ValueError('Inactive native story grouping requires the qualified bare-frame static controls')
        proposed=legacy.execution_model(result,engine)
        stories=proposed['stories']
        if any(s.get('rigid_diaphragm') or s.get('floor_loads') or s.get('dead_load') or s.get('live_load') for s in stories):
            raise ValueError('Story bookkeeping must not introduce diaphragm or floor loading')
        result['stories']=deepcopy(stories)
    return pilot.canonical(result,engine)
