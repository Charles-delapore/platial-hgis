"""Unit tests for D3-P2 SQLite FTS5 gazetteer index."""

import pathlib
import unittest

from platial_hgis.connectors import load_chgis_geoparquet, load_periodo_json, load_whg_lpf
from platial_hgis.gazetteer import GazetteerIndex, duckdb_available
from platial_hgis.primitives import CompetingGeometry, FuzzyInterval, PlatialAttributes, PlatialPlace

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"
EXTERNAL_DL = pathlib.Path("/working_dir/c_2a576c8df0e2a8ca/downloads")


class TestGazetteerIndex(unittest.TestCase):
    def test_fts5_and_cjk_temporal_search(self) -> None:
        p_tang = PlatialPlace(
            place_id="demo:chang-an-tang",
            title="京兆府",
            fclasses=("A", "P"),
            names=[{"toponym": "长安", "lang": "zh"}, {"toponym": "Chang'an", "lang": "en"}],
            when=FuzzyInterval.from_crisp(713, 907, label="Tang"),
            geometries=[
                CompetingGeometry("h1", {"type": "Point", "coordinates": [108.94, 34.26]}, 1.0, uncertainty_radius_km=10.0)
            ],
            platial=PlatialAttributes(location={"dynasty": "Tang", "lev_rank": 3, "type_ch": "府"}),
        )
        p_qing = PlatialPlace(
            place_id="demo:xian-qing",
            title="西安府",
            fclasses=("A", "P"),
            names=[{"toponym": "长安县", "lang": "zh"}, {"toponym": "Xi'an", "lang": "en"}],
            when=FuzzyInterval.from_crisp(1644, 1911, label="Qing"),
            geometries=[
                CompetingGeometry("h1", {"type": "Point", "coordinates": [108.95, 34.27]}, 1.0, uncertainty_radius_km=8.0)
            ],
            platial=PlatialAttributes(location={"dynasty": "Qing", "lev_rank": 3, "type_ch": "府"}),
        )

        with GazetteerIndex(":memory:") as idx:
            idx.add_places([p_tang, p_qing])
            idx.add_places(load_whg_lpf(FIXTURES / "whg-place-sample.json"))
            idx.add_period(load_periodo_json(FIXTURES / "periodo-sample-darkage.json"))

            self.assertEqual(idx.count_places(), 3)
            # Temporal filter isolates Tang record
            tang_hits = idx.search("长安", year_start=750, year_end=760)
            self.assertEqual(len(tang_hits), 1)
            self.assertEqual(tang_hits[0].place_id, "demo:chang-an-tang")

            # Multilingual WHG FTS5 lookup
            ist_hits = idx.search("Constantinople")
            self.assertEqual(len(ist_hits), 1)
            self.assertEqual(ist_hits[0].title, "İstanbul")

    def test_duckdb_graceful_fallback(self) -> None:
        if not duckdb_available():
            with self.assertRaises(RuntimeError):
                GazetteerIndex.query_geoparquet_duckdb("nonexistent.parquet")

    def test_external_chgis_full_indexing_when_available(self) -> None:
        pq_file = EXTERNAL_DL / "chgis-tangsong-mingqing-pref-snapshot.geoparquet"
        if pq_file.exists():
            places = load_chgis_geoparquet(pq_file)
            with GazetteerIndex(":memory:") as idx:
                n = idx.add_places(places)
                self.assertEqual(n, 810)
                hits = idx.search("高平", year_start=750, year_end=750)
                self.assertGreaterEqual(len(hits), 1)
                self.assertEqual(hits[0].title, "高平郡")


if __name__ == "__main__":
    unittest.main()
