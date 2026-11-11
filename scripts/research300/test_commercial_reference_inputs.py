"""Native representation changes must preserve authored structural mechanics."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest

from commercial_reference_inputs import execution_model, published_section_model

ROOT = Path(__file__).resolve().parents[2]


def fixture(case):
    return json.loads((ROOT/'corpora/research-300/cases'/case/'model-state-1.json').read_text())


def fidelity(actual, expected):
    script = """const fs=require('fs');const {comparePhysicalModels}=require('./lib/physical-model-fidelity.cjs');
    const [actual,expected]=JSON.parse(fs.readFileSync(0,'utf8'));
    console.log(JSON.stringify(comparePhysicalModels(actual,expected,{coordinate:1e-8,property:1e-6,load:1e-6,explicitElasticProperties:true,staticTheory:'Timoshenko'})));"""
    result = subprocess.run(['node', '-e', script], input=json.dumps([actual,expected]),
                            cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


class ReferenceRepresentations(unittest.TestCase):
    def test_published_precision_changes_only_released_properties(self):
        source=fixture('STD-089');original=deepcopy(source)
        public={'sections':deepcopy(source['sections'])}
        for s in public['sections']:
            s['properties']={k:float(format(v,'.8g')) for k,v in s['properties'].items()}
        actual=published_section_model(source,public)
        self.assertEqual(source,original)
        for s,p in zip(actual['sections'],public['sections']):self.assertEqual(s['properties'],p['properties'])
        for k in source:
            if k!='sections':self.assertEqual(actual[k],source[k])
        self.assertTrue(fidelity(actual,source)['pass'])
        public['sections'][0]['properties']['J']*=1.00001
        with self.assertRaisesRegex(ValueError,'display precision'):published_section_model(source,public)

    def test_published_precision_rejects_missing_duplicate_and_nonfinite_properties(self):
        source=fixture('STD-089')
        for kind in ['missing','duplicate','nan','extra']:
            public={'sections':deepcopy(source['sections'])}
            if kind=='missing':public['sections'][0]['properties'].pop('J')
            if kind=='duplicate':public['sections'].append(deepcopy(public['sections'][0]))
            if kind=='nan':public['sections'][0]['properties']['J']=float('nan')
            if kind=='extra':public['sections'][0]['properties']['invented']=1
            with self.subTest(kind=kind),self.assertRaises(ValueError):published_section_model(source,public)

    def test_inactive_stories_keep_sloping_roof_geometry(self):
        source=fixture('INT-092');original=deepcopy(source)
        actual=execution_model(source,'YJK')
        self.assertEqual(source,original)
        self.assertEqual(actual['nodes'],source['nodes'])
        self.assertTrue(all(not s['rigid_diaphragm'] for s in actual['stories']))
        self.assertTrue(fidelity(actual,source)['pass'])

    def test_free_beam_cuts_preserve_loads_and_member_orientation(self):
        source=fixture('MM-079');original=deepcopy(source)
        actual=execution_model(source,'YJK')
        self.assertEqual(source,original)
        self.assertEqual(len(actual['nodes']),len(source['nodes'])+2)
        self.assertEqual(len(actual['elements']),len(source['elements'])+2)
        self.assertTrue(fidelity(actual,source)['pass'])
        # A real topological change must fail the same independent comparison.
        cut=next(n for n in actual['nodes'] if 'reference-cut' in n['id'])
        cut['restraints'][2]=True
        self.assertFalse(fidelity(actual,source)['pass'])

    def test_nonuniform_or_partial_loads_are_rejected(self):
        for patch in [{'distribution':'linear','wz_start':-2,'wz_end':-3},
                      {'variation':'linear'}, {'segments':[{'start':0,'end':1,'wz':-2}]},
                      {'start':0,'end':1}, {'points':[{'position':0,'wz':-2}]}]:
            source=fixture('MM-079');actual=execution_model(source,'YJK')
            parent=next(e['id'].split('-reference-segment')[0] for e in actual['elements'] if 'reference-segment' in e['id'])
            source['load_cases'][0]['loads'].append({'id':'bad','element':parent,'type':'distributed',
                                                   'reference_frame':'global','wz':-2,**patch})
            with self.subTest(patch=patch), self.assertRaisesRegex(ValueError,'uniform'):
                execution_model(source,'YJK')

    def test_pkpm_is_unchanged_and_not_aliased(self):
        source=fixture('MM-079');actual=execution_model(source,'PKPM')
        self.assertEqual(actual,source);self.assertIsNot(actual,source)
        actual['nodes'][0]['x']+=1
        self.assertNotEqual(actual['nodes'],source['nodes'])


if __name__=='__main__':unittest.main()
