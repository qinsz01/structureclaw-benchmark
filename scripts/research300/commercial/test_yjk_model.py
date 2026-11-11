"""Reject unqualified physical mappings before loading a vendor SDK."""
import copy,json,unittest
from pathlib import Path
try:
    from .yjk_model import validate_packet
except ImportError:
    from yjk_model import validate_packet
class ModelValidationTests(unittest.TestCase):
    def setUp(self):
        self.model=json.loads((Path(__file__).parent/'fixtures/yjk_frame_a_endpoints.json').read_text())['model_fragment']
    def test_recorded_packet_validation_does_not_modify_source_numbers(self):
        before=copy.deepcopy(self.model);validate_packet(self.model);self.assertEqual(self.model,before)
    def test_anisotropic_inclined_column_is_not_silently_rotated(self):
        self.model['nodes'][1]['x']+=1
        column=next(e for e in self.model['elements'] if e['type']=='column');column_top=next(n for n in self.model['nodes'] if n['id']==column['nodes'][1]);column_top['x']=1
        sec=next(s for s in self.model['sections'] if s['id']==column['section']);sec['properties']['Iy']*=2
        with self.assertRaisesRegex(ValueError,'anisotropic'):validate_packet(self.model)
    def test_unknown_controls_and_invalid_properties_are_rejected(self):
        for mutate in [lambda m:m['analysis_control'].update(p_delta=True),lambda m:m['materials'][0].update(G=0),lambda m:m['elements'][0].update(rotation_angle=10),lambda m:m['sections'][0]['properties'].update(Asy=0)]:
            m=copy.deepcopy(self.model);mutate(m)
            with self.assertRaises(ValueError):validate_packet(m)
if __name__=='__main__':unittest.main()
