import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import clip_fetcher as cf

BIG = b"x" * 20_000


def fake_response(status=200, json_data=None, content=BIG):
    res = Mock(status_code=status, text="err", content=content)
    res.json.return_value = json_data or {}
    res.raise_for_status = Mock()
    return res


def pexels_payload(vid_id=1, link="https://x/v.mp4"):
    return {"videos": [{"id": vid_id, "video_files": [{"file_type": "video/mp4", "width": 720, "link": link}]}]}


class ClipFetcherTests(unittest.TestCase):
    def scenes(self):
        return [{"id": "scene_01", "visualPrompt": "Photorealistic vertical 9:16 close-up of elevator motor pulling cable", "title": "Motor lift"},
                {"id": "scene_02", "visualPrompt": "Photorealistic vertical shot of steel brake clamping rail", "title": "Rem baja"}]

    def test_build_queries_layers_from_specific_to_generic(self):
        queries = cf._build_queries(self.scenes()[0]["visualPrompt"], "Motor lift")
        self.assertEqual(queries[0], "elevator motor")
        self.assertEqual(queries[1:4], ["elevator", "motor", "pulling"])
        self.assertIn("motor lift", queries)
        self.assertEqual(queries[-3:], ["water flow", "engineering machine", "science technology"])
        self.assertEqual(len(queries), len(set(queries)))

    def test_clear_clips_only_removes_scene_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "scene_01.mp4").write_bytes(b"x")
            (d / "keep.txt").write_text("jangan hapus")
            cf.clear_clips(d)
            self.assertEqual([p.name for p in d.iterdir()], ["keep.txt"])

    def test_pexels_downloads_and_records_id(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"PEXELS_API_KEY": "p"}, clear=True), \
                patch.object(cf.requests, "get", side_effect=[fake_response(json_data=pexels_payload()), fake_response()]):
            cf.fill_clips(self.scenes()[:1], Path(tmp), log=lambda *a: None)
            out = Path(tmp) / "scene_01.mp4"
            self.assertTrue(out.exists() and out.stat().st_size > 10_000)

    def test_same_video_never_downloaded_twice(self):
        # Kedua adegan mendapat video id yang sama dari Pexels; adegan kedua harus melewatinya.
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"PEXELS_API_KEY": "p"}, clear=True), \
                patch.object(cf.requests, "get", side_effect=[
                    fake_response(json_data=pexels_payload(7)), fake_response(),            # adegan 1: unduh id 7
                    fake_response(json_data=pexels_payload(7)),                              # adegan 2 query 1: id 7 sudah dipakai
                    fake_response(json_data=pexels_payload(8, "https://x/w.mp4")), fake_response(),  # query berikutnya: id 8
                ]) as get:
            logs = []
            cf.fill_clips(self.scenes(), Path(tmp), log=logs.append)
            self.assertTrue((Path(tmp) / "scene_02.mp4").exists())
            self.assertTrue(any("scene_02" in line for line in logs))

    def test_query_widens_when_first_query_empty(self):
        calls = []

        def responder(url, **kw):
            if "pexels" in url:
                calls.append(kw["params"]["query"])
                if len(calls) == 1:
                    return fake_response(json_data={"videos": []})
                return fake_response(json_data=pexels_payload())
            return fake_response()

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"PEXELS_API_KEY": "p"}, clear=True), \
                patch.object(cf.requests, "get", side_effect=responder):
            cf.fill_clips(self.scenes()[:1], Path(tmp), log=lambda *a: None)
            self.assertEqual(calls[:2], ["elevator motor", "elevator"])
            self.assertTrue((Path(tmp) / "scene_01.mp4").exists())

    def test_pixabay_fallback_and_existing_clip_skipped(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"PIXABAY_API_KEY": "p"}, clear=True), \
                patch.object(cf.requests, "get", side_effect=[
                    fake_response(json_data={"hits": [{"id": 3, "videos": {"medium": {"url": "https://x/p.mp4"}}}]}),
                    fake_response()]) as get:
            (Path(tmp) / "scene_02.mp4").write_bytes(BIG)
            cf.fill_clips(self.scenes(), Path(tmp), log=lambda *a: None)
            self.assertTrue((Path(tmp) / "scene_01.mp4").exists())
            # hanya dua panggilan (cari + unduh) untuk scene_01; scene_02 tidak dicari sama sekali
            self.assertEqual(get.call_count, 2)

    def test_tiny_download_rejected_and_no_keys_noop(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            cf.fill_clips(self.scenes(), Path(tmp), log=lambda *a: None)
            self.assertEqual(list(Path(tmp).iterdir()), [])
        with tempfile.TemporaryDirectory() as tmp, patch.object(cf.requests, "get", return_value=fake_response(content=b"tiny")):
            out = Path(tmp) / "scene_01.mp4"
            self.assertFalse(cf._download("https://x/v.mp4", out))
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
