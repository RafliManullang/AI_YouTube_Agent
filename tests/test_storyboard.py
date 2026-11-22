import json
import tempfile
import unittest
from pathlib import Path

import main_agent as agent
import schema_gate
import storyboard_exporter as sb


def make_scenes(n=3):
    return [dict(id=f"scene_{i + 1:02d}", start=i * 2.0, end=(i + 1) * 2.0,
                 narration=f"Narasi adegan {i + 1} yang cukup panjang.",
                 visualPrompt=f"Photorealistic vertical 9:16 shot number {i + 1}", tone="santai") for i in range(n)]


class StoryboardTests(unittest.TestCase):
    def test_clip_plan_frames_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            clips = Path(tmp)
            (clips / "scene_02.png").write_bytes(b"x")
            plan = sb.build_clip_plan(make_scenes(), clips)
            self.assertEqual([p["startFrame"] for p in plan], [0, 60, 120])
            self.assertTrue(all(p["durationInFrames"] == 60 for p in plan))
            self.assertEqual(plan[1]["clipPath"], "clips/scene_02.png")
            self.assertEqual([p["id"] for p in sb.missing_clips(plan)], ["scene_01", "scene_03"])

    def test_storyboard_files_list_prompts_and_durations(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenes = make_scenes(2)
            plan = sb.build_clip_plan(scenes, Path(tmp))
            txt, html = sb.write_storyboard(scenes, plan, Path(tmp) / "out", "Topik Uji")
            text = txt.read_text()
            self.assertIn("scene_01.mp4", text)
            self.assertIn("2.0 detik", text)
            self.assertIn("Photorealistic vertical", text)
            self.assertIn("scene_02", html.read_text())

    def test_validate_content_requires_no_visual_code(self):
        data = {"title": "Cara kerja lift", "description": "d", "tags": ["sains"], "category": "CARA KERJA",
                "thumbnail_text": "LIFT?", "music": "tenang",
                "scenes": [{"lines": [{"speaker": "flay", "text": "Lift naik karena motor menarik kabel baja kuat."}],
                            "title": "Motor menarik", "visualPrompt": "Photorealistic vertical 9:16 elevator motor pulling a steel cable"},
                           {"lines": [{"speaker": "flay", "text": "Balok penyeimbang turun saat kabin naik perlahan."}],
                            "title": "Penyeimbang"},
                           {"lines": [{"speaker": "flay", "text": "Rem pengaman langsung mengunci rel ketika kabel putus."}],
                            "title": "Rem aman"}]}
        agent.validate_content(data)
        self.assertEqual([s["id"] for s in data["scenes"]], ["scene_01", "scene_02", "scene_03"])
        self.assertTrue(all(s["visualPrompt"] for s in data["scenes"]))
        self.assertNotIn("assets", data)

    def test_schema_gate_accepts_new_props(self):
        props = {"audioUrl": "voice.mp3", "durationInSeconds": 6.0, "words": [],
                 "scenes": [{"id": "scene_01", "narration": "Halo dunia", "visualPrompt": "A shot",
                             "clipPath": "", "startFrame": 0, "durationInFrames": 180}]}
        fixed = schema_gate.auto_fix(json.loads(json.dumps(props)))
        self.assertEqual(fixed["scenes"][0]["id"], "scene_01")


if __name__ == "__main__":
    unittest.main()
