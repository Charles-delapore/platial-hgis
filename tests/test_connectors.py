"""Unit tests for D3-P2 connectors (WHG, PeriodO, CBDB schema, Cliopatria, CHGIS external)."""

import json
import pathlib
import tempfile
import unittest

from platial_hgis.connectors import (
    CBDBLicenseError,
    CBDBSchemaValidator,
    load_cbdb_sources_inventory,
    load_chgis_geoparquet,
    load_chgis_shapefile_zip,
    load_cliopatria_geojson,
    load_periodo_json,
    load_whg_lpf,
)

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"
EXTERNAL_DL = pathlib.Path("/working_dir/c_2a576c8df0e2a8ca/downloads")


class TestConnectors(unittest.TestCase):
    def test_load_whg_and_periodo_fixtures(self) -> None:
        places = load_whg_lpf(FIXTURES / "whg-place-sample.json")
        self.assertEqual(len(places), 1)
        self.assertEqual(places[0].title, "İstanbul")

        per = load_periodo_json(FIXTURES / "periodo-sample-cultural-revolution.json")
        self.assertEqual(per["id"], "p06c6g3bsbt")
        self.assertEqual(per["interval"].earliest_start, 1966.0)
        self.assertEqual(per["interval"].latest_end, 1976.0)

    def test_cbdb_sources_inventory_and_schema_license_guard(self) -> None:
        inv = load_cbdb_sources_inventory(FIXTURES / "cbdb-sources-inventory.csv")
        self.assertGreaterEqual(len(inv), 10)
        self.assertIn("source", inv[0])

        validator = CBDBSchemaValidator(allow_out_of_release=False)
        ok_row = {
            "cbdb_person_id": "DEMO-001",
            "name_ch": "示例人物",
            "name_py": "Shili Renwu",
            "dynasty": "Tang",
            "birth_year": "701",
            "death_year": "762",
            "index_year": "731",
            "birth_place": "绵州",
            "index_place": "长安",
            "entry_method": "举荐",
            "social_status": "诗人",
            "source_text": "Open schema validation synthetic test row (not real CBDB)",
            "cbdb_release": "CBDB_bi_20250520",
            "license_tier": "CC BY-NC-SA 4.0 (in-release)",
        }
        validator.validate_row(ok_row)

        bad_tier = dict(ok_row, license_tier="CBDB-2026-terms (out-of-release)")
        with self.assertRaises(CBDBLicenseError):
            validator.validate_row(bad_tier)

        no_source = dict(ok_row, source_text="")
        with self.assertRaises(CBDBLicenseError):
            validator.validate_row(no_source)

    def test_cliopatria_geojson_loader(self) -> None:
        sample_clio = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "Name": "Tang Dynasty",
                        "FromYear": 618,
                        "ToYear": 907,
                        "Area": 5400000.0,
                        "Type": "POLITY",
                        "Wikidata": "Q9683",
                        "SeshatID": "CnTang*",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[100, 30], [115, 30], [115, 40], [100, 40], [100, 30]]],
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "clio.geojson"
            p.write_text(json.dumps(sample_clio), encoding="utf-8")
            matched = load_cliopatria_geojson(p, year=750)
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0].title, "Tang Dynasty")
            self.assertEqual(len(load_cliopatria_geojson(p, year=1200)), 0)

    def test_external_chgis_loaders_when_available(self) -> None:
        # External CHGIS files are NOT vendored in git (CHGIS V6 EULA);
        # test automatically validates them when present in the local sandbox downloads.
        pq_file = EXTERNAL_DL / "chgis-tangsong-mingqing-pref-snapshot.geoparquet"
        if pq_file.exists():
            tang = load_chgis_geoparquet(pq_file, dynasty_filter="Tang", limit=20)
            self.assertEqual(len(tang), 20)
            self.assertEqual(tang[0].provenance, "chgis_v6_external")
            self.assertGreater(tang[0].primary_geometry.uncertainty_radius_km, 0.0)

        zip_file = EXTERNAL_DL / "v6_time_pref_pts_utf_wgs84.zip"
        if zip_file.exists():
            pts = load_chgis_shapefile_zip(zip_file, limit=25)
            self.assertEqual(len(pts), 25)
            self.assertEqual(pts[0].fclasses, ("A", "P"))


if __name__ == "__main__":
    unittest.main()
