import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

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
            lambda r: r["nodes"][-1].update(visibleScenes=[0]),  # focus tersembunyi di adegan 3
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
