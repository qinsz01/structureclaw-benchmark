"""Regression checks for the scoped maintainer-only native representation."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from oracle_models import canonical, pilot

ROOT=Path(__file__).resolve().parents[2]
EDITION=ROOT/'corpora/research300-v2-v1'


def read(path):
    return json.loads(path.read_text())


class MaintainerNaturalStories(unittest.TestCase):
    def test_sloping_roof_changes_only_inactive_grouping_and_not_source(self):
        for turn,height in [('t1',8),('t2',9),('t3',9)]:
            with self.subTest(turn=turn):
                model=read(EDITION/'cases/V2-INT-025/private'/f'{turn}.json')['model']
                before=deepcopy(model)
                result=canonical(model,'YJK')
                self.assertEqual(model,before)
                self.assertEqual(result['stories'],[{'id':'s1','elevation':0,'height':height,'rigid_diaphragm':False}])
                self.assertEqual({k:v for k,v in result.items() if k!='stories'},model)
                self.assertFalse(any(s.get(k) for s in result['stories'] for k in ['rigid_diaphragm','floor_loads','dead_load','live_load']))
                result['nodes'][0]['x']+=1
                self.assertEqual(model,before)

    def test_active_controls_do_not_receive_implicit_inactive_grouping(self):
        source=read(EDITION/'cases/V2-INT-025/private/t1.json')['model']
        for name in ['self_weight','rigid_floor','p_delta','rigid_offsets','construction_stage']:
            with self.subTest(control=name):
                model=deepcopy(source);model['analysis_control'][name]=True;before=deepcopy(model)
                with self.assertRaisesRegex(ValueError,'bare-frame static controls'):
                    canonical(model,'YJK')
                self.assertEqual(model,before)

    def test_other_29_commercial_cases_and_42_turns_keep_previous_representation(self):
        cases=read(EDITION/'manifest.json')['cases'];case_count=turn_count=0
        for case in cases:
            if case['engine']=='OpenSees' or case['id']=='V2-INT-025':continue
            case_count+=1
            for turn in case['turns']:
                with self.subTest(case=case['id'],turn=turn['id']):
                    model=read(EDITION/turn['private'])['model'];before=deepcopy(model)
                    self.assertTrue(model.get('stories'))
                    actual=canonical(model,case['engine']);previous=pilot.canonical(model,case['engine'])
                    self.assertEqual(actual,previous)
                    self.assertEqual(json.dumps(actual,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),
                                     json.dumps(previous,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode())
                    self.assertEqual(model,before)
                    turn_count+=1
        self.assertEqual((case_count,turn_count),(29,42))

    def test_other_engines_do_not_add_natural_stories(self):
        model=read(EDITION/'cases/V2-INT-025/private/t1.json')['model'];before=deepcopy(model)
        for engine in ['PKPM','OpenSees']:
            with self.subTest(engine=engine):
                result=canonical(model,engine)
                self.assertEqual(result,pilot.canonical(model,engine))
                self.assertNotIn('stories',result)
                self.assertEqual(model,before)


if __name__=='__main__':unittest.main()
