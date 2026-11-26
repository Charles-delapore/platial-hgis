"""Unit tests for lossless GeoParquet and JSON I/O."""

import json
import pathlib
import tempfile
import unittest

import pyarrow.parquet as pq

from platial_hgis.io_geoparquet import (
    load_geoparquet,
    load_json,
    save_geoparquet,
    save_json,
)
from platial_hgis.primitives import (
    AbsenceState,
    AffectLayer,
    CompetingGeometry,
    EvidenceRef,
    FuzzyInterval,
    PlatialAttributes,
    PlatialPlace,
)


class TestIOGeoParquet(unittest.TestCase):
    def _sample_places(self) -> list[PlatialPlace]:
        ev = EvidenceRef(source_id="ev-1", label="Old Book of Tang", evidence_level="verified")
        return [
            PlatialPlace(
                place_id="urn:platial:luoyang",
                title="Luoyang",
                fclasses=("A", "P"),
                names=[{"toponym": "洛阳", "lang": "zh"}],
                when=FuzzyInterval(618, 618, 907, 907, label="Tang"),
                geometries=[
                    CompetingGeometry(
                        hypothesis_id="h1",
                        geometry={"type": "Point", "coordinates": [112.454, 34.619]},
                        weight=0.85,
                        evidence=(ev,),
                        uncertainty_radius_km=3.5,
                    ),
                    CompetingGeometry(
                        hypothesis_id="h2",
                        geometry={"type": "Point", "coordinates": [112.55, 34.68]},
                        weight=0.15,
                        evidence=(ev,),
                        uncertainty_radius_km=8.0,
                    ),
                ],
                platial=PlatialAttributes(
                    location={"modern": "Luoyang, Henan"},
                    locale={"setting": "eastern capital"},
                    affect=AffectLayer(valence=0.5, arousal=0.6, dominant_mood="nostalgic_splendor"),
                ),
                evidence=[ev],
                provenance="open_historical_demo",
            ),
            PlatialPlace(
                place_id="urn:platial:lost-ferry",
                title="Unrecorded Canal Ferry",
                fclasses=("H",),
                absence=AbsenceState.UNRECORDED,
                absence_reason="Not recorded in surviving Song canal registers",
            ),
        ]

    def test_geoparquet_roundtrip_and_geo_metadata(self) -> None:
        places = self._sample_places()
        with tempfile.TemporaryDirectory() as tmp:
            pq_path = pathlib.Path(tmp) / "places.geoparquet"
            save_geoparquet(places, pq_path)

            # Verify GeoParquet v1.0.0 metadata exists
            meta = pq.read_schema(pq_path).metadata
            self.assertIn(b"geo", meta)
            geo = json.loads(meta[b"geo"].decode("utf-8"))
            self.assertEqual(geo["primary_column"], "geometry")
            self.assertEqual(geo["columns"]["geometry"]["encoding"], "WKB")
            self.assertIn("Point", geo["columns"]["geometry"]["geometry_types"])

            reloaded = load_geoparquet(pq_path)
            self.assertEqual(len(reloaded), 2)
            self.assertEqual(reloaded[0].to_dict(), places[0].to_dict())
            self.assertEqual(reloaded[1].to_dict(), places[1].to_dict())

    def test_json_roundtrip(self) -> None:
        places = self._sample_places()
        with tempfile.TemporaryDirectory() as tmp:
            j_path = pathlib.Path(tmp) / "places.json"
            save_json(places, j_path)
            reloaded = load_json(j_path)
            self.assertEqual([p.to_dict() for p in reloaded], [p.to_dict() for p in places])


if __name__ == "__main__":
    unittest.main()
