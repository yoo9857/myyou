from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline


class SfxWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "movie.srt").write_text(
            "1\n00:00:08,000 --> 00:00:09,000\nprevious line\n",
            encoding="utf-8",
        )
        self.config = {"subtitle": "movie.srt", "narration_sfx_max_uses": 8}
        self.plan = {
            "segments": [{
                "order": 1,
                "source_start": 10.0,
                "source_end": 20.0,
                "narration": "A short line.",
                "narration_sfx_preroll": "bass_omen",
                "narration_sfx_lead_seconds": 0.5,
                "narration_sfx_rationale": "An ominous but unprotected setup.",
                "narration_scene_protection": "clear",
            }]
        }
        self.manifest = {
            "global_rules": {
                "max_uses_per_19_25_min_review": 8,
                "minimum_seconds_between_any_sfx": 25,
                "minimum_seconds_before_reusing_same_sfx": 90,
            },
            "assets": {"bass_omen": {"duration_seconds": 0.7, "max_uses_per_review": 2}},
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self) -> None:
        asset = ("bass_omen", self.root / "bass.wav", self.manifest["assets"]["bass_omen"])
        with patch.object(pipeline, "ROOT", self.root), patch.object(
            pipeline, "load_sfx_manifest", return_value=self.manifest
        ), patch.object(pipeline, "segment_sfx_asset", return_value=asset):
            pipeline.validate_sfx_plan(self.plan, self.config)

    def test_accepts_dialogue_free_preroll_with_short_tail(self) -> None:
        self.validate()

    def test_rejects_movie_dialogue_collision(self) -> None:
        (self.root / "movie.srt").write_text(
            "1\n00:00:10,100 --> 00:00:10,300\nimportant line\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "영화 대사와 겹칩니다"):
            self.validate()

    def test_rejects_long_tail_under_narration(self) -> None:
        self.plan["segments"][0]["narration_sfx_lead_seconds"] = 0.2
        with self.assertRaisesRegex(ValueError, "꼬리 겹침"):
            self.validate()

    def test_rejects_protected_scene(self) -> None:
        self.plan["segments"][0]["narration_scene_protection"] = "active_combat"
        with self.assertRaisesRegex(ValueError, "보호 장면"):
            self.validate()


class NarrationRhythmGateTests(unittest.TestCase):
    def test_rejects_three_consecutive_narration_segments(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan_path = Path(td) / "edit_plan.json"
            segments = []
            for index in range(3):
                segments.append({
                    "order": index + 1,
                    "source_start": index * 400.0,
                    "source_end": (index + 1) * 400.0,
                    "narration": f"line {index + 1}",
                })
            plan_path.write_text(__import__("json").dumps({"segments": segments}), encoding="utf-8")
            config = {
                "plan_min_segments": 1,
                "plan_max_segments": 10,
                "plan_max_clip_seconds": 500,
                "enforce_narration_rhythm_gate": True,
            }
            with patch.object(pipeline, "load_config", return_value=config), patch.object(
                pipeline, "validate_story_coverage"
            ), patch.object(pipeline, "validate_sfx_plan"):
                with self.assertRaisesRegex(ValueError, "3개 이상 연속"):
                    pipeline.validate_plan(plan_path, 1201.0, 1320.0)


if __name__ == "__main__":
    unittest.main()
