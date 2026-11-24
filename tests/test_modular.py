import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import asset_generator as assets
import main_agent as agent
import mech_rig

EXAMPLE = Path(__file__).resolve().parents[1] / "video_engine/examples/pod-modular.json"


class RigTests(unittest.TestCase):
    def setUp(self):
        self.props = json.loads(EXAMPLE.read_text())
        self.plan = self.props["modular"]
        self.data = {"title": "Mesin kopi", "scenes": self.props["scenes"]}

    def test_prompt_is_compact_and_includes_every_scene(self):
        self.data["scenes"] = [dict(title=str(i), narration="壓力" * 700) for i in range(10)]
        prompt = mech_rig.build_prompt(self.data)
        self.assertLessEqual(len(prompt.encode()), 2000)
        for i in range(10):
            self.assertIn(f"\n{i}: {i}", prompt)

    def test_geometry_and_references_checked(self):
        self.assertEqual(mech_rig.validate(self.plan, 4), self.plan)
        for change in [
            lambda p: p["mech_rig"]["nodes"][0].update(x=940),
            lambda p: p["mech_rig"]["nodes"][1].update(y=400),
            lambda p: p["mech_rig"]["pipes"][0].update(id="cup"),
            lambda p: p["mech_rig"]["pipes"][0].update(points=[[240, 999], [905, 700]]),
            lambda p: p["scene_states"][0].update(focusNode="brew"),
            lambda p: p["scene_states"][0].update(active={"fake": 0.5}),
            lambda p: p["scene_states"][0].update(active={"cup": 2}),
            lambda p: p["scene_states"].pop(),
        ]:
            bad = copy.deepcopy(self.plan)
            change(bad)
            with self.assertRaises(ValueError):
                mech_rig.validate(bad, 4)

    def test_wing_contract_and_bounded_geometry(self):
        plan = json.loads(EXAMPLE.with_name("wing-modular.json").read_text())["modular"]
        self.assertEqual(mech_rig.validate(plan, 5, require_style=True), plan)
        self.assertIn("3: [analogi]", mech_rig.build_prompt(self.data, [{}, {}, {}, {"mode": "analogi"}]))
        for mutate in [
            lambda r: r.update(archetype="unknown"),
            lambda r: r["atmosphere"].update(particle="unsupported"),
            lambda r: r["atmosphere"].update(accent="url(#x)"),
            lambda r: r["nodes"][0].update(viewBox="0 0 0 900"),
            lambda r: r["nodes"][0]["paths"][0].update(d="<script>"),
            lambda r: r["nodes"][0]["paths"][0].update(d="M12 112 Q200 399"),
            lambda r: r["nodes"][0]["paths"][0].update(d="M12 112 L401 0"),
            lambda r: r["nodes"][0].update(paths=r["nodes"][0]["paths"] * 2),
            lambda r: r["nodes"][-1].update(visibleScenes=[5]),
            lambda r: next(n for n in r["nodes"] if n["id"] == "paper").update(visibleScenes=[0]),  # focus tersembunyi di adegan 3
        ]:
            bad = copy.deepcopy(plan)
            mutate(bad["mech_rig"])
            with self.assertRaises(ValueError):
                mech_rig.validate(bad, 5)

    def test_groq_first_and_checkpoint_reuse(self):
        # Migrasi checkpoint lama hanya sekali. Naskah dan audio tetap sama.
        self.data["modular"] = copy.deepcopy(self.plan)
        self.plan["mech_rig"].update(
            archetype="appliance_box",
            atmosphere={
                "bgTop": "#9d623e",
                "bgBottom": "#332d35",
                "accent": "#ffca8f",
                "gridStyle": "clean",
                "particle": "steam",
            },
        )
        groq = Mock(return_value=json.dumps(self.plan))
        gem = Mock()
        voice = {"timings": self.props["mechScenes"]}
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(agent, "SESSION_PATH", Path(tmp) / "session.json"),
            patch.object(
                agent, "build_text_sources", return_value=[("Gemini model", gem), ("Groq model", groq)]
            ) as sources,
        ):
            self.assertEqual(agent.prepare_modular(self.data, voice), self.plan)
            session = json.loads(agent.SESSION_PATH.read_text())
            self.assertEqual(session["voice"], voice)
            self.assertEqual(agent.prepare_modular(session["data"], voice), self.plan)
            groq.assert_called_once()
            gem.assert_not_called()
            sources.assert_called_once()


def toilet_plan():
    nodes = [
        {"id": "tankbody", "type": "casing", "x": 540, "y": 850, "w": 620, "h": 760, "label": "Tangki toilet"},
        {"id": "water", "type": "tank", "x": 380, "y": 780, "w": 200, "h": 320, "label": "Air tangki"},
        {"id": "btn", "type": "push_button", "x": 380, "y": 540, "w": 120, "h": 110, "label": "Tombol flush"},
        {"id": "ball", "type": "float_ball", "x": 470, "y": 720, "w": 130, "h": 170, "label": "Pelampung"},
        {"id": "flapper", "type": "valve", "x": 640, "y": 800, "w": 130, "h": 120, "label": "Katup flapper"},
        {"id": "siphon", "type": "siphon_pipe", "x": 660, "y": 1010, "w": 200, "h": 220, "label": "Sifon"},
    ]
    states = [
        {"sceneIndex": 0, "focusNode": "tankbody", "zoom": 1, "cutaway": 0, "active": {}},
        {"sceneIndex": 1, "focusNode": "btn", "zoom": 1.6, "cutaway": 1, "active": {"btn": 1}},
        {"sceneIndex": 2, "focusNode": "ball", "zoom": 1.5, "cutaway": 1, "active": {"ball": 0.8, "flapper": 0.9}},
        {"sceneIndex": 3, "focusNode": "siphon", "zoom": 1.4, "cutaway": 0.9, "active": {"siphon": 1}},
    ]
    return {"mech_rig": {"archetype": "bottle_tank", "nodes": nodes, "pipes": []}, "scene_states": states}


class AntiWeirdTests(unittest.TestCase):
    def test_toilet_rig_with_new_components_passes(self):
        self.assertEqual(mech_rig.validate(toilet_plan(), 4)["mech_rig"]["archetype"], "bottle_tank")
        self.assertIn("push_button", mech_rig.build_prompt({"title": "Toilet", "scenes": []}))

    def test_tiny_floating_and_lazy_zoom_rejected(self):
        for change in [
            lambda p: p["mech_rig"]["nodes"][2].update(w=40, h=40),          # tombol sekecil titik
            lambda p: p["mech_rig"]["nodes"][4].update(x=880, y=460),          # katup melayang di pojok luar bodi
            lambda p: p["scene_states"][1].update(zoom=1.1),                   # adegan inti tidak mendekat
        ]:
            bad = copy.deepcopy(toilet_plan())
            change(bad)
            with self.assertRaises(ValueError):
                mech_rig.validate(bad, 4)

    def test_comment_cta_stripped_from_closing(self):
        scenes = [{"lines": [{"speaker": "flay", "text": "Jadi begitu cara flush bekerja. Tulis pendapatmu di komentar!"}]}]
        agent.strip_comment_cta(scenes)
        self.assertNotIn("komentar", scenes[0]["narration"])
        self.assertIn("flush", scenes[0]["narration"])
        self.assertIn("AKURASI MEKANIS WAJIB", agent.build_prompt("toilet duduk", []))


class BlueprintAndGateTests(unittest.TestCase):
    def test_blueprint_locked_into_rig_prompt_and_topic_rule(self):
        data = {"title": "Toilet", "scenes": [],
                "mechanism_blueprint": {"components": ["tombol flush", "sifon"], "chain": ["tombol -> sifon"]}}
        prompt = mech_rig.build_prompt(data)
        self.assertIn("BLUEPRINT TERKUNCI", prompt)
        self.assertIn("tombol flush", prompt)
        self.assertIn("rantai mekanis/fluida/termal/listrik", agent.build_prompt(None, []))
        self.assertIn("mechanism_blueprint", agent.build_prompt("toilet", []))

    def test_vision_gate_revises_once_when_rejected(self):
        data = {"title": "Toilet", "scenes": [], "modular": {"lama": True}}
        props = {"modular": {}, "mechScenes": [
            {"startFrame": 0, "endFrame": 60, "triggerFrame": 20},
            {"startFrame": 60, "endFrame": 120, "triggerFrame": 80},
            {"startFrame": 120, "endFrame": 180, "triggerFrame": 140}]}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(agent, "REMOTION_DIR", tmp), patch.object(agent, "OUT_DIR", tmp), \
                patch.object(agent, "vision_caller", return_value=lambda prompt, pngs: '{"ok": false, "issues": ["komponen bertabrakan"]}'), \
                patch.object(agent.subprocess, "run") as run, \
                patch.object(agent, "prepare_modular", return_value={"rig": "baru"}) as prep:
            def fake_run(*a, **k):
                Path(a[0][5]).write_bytes(b"png")
            run.side_effect = fake_run
            self.assertEqual(agent.vision_gate(props, data, {}), {"rig": "baru"})
            prep.assert_called_once()
            self.assertNotIn("modular", data)

    def test_vision_gate_skips_without_vision(self):
        with patch.object(agent, "vision_caller", return_value=None):
            self.assertIsNone(agent.vision_gate({"modular": {}, "mechScenes": []}, {}, {}))


class ExteriorAndConnectionTests(unittest.TestCase):
    def test_exterior_prompt_locked_and_vision_regenerates_once(self):
        self.assertIn("solid dark slate studio background", assets.exterior_prompt("hand water pump"))
        self.assertIn("no cave", assets.exterior_prompt("hand water pump"))
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(assets, "generate_picture", side_effect=[b"first", b"second"]) as gen:
            vision = Mock(side_effect=['{"ok": false}', '{"ok": true}'])
            out = assets.generate_exterior({"title": "Pompa air tangan", "assets": []}, Path(tmp),
                                           {}, lambda: None, [], vision, lambda *a: None)
            self.assertEqual(out, "assets/01_exterior.png")
            self.assertEqual(gen.call_count, 2)
            self.assertIn("pompa air tangan", vision.call_args_list[0].args[0].lower())

    def test_analogy_label_must_be_scene_scoped(self):
        plan = toilet_plan()
        plan["mech_rig"]["nodes"].append({"id": "balon", "type": "context_object", "variant": "paper",
                                          "x": 500, "y": 700, "w": 150, "h": 150, "label": "Balon analogi"})
        with self.assertRaises(ValueError):
            mech_rig.validate(plan, 4)
        plan["mech_rig"]["nodes"][-1]["visibleScenes"] = [2]
        mech_rig.validate(plan, 4)

    def test_lever_must_touch_something(self):
        plan = toilet_plan()
        plan["mech_rig"]["nodes"].append({"id": "tuas", "type": "lever", "x": 240, "y": 500, "w": 100, "h": 100, "label": "Tuas"})
        with self.assertRaises(ValueError):  # jauh dari semua komponen (di dalam bodi tapi tidak bersentuhan)
            mech_rig.validate(plan, 4)
        plan["mech_rig"]["nodes"][-1].update(x=430, y=560)  # menempel tombol/tangki
        mech_rig.validate(plan, 4)

    def test_end_pad_is_tight_for_loop(self):
        self.assertLessEqual(agent.END_PAD, 0.35)


class PerformanceAndStoryTests(unittest.TestCase):
    def test_prompt_states_exact_scene_count_and_focus_not_stuck(self):
        data = {"title": "Dongkrak", "scenes": [{"title": str(i), "narration": "x"} for i in range(8)],
                "mechanism_blueprint": {"components": ["tuas"], "chain": []}}
        self.assertIn("WAJIB TEPAT 8 objek di scene_states (sceneIndex 0..7)", mech_rig.build_prompt(data))
        plan = toilet_plan()
        plan["scene_states"][0].update(focusNode="btn")  # btn,btn,btn = 3 berturut-turut
        plan["scene_states"][2].update(focusNode="btn")
        plan["scene_states"][1].update(focusNode="btn")
        with self.assertRaises(ValueError):
            mech_rig.validate(plan, 4)

    def test_cleanup_public_stale_removes_clips_only(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(agent, "PUBLIC_DIR", tmp):
            clips = Path(tmp) / "clips"
            clips.mkdir()
            (clips / "scene_01.mp4").write_bytes(b"x" * 10)
            (Path(tmp) / "bgm.mp3").write_bytes(b"keep")
            agent.cleanup_public_stale()
            self.assertEqual(list(clips.iterdir()), [])
            self.assertTrue((Path(tmp) / "bgm.mp3").exists())

    def test_story_images_three_locked_subjects(self):
        data = {"title": "Dongkrak hidrolik", "assets": [], "scenes": [{"narration": "Ibarat pompa tangan.", "title": "Analogi"}]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(assets, "generate_picture", return_value=b"png") as gen:
            out = assets.generate_story_images(data, Path(tmp), {}, lambda: None, [], None, lambda *a: None)
            self.assertEqual(set(out), {"exterior", "analogy", "payoff"})
            subjects = " ".join(c.args[0] for c in gen.call_args_list)
            self.assertIn("actively doing its real job", subjects)
            self.assertIn("successful final result", subjects)
