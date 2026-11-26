"""Unit tests for D3-P5 zero-backend interactive HTML narrative compiler."""

import pathlib
import tempfile
import unittest

from platial_hgis.narrative import parse_storyboard_dict
from platial_hgis.narrative_html import compile_narrative_html


class TestNarrativeHTMLCompiler(unittest.TestCase):
    def test_compile_standalone_offline_html(self) -> None:
        sb = parse_storyboard_dict(
            {
                "storyboard_id": "test-canal",
                "title": "Grand Canal Test Story",
                "subtitle": "Qingjiangpu to Hangzhou",
                "sources": [
                    {
                        "source_id": "src-1",
                        "label": "Qingjiangpu Historical Canal Archive (demo)",
                        "evidence_level": "verified",
                    }
                ],
                "scenes": [
                    {
                        "narrative_unit_id": "u1",
                        "map_scene_id": "s1",
                        "title": "Qingjiangpu",
                        "heritage_element": "Qingjiangpu Sluice",
                        "narrative_text": "Canal hub text.",
                        "when": {"earliest_start": 1415, "latest_start": 1415, "earliest_end": 1855, "latest_end": 1855},
                        "camera": {"center": [119.015, 33.610], "zoom": 10.0, "shot_type": "establishing"},
                        "evidence_level": "verified",
                        "evidence_ids": ["src-1"],
                    },
                    {
                        "narrative_unit_id": "u2",
                        "map_scene_id": "s2",
                        "title": "Yangzhou",
                        "heritage_element": "Guazhou Crossing",
                        "narrative_text": "Canal-Yangtze junction.",
                        "when": {"earliest_start": 605, "latest_start": 610, "earliest_end": 1900, "latest_end": 1911},
                        "camera": {"center": [119.41, 32.39], "zoom": 9.5, "shot_type": "tracking"},
                        "evidence_level": "indirect",
                        "evidence_ids": ["src-1"],
                    },
                ],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "story.html"
            html_str = compile_narrative_html(sb, out)
            self.assertTrue(out.exists())
            self.assertIn("<!DOCTYPE html>", html_str)
            self.assertIn("Grand Canal Test Story", html_str)
            self.assertIn("Qingjiangpu Sluice", html_str)
            # Zero external CDN dependencies
            self.assertNotIn("https://cdn", html_str)
            self.assertNotIn("unpkg.com", html_str)


if __name__ == "__main__":
    unittest.main()
