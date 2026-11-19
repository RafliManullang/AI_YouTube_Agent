import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

import asset_generator as assets
import main_agent as agent


def spec():
    return [dict(id=k, view_type=v, prompt='water heater ' + v) for k, v in assets.VIEWS.items()]


class HybridTests(unittest.TestCase):
    def test_validation_and_owned_cleanup(self):
        bad = spec()
        bad[2]['id'] = '../unsafe'
        with self.assertRaises(ValueError):
            assets.validate_assets(bad)
        with tempfile.TemporaryDirectory() as tmp:
            owned = Path(tmp) / '03_cutaway.png'
            other = Path(tmp) / 'personal.png'
            owned.touch(); other.touch()
            assets.clear_assets(Path(tmp))
            self.assertFalse(owned.exists())
            self.assertTrue(other.exists())

    def test_png_crop_and_invalid_provider_response(self):
        buf = io.BytesIO()
        Image.new('RGB', (320, 450)).save(buf, 'JPEG')
        with Image.open(io.BytesIO(assets.picture_bytes(buf.getvalue()))) as png:
            self.assertEqual((png.format, png.size), ('PNG', (1080, 1920)))
        with self.assertRaises(OSError):
            assets.picture_bytes(b'<html>not an image</html>')

    def test_script_to_props_partial_resume_and_vision_correction(self):
        data = {'title': 'Water heater', 'assets': spec(), 'scenes': []}
        for i, key in enumerate(['01_exterior', '03_cutaway', '02_analogy', '04_closeup', '01_exterior']):
            data['scenes'].append(dict(start=i, end=i+1, title='heater', narration='heater', asset_id=key,
                                       component='coil', overlay={'type':'heat_pulse'}))
        voice = {'timings': agent.render_timings(data['scenes'], [], 5)}
        text = json.dumps({'has_garbled_text': True, 'anchors': {}})
        clean = json.dumps({'has_garbled_text': False, 'anchors': {'coil':[.3,.7]}})
        vision = Mock(side_effect=[RuntimeError('quota'), text, clean])
        with tempfile.TemporaryDirectory() as tmp, patch.object(agent,'PUBLIC_DIR',tmp), \
                patch.object(agent,'SESSION_PATH',Path(tmp)/'last_session.json'), patch.object(agent,'GEMINI_KEY',''), \
                patch.object(agent,'vision_caller',return_value=vision), \
                patch.object(assets,'generate_picture',side_effect=[b'ext',b'analogy',b'cut',b'new cut',b'close',b'ext']) as gen:
            with self.assertRaisesRegex(RuntimeError,'quota'):
                agent.prepare_hybrid(data,voice)
            def resume():
                checkpoint = json.loads(agent.SESSION_PATH.read_text())
                return agent.prepare_hybrid(checkpoint['data'], checkpoint['voice'])
            plan = resume()
            shot = plan['shots'][1]
            self.assertEqual(shot['camera']['focusY'],.7)
            self.assertEqual(shot['overlay']['targetX'],324)
            self.assertEqual(plan, resume())
            self.assertEqual(gen.call_count,5)
            self.assertEqual(vision.call_count,3)
            self.assertEqual(gen.call_args_list[3].args[1],gen.call_args_list[2].args[1]+1)
            self.assertTrue(all(assets.MASTER_STYLE_PROMPT in c.args[0] for c in gen.call_args_list))
            (Path(tmp)/'assets/01_exterior.png').write_bytes(b'corrupt')
            self.assertEqual(plan,resume())
            self.assertEqual(gen.call_count,6)
            self.assertEqual(vision.call_count,3)

    def test_rejection_persists_and_missing_anchor_disables_pointer(self):
        vision = Mock(return_value='{"has_garbled_text":true,"anchors":{}}')
        with tempfile.TemporaryDirectory() as tmp, patch.object(assets,'generate_picture',return_value=b'png') as gen:
            cache = {}
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'satu regenerasi'):
                    assets.generate_scene_assets(spec(),Path(tmp),'lift',['gear'],cache,Mock(),vision=vision)
            self.assertEqual((gen.call_count,vision.call_count),(4,2))
        shot = {'asset_id':'03_cutaway','camera':{},'overlay':{},'component':'gear'}
        assets.apply_anchors([shot],{})
        self.assertTrue(shot['unlocated'])
        self.assertEqual(shot['overlay']['type'],'badge_only')
