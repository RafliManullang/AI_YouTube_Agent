import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

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

    @patch.object(assets.time, "sleep")
    def test_script_to_props_partial_resume_and_vision_correction(self, sleep):
        data = {'title': 'Water heater', 'assets': spec(), 'scenes': []}
        for i, key in enumerate(['01_exterior', '03_cutaway', '02_analogy', '04_closeup', '01_exterior']):
            data['scenes'].append(dict(start=i, end=i+1, title='heater', narration='heater', asset_id=key,
                                       component='coil', overlay={'type':'heat_pulse'}))
        voice = {'timings': agent.render_timings(data['scenes'], [], 5)}
        text = json.dumps({'has_garbled_text': True, 'anchors': {}})
        clean = json.dumps({'has_garbled_text': False, 'anchors': {'coil':[.3,.7]}})
        vision = Mock(side_effect=[RuntimeError('quota'), text, clean])
        with tempfile.TemporaryDirectory() as tmp, patch.object(agent,'PUBLIC_DIR',tmp), \
                patch.object(agent,'SESSION_PATH',Path(tmp)/'last_session.json'), patch.object(agent,'GEMINI_KEYS',[]), \
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
            sleep.reset_mock()
            self.assertEqual(plan, resume())
            sleep.assert_not_called()
            self.assertEqual(gen.call_count,5)
            self.assertEqual(vision.call_count,3)
            self.assertEqual(gen.call_args_list[3].args[1],gen.call_args_list[2].args[1]+1)
            self.assertTrue(all(assets.MASTER_STYLE_PROMPT in c.args[0] for c in gen.call_args_list))
            (Path(tmp)/'assets/01_exterior.png').write_bytes(b'corrupt')
            self.assertEqual(plan,resume())
            self.assertEqual(gen.call_count,6)
            self.assertEqual(vision.call_count,3)

    @patch.object(assets.time, "sleep")
    def test_rejection_persists_and_missing_anchor_disables_pointer(self, sleep):
        vision = Mock(return_value='{"has_garbled_text":true,"anchors":{}}')
        with tempfile.TemporaryDirectory() as tmp, patch.object(assets,'generate_picture',return_value=b'png') as gen:
            cache = {}
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'satu regenerasi'):
                    assets.generate_scene_assets(spec(),Path(tmp),'lift',['gear'],cache,Mock(),vision=vision)
            self.assertEqual((gen.call_count,vision.call_count),(4,2))
            self.assertEqual(sleep.call_args_list, [call(2)] * 3)
        shot = {'asset_id':'03_cutaway','camera':{},'overlay':{},'component':'gear'}
        assets.apply_anchors([shot],{})
        self.assertTrue(shot['unlocated'])
        self.assertEqual(shot['overlay']['type'],'badge_only')


class ImageProviderTests(unittest.TestCase):
    @staticmethod
    def portrait():
        buf = io.BytesIO()
        Image.new('RGB', (256, 448)).save(buf, 'JPEG')
        return buf.getvalue()

    def test_rotate_models_then_keys_and_stop_on_image(self):
        from google.genai import types
        first, second = Mock(), Mock()
        first.models.generate_content.side_effect = RuntimeError('429 quota exhausted')
        second.models.generate_content.side_effect = [
            types.GenerateContentResponse(candidates=[]),
            types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(parts=[
                types.Part.from_text(text='note'), types.Part.from_bytes(data=self.portrait(), mime_type='image/jpeg')]))]),
        ]
        log = Mock()
        with patch.dict(os.environ, {'IMAGE_MODEL': 'custom-image'}), patch.object(assets.requests, 'post') as hf:
            png = assets.generate_picture('prompt', 123, [first, second], log)
            hf.assert_not_called()
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1080, 1920))
        expected = ['custom-image', *assets.GEMINI_IMAGE_MODELS[1:]]
        for client, models in [(first, expected), (second, expected[:2])]:
            calls = client.models.generate_content.call_args_list
            self.assertEqual([c.kwargs['model'] for c in calls], models)
            for c in calls:
                self.assertEqual(c.kwargs['contents'], 'prompt')
                self.assertEqual(c.kwargs['config'].response_modalities, ['IMAGE'])
                self.assertEqual(c.kwargs['config'].image_config.aspect_ratio, '9:16')
        self.assertIn('429 quota exhausted', log.call_args_list[0].args[0])
        self.assertIn('tidak mengembalikan data gambar', log.call_args_list[-1].args[0])

    def test_hf_after_exhaustion(self):
        client = Mock()
        client.models.generate_content.side_effect = RuntimeError('503')
        with patch.dict(os.environ, {'HF_TOKEN':'test', 'IMAGE_MODEL':'gemini-2.5-flash-image'}), \
                patch.object(assets.requests, 'post') as hf:
            hf.return_value.content = self.portrait()
            assets.generate_picture('prompt', 7, [client], Mock())
            self.assertEqual(client.models.generate_content.call_count, 3)  # override duplikat
            hf.assert_called_once_with(assets.HF_FLUX_URL, timeout=120,
                headers={'Authorization':'Bearer test', 'Accept':'image/png'},
                json={'inputs':'prompt','parameters':{'width':768, 'height':1344, 'seed':7}})
            hf.return_value.raise_for_status.assert_called_once()

    def test_missing_hf_token_no_unauthenticated_request(self):
        with patch.dict(os.environ, {'HF_TOKEN':' '}), patch.object(assets.requests, 'post') as hf:
            with self.assertRaisesRegex(RuntimeError, 'HF_TOKEN'):
                assets.generate_picture('prompt', 7, [], Mock())
            hf.assert_not_called()
