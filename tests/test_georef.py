"""Unit tests for D3-P3 Allmaps/Maplat parsers and non-distorting coordinate bridge."""

import pathlib
import unittest

from platial_hgis.georef import (
    NonDistortingBridge,
    haversine_m,
    lonlat_to_mercator,
    mercator_to_lonlat,
    parse_allmaps_annotation,
    parse_maplat_standard,
)

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


class TestGeorefBridge(unittest.TestCase):
    def test_mercator_roundtrip(self) -> None:
        mx, my = lonlat_to_mercator(106.6974, 10.7791)
        lon, lat = mercator_to_lonlat(mx, my)
        self.assertAlmostEqual(lon, 106.6974, places=6)
        self.assertAlmostEqual(lat, 10.7791, places=6)

    def test_parse_real_allmaps_and_maplat_saigon_consistency(self) -> None:
        am_spec = parse_allmaps_annotation(FIXTURES / "allmaps-example-saigon-annotation.json")
        ml_spec = parse_maplat_standard(FIXTURES / "allmaps-saigon-maplat-standard.json")

        self.assertEqual(am_spec.width, 16267)
        self.assertEqual(am_spec.height, 14859)
        self.assertEqual(len(am_spec.gcps), 6)
        self.assertEqual(len(ml_spec.gcps), 6)
        self.assertIsNotNone(am_spec.svg_mask)

        # Verify Maplat Mercator-converted GCPs match Allmaps WGS84 GCPs within 1 meter
        for g_am, g_ml in zip(am_spec.gcps, ml_spec.gcps):
            self.assertEqual(g_am.pixel_x, g_ml.pixel_x)
            self.assertEqual(g_am.pixel_y, g_ml.pixel_y)
            self.assertLess(haversine_m(g_am.lon, g_am.lat, g_ml.lon, g_ml.lat), 1.0)

    def test_tps_and_tin_bridge_residuals_and_bijectivity(self) -> None:
        spec = parse_allmaps_annotation(FIXTURES / "allmaps-example-saigon-annotation.json")

        tps = NonDistortingBridge.from_spec(spec, method="tps")
        tps_eval = tps.evaluate_residuals()
        self.assertLess(tps_eval["in_sample_rmse_m"], 0.1)
        self.assertLess(tps_eval["roundtrip_max_px"], 1e-3)
        self.assertIsNotNone(tps_eval["loocv_rmse_m"])
        self.assertLess(tps_eval["loocv_rmse_m"], 100.0)

        # Test interior non-GCP point round-trip closure
        lon, lat = tps.pixel_to_lonlat(7500.0, 7000.0)
        rx, ry = tps.lonlat_to_pixel(lon, lat)
        self.assertAlmostEqual(rx, 7500.0, places=2)
        self.assertAlmostEqual(ry, 7000.0, places=2)

        # Local viewport scale & rotation
        vp = tps.local_viewport_transform(7500.0, 7000.0)
        self.assertGreater(vp["mean_scale_m_per_px"], 0.0)

        # TIN piecewise affine bridge
        tin = NonDistortingBridge.from_spec(spec, method="tin")
        tin_eval = tin.evaluate_residuals()
        self.assertLess(tin_eval["in_sample_rmse_m"], 0.1)
        self.assertLess(tin_eval["roundtrip_max_px"], 1e-3)


if __name__ == "__main__":
    unittest.main()
