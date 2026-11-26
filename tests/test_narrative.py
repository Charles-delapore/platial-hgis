"""Unit tests for D3-P5 evidence-bound narrative storyboard validator."""

import pathlib
import tempfile
import unittest
import yaml

from platial_hgis.narrative import (
    NarrativeValidationError,
    load_storyboard,
    parse_storyboard_dict,
)


class TestNarrativeValidator(unittest.TestCase):
    def _base_script(self) -> dict:
        return {
            "storyboard_id": "canal-demo",
            "title": "Grand Canal Narrative Test",
            "sources": [
                {
                    "source_id": "src-ming-shi",
                    "label": "History of Ming (Hequzhi / River & Canal Treatise)",
                    "evidence_level": "verified",
                }
            ],
            "scenes": [
                {
                    "narrative_unit_id": "u1",
                    "map_scene_id": "s1",
                    "title": "Qingjiangpu Lock Complex",
                    "heritage_element": "Qingjiangpu Sluice & Granary Hub",
                    "narrative_text": "Ming canal grain transport hub at the Yellow-Huai-Canal junction.",
                    "when": {
                        "earliest_start": 1415,
                        "latest_start": 1415,
                        "earliest_end": 1855,
                        "latest_end": 1855,
                    },
                    "camera": {
                        "center": [119.015, 33.610],
                        "zoom": 10.5,
                        "bearing": -15,
                        "pitch": 35,
                        "shot_type": "establishing",
                    },
                    "evidence_level": "verified",
                    "evidence_ids": ["src-ming-shi"],
                    "temporal_shift": "chronological",
                    "transition": "fly_to",
                }
            ],
        }

    def test_valid_yaml_storyboard_loads(self) -> None:
        raw = self._base_script()
        with tempfile.TemporaryDirectory() as tmp:
            ypath = pathlib.Path(tmp) / "story.yaml"
            ypath.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
            sb = load_storyboard(ypath)
            self.assertEqual(len(sb.scenes), 1)
            self.assertEqual(sb.scenes[0].evidence_ids, ("src-ming-shi",))

    def test_rejects_uncited_non_speculative_scene(self) -> None:
        raw = self._base_script()
        raw["scenes"][0]["evidence_ids"] = []
        raw["scenes"][0]["evidence_level"] = "verified"
        with self.assertRaises(NarrativeValidationError):
            parse_storyboard_dict(raw)

        # Speculative scene without evidence_ids IS permitted
        raw["scenes"][0]["evidence_level"] = "speculative"
        sb = parse_storyboard_dict(raw)
        self.assertEqual(sb.scenes[0].evidence_level, "speculative")

    def test_rejects_undeclared_source_and_missing_camera(self) -> None:
        raw = self._base_script()
        raw["scenes"][0]["evidence_ids"] = ["src-missing"]
        with self.assertRaises(NarrativeValidationError):
            parse_storyboard_dict(raw)

        raw2 = self._base_script()
        del raw2["scenes"][0]["camera"]
        with self.assertRaises(NarrativeValidationError):
            parse_storyboard_dict(raw2)


if __name__ == "__main__":
    unittest.main()
