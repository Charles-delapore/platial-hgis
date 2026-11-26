"""Unit tests for D3-P7 three offline reproducible empirical case packs."""

import pathlib
import tempfile
import unittest

from platial_hgis.cases import (
    run_case_grand_canal_narrative,
    run_case_silk_road_contested,
    run_case_tang_song_poets,
)


class TestEmpiricalCases(unittest.TestCase):
    def test_all_three_cases_reproduce_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            c1 = run_case_tang_song_poets(root / "case1")
            self.assertEqual(c1["places_count"], 6)
            self.assertGreaterEqual(c1["cooccurrence_summary"]["edge_count"], 1)
            self.assertTrue(pathlib.Path(c1["outputs"]["lpf"]).exists())
            self.assertTrue(pathlib.Path(c1["outputs"]["geoparquet"]).exists())

            c2 = run_case_silk_road_contested(root / "case2")
            self.assertGreaterEqual(c2["places_count"], 5)
            self.assertEqual(c2["archival_silence_counts"]["contested"], 1)
            self.assertEqual(c2["archival_silence_counts"]["unrecorded"], 1)
            self.assertEqual(c2["archival_silence_counts"]["absent"], 1)
            self.assertGreater(c2["allen_loulan_vs_dunhuang"]["contemporary"], 0.9)

            c3 = run_case_grand_canal_narrative(root / "case3")
            self.assertEqual(c3["scenes_count"], 5)
            self.assertGreater(c3["narrative_html_bytes"], 4000)
            self.assertTrue(pathlib.Path(c3["outputs"]["narrative_html"]).exists())
            self.assertTrue(pathlib.Path(c3["outputs"]["review_html"]).exists())
            self.assertEqual(c3["provenance_stats"]["human_verified"], 1)
            self.assertEqual(c3["provenance_stats"]["ai_pending"], 1)


if __name__ == "__main__":
    unittest.main()
