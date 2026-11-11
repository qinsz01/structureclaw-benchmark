"""Public packet regression checks; no solver or network is used."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts.research300_v2.models import build_model
from scripts.research300_v2.public import write_public


class PublicPackets(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = build_model('frame', 0)
        self.case = {'id': 'REVIEW-001', 'family': 'STD', 'title': 'Public packet check',
                     'level': 2, 'origin': 'authored', 'engine': 'OpenSees'}
        self.turn = {'model': self.model, 'kind': 'static', 'instruction': 'Reconstruct and analyse.'}
        self.ref = {'kind': 'static', 'requests': [{'id': 'ux', 'selection': {'kind': 'case', 'id': 'W'},
                    'location': 'node:N0-1', 'component': 'ux', 'unit': 'm',
                    'value': 'HIDDEN_REFERENCE_VALUE', 'tolerance': {'abs': 'HIDDEN_TOLERANCE'},
                    'time': 'HIDDEN_PEAK_TIME', 'rawTrace': 'HIDDEN_TRACE'}],
                    'derived': [{'id': 'd', 'operation': 'abs', 'operands': ['ux'], 'unit': 'm',
                                 'value': 'HIDDEN_DERIVED_VALUE', 'tolerance': 'HIDDEN_DERIVED_TOLERANCE'}],
                    'reportIds': ['ux', 'd'], 'expectedIssuePaths': ['/HIDDEN_ISSUE_PATH']}

    def test_initial_standard_is_complete_and_reference_numbers_are_private(self):
        folder = self.root / 'standard'
        write_public(folder, self.case, self.turn, 1, self.ref)
        task = json.loads((folder / 'task.json').read_text())
        self.assertEqual(task['reportIds'], ['ux', 'd'])
        self.assertEqual(set(task['attachments']), {p.name for p in folder.iterdir()} - {'task.json'})
        self.assertEqual(json.loads((folder / 'materials.json').read_text()), self.model['materials'])
        self.assertEqual(json.loads((folder / 'model-convention.json').read_text())['coordinate_system'],
                         self.model['coordinate_system'])
        for name in ['nodes.csv', 'members.csv', 'materials.csv', 'sections.json', 'loads.json',
                     'combinations.json', 'analysis-control.json', 'tool-contract.md']:
            self.assertTrue((folder / name).is_file(), name)
        for file in folder.iterdir():
            self.assertNotIn('HIDDEN_', file.read_text(), file.name)

    def test_load_recipe_replaces_the_private_mechanical_load_schedule(self):
        self.case['loadRecipe'] = {'cases': [{'id': 'D', 'type': 'dead', 'terms': [
            {'kind': 'surface-on-members', 'members': ['B0-1'], 'pressureKNM2': 2.,
             'tributaryWidthM': 4., 'globalUnitVector': [0, 0, -1]}]}]}
        folder = self.root / 'recipe'
        write_public(folder, self.case, self.turn, 1, self.ref)
        self.assertTrue((folder / 'load-recipe.json').is_file())
        self.assertFalse((folder / 'loads.json').exists())
        self.assertIn('loadInput', json.loads((folder / 'task.json').read_text()))

    def test_later_turn_has_only_change_order_and_replacement_excitation(self):
        folder = self.root / 'later'
        turn = deepcopy(self.turn)
        turn['changeOrder'] = {'schemaVersion': 1, 'operations': [
            {'op': 'scale-load-case', 'caseId': 'W', 'factor': 1.2}]}
        turn['parameters'] = {'dt': .02, 'groundMotion': [0., .1, -.2, 0.], 'groundMotionUnit': 'g'}
        write_public(folder, self.case, turn, 2, self.ref)
        self.assertEqual({p.name for p in folder.iterdir()},
                         {'task.json', 'change-order.json', 'analysis-parameters.json', 'excitation.csv'})
        params = json.loads((folder / 'analysis-parameters.json').read_text())
        self.assertNotIn('groundMotion', params)
        self.assertEqual(params['groundMotionFile'], 'excitation.csv')

    def test_96_node_spatial_packet_paginates_and_never_issues_geometry_json(self):
        folder = self.root / 'spatial'
        self.case.update(family='MM', inputMode='multiview')
        self.turn['model'] = build_model('space_frame', 29)
        self.assertEqual(len(self.turn['model']['nodes']), 96)
        write_public(folder, self.case, self.turn, 1, self.ref)
        self.assertEqual(len(list(folder.glob('geometry-nodes-*.png'))), 5)
        self.assertTrue((folder / 'geometry-stories-01.png').exists())
        self.assertTrue((folder / 'metadata.json').exists())
        for name in ['nodes.csv', 'stories.json', 'model.json', 'model-to-review.json']:
            self.assertFalse((folder / name).exists(), name)
        with Image.open(folder / 'geometry-overview.png') as overview:
            self.assertEqual(overview.size, (2400, 1320))

    def test_dxf_preserves_xyz_node_points_and_explicit_restraint_masks(self):
        folder = self.root / 'dxf'
        self.case.update(family='MM', inputMode='dxf')
        self.turn['model'] = build_model('space_frame', 0)
        write_public(folder, self.case, self.turn, 1, self.ref)
        dxf = (folder / 'geometry.dxf').read_text()
        self.assertEqual(dxf.count('0\nPOINT\n8\nNODE\n'), len(self.turn['model']['nodes']))
        for node in self.turn['model']['nodes']:
            mask = ''.join(str(int(v)) for v in node['restraints'])
            self.assertIn(node['id'] + ' FIXED=' + mask, dxf)
        self.assertFalse((folder / 'nodes.csv').exists())

    def test_mm_full_model_and_machine_readable_boundaries_are_rejected(self):
        self.case.update(family='MM', inputMode='dxf')
        self.turn['suspectModel'] = self.model
        with self.assertRaisesRegex(ValueError, 'full suspect model'):
            write_public(self.root / 'bad-full', self.case, self.turn, 1, self.ref)
        del self.turn['suspectModel']
        self.turn['suspectExcerpt'] = {'boundaryExcerpt': {'restraints': [True] * 6}}
        with self.assertRaisesRegex(ValueError, 'geometry or boundary'):
            write_public(self.root / 'bad-boundary', self.case, self.turn, 1, self.ref)


if __name__ == '__main__':
    unittest.main()
