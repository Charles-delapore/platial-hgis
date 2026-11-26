"""Unit tests for D3-P3 SVG region annotations and WGS84 projection."""

import pathlib
import unittest

from platial_hgis.annotations import (
    SVGMapAnnotation,
    build_svg_polygon,
    parse_svg_polygon_points,
)
from platial_hgis.georef import NonDistortingBridge, parse_allmaps_annotation
from platial_hgis.primitives import EvidenceRef

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


class TestSVGAnnotations(unittest.TestCase):
    def test_parse_real_allmaps_svg_mask_and_project_to_wgs84(self) -> None:
        spec = parse_allmaps_annotation(FIXTURES / "allmaps-example-saigon-annotation.json")
        self.assertIsNotNone(spec.svg_mask)
        pts = parse_svg_polygon_points(spec.svg_mask or "")
        self.assertGreaterEqual(len(pts), 4)

        ev = EvidenceRef(
            source_id="bnf-saigon",
            label="BnF GE C-2682 via Allmaps (CC0)",
            uri="https://annotations.allmaps.org/maps/1bfb1eb4198e7240",
            evidence_level="verified",
        )
        ann = SVGMapAnnotation(
            annotation_id="urn:anno:saigon-mask",
            canvas_id=spec.iiif_service_id or "canvas:1",
            label="Saigon Historical Map Mask",
            svg_selector=spec.svg_mask or "",
            evidence=(ev,),
            place_id="urn:platial:saigon",
        )
        bridge = NonDistortingBridge.from_spec(spec, method="tps")
        feat = ann.to_wgs84_geojson_feature(bridge)
        self.assertEqual(feat["geometry"]["type"], "Polygon")
        ring = feat["geometry"]["coordinates"][0]
        self.assertEqual(ring[0], ring[-1])
        # Coordinates should fall near Saigon (~106.7E, 10.78N)
        lons = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        self.assertTrue(106.5 < sum(lons) / len(lons) < 107.0)
        self.assertTrue(10.5 < sum(lats) / len(lats) < 11.0)

        w3c = ann.to_w3c_web_annotation()
        self.assertEqual(w3c["target"]["selector"]["type"], "SvgSelector")

    def test_rejects_annotation_without_evidence_and_builds_svg(self) -> None:
        svg = build_svg_polygon([(100, 100), (200, 100), (200, 200), (100, 200)], width=1000, height=1000)
        with self.assertRaises(ValueError):
            SVGMapAnnotation(
                annotation_id="urn:anno:no-ev",
                canvas_id="canvas:1",
                label="Uncited",
                svg_selector=svg,
                evidence=(),
            )


if __name__ == "__main__":
    unittest.main()
