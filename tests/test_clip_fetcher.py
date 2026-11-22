import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import clip_fetcher as cf


def fake_response(status=200, json_data=None, content=b"x" * 5000):
    res = Mock(status_code=status, text="err", content=content)
    res.json.return_value = json_data or {}
    res.raise_for_status = Mock()
    return res


class ClipFetcherTests(unittest.TestCase):
    def scenes(self):
        return [{"id": "scene_01", "visualPrompt": "Photorealistic vertical 9:16 close-up of elevator motor pulling cable, cinematic camera"},
                {"id": "scene_02", "visualPrompt": "Photorealistic vertical shot of steel brake clamping rail"}]

    def test_short_query_drops_style_words(self):
        self.assertEqual(cf._short_query(self.scenes()[0]["visualPrompt"], "x"), "elevator motor pulling")

    def test_clear_clips_only_removes_scene_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "scene_01.mp4").write_bytes(b"x")
            (d / "keep.txt").write_text("jangan hapus")
            cf.clear_clips(d)
            self.assertEqual([p.name for p in d.iterdir()], ["keep.txt"])

    def test_fal_first_then_no_more_calls_for_that_scene(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"FAL_KEY": "k"}, clear=True), \
                patch.object(cf.requests, "post", return_value=fake_response(json_data={"images": [{"url": "https://x/y.png"}]})) as post, \
                patch.object(cf.requests, "get", return_value=fake_response()) as get:
            cf.fill_clips(self.scenes()[:1], Path(tmp), log=lambda *a: None)
            self.assertTrue((Path(tmp) / "scene_01.png").exists())
            post.assert_called_once()
            self.assertIn("portrait_16_9", str(post.call_args.kwargs["json"]))

    def test_falls_back_to_pexels_when_fal_fails(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"FAL_KEY": "k", "PEXELS_API_KEY": "p"}, clear=True), \
                patch.object(cf.requests, "post", return_value=fake_response(status=500)) , \
                patch.object(cf.requests, "get", side_effect=[
                    fake_response(json_data={"videos": [{"video_files": [{"file_type": "video/mp4", "width": 720, "link": "https://x/v.mp4"}]}]}),
                    fake_response()]):
            cf.fill_clips(self.scenes()[:1], Path(tmp), log=lambda *a: None)
            self.assertTrue((Path(tmp) / "scene_01.mp4").exists())

    def test_existing_clip_is_not_refetched(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"FAL_KEY": "k"}, clear=True), \
                patch.object(cf.requests, "post") as post:
            (Path(tmp) / "scene_01.mp4").write_bytes(b"x" * 5000)
            cf.fill_clips(self.scenes()[:1], Path(tmp), log=lambda *a: None)
            post.assert_not_called()

    def test_no_keys_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            cf.fill_clips(self.scenes(), Path(tmp), log=lambda *a: None)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
