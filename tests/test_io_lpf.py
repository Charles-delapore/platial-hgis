"""Unit tests for LPF JSON-LD bidirectional I/O and strict schema validation."""

import pathlib
import tempfile
import unittest

from platial_hgis.io_lpf import (
    LPFValidationError,
    load_lpf,
    places_to_lpf_collection,
    save_lpf,
    validate_lpf,
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

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


class TestIOLPF(unittest.TestCase):
    def test_load_real_whg_lpf_sample(self) -> None:
        places = load_lpf(FIXTURES / "whg-place-sample.json", strict_v13=False)
        self.assertEqual(len(places), 1)
        ist = places[0]
        self.assertEqual(ist.title, "İstanbul")
        self.assertEqual(ist.fclasses, ("P",))
        self.assertEqual(len(ist.geometries), 1)
        self.assertAlmostEqual(ist.primary_geometry.geometry["coordinates"][0], 28.94966, places=4)
        self.assertGreater(len(ist.names), 20)
        self.assertTrue(any("GeoNames" in e.label for e in ist.evidence))

    def test_lossless_roundtrip_competing_geometries_and_absence(self) -> None:
        ev = EvidenceRef(source_id="src-loulan", label="Stein 1907", evidence_level="verified")
        p1 = PlatialPlace(
            place_id="urn:platial:loulan",
            title="Loulan / Krorän",
            fclasses=("S", "P"),
            names=[{"toponym": "楼兰", "lang": "zh"}, {"toponym": "Krorän", "lang": "xpg"}],
            when=FuzzyInterval(-176, -150, 330, 400, label="Han-Jin Oasis", certainty="uncertain"),
            geometries=[
                CompetingGeometry(
                    hypothesis_id="h-le-site",
                    geometry={"type": "Point", "coordinates": [89.91, 40.51]},
                    weight=0.72,
                    evidence=(ev,),
                    uncertainty_radius_km=8.0,
                ),
                CompetingGeometry(
                    hypothesis_id="h-south-lop",
                    geometry={"type": "Point", "coordinates": [89.45, 39.85]},
                    weight=0.28,
                    evidence=(ev,),
                    uncertainty_radius_km=25.0,
                ),
            ],
            absence=AbsenceState.CONTESTED,
            absence_reason="Multiple candidate ruin complexes in Lop Nor basin",
            platial=PlatialAttributes(
                location={"basin": "Tarim / Lop Nor"},
                locale={"setting": "oasis entrepot"},
                affect=AffectLayer(valence=-0.35, arousal=0.65, dominant_mood="desolation_awe"),
            ),
            evidence=[ev],
            ccodes=["CN"],
            provenance="open_historical_demo",
        )
        p2 = PlatialPlace(
            place_id="urn:platial:silent-post",
            title="Unattested Desert Post",
            fclasses=("R",),
            absence=AbsenceState.UNRECORDED,
            absence_reason="Archival silence between 400 and 640 CE",
        )

        with tempfile.TemporaryDirectory() as tmp:
            out_path = pathlib.Path(tmp) / "places.lpf.jsonld"
            save_lpf([p1, p2], out_path, strict_v13=True)
            reloaded = load_lpf(out_path, strict_v13=True)

        self.assertEqual(len(reloaded), 2)
        r1, r2 = reloaded
        self.assertEqual(r1.place_id, p1.place_id)
        self.assertEqual(len(r1.geometries), 2)
        self.assertAlmostEqual(r1.geometries[0].weight, 0.72)
        self.assertEqual(r1.when.earliest_start, -176.0)
        self.assertEqual(r1.when.latest_end, 400.0)
        self.assertEqual(r1.platial.affect.dominant_mood, "desolation_awe")
        self.assertEqual(r2.absence, AbsenceState.UNRECORDED)
        self.assertEqual(len(r2.geometries), 0)

    def test_strict_v13_validation_rejects_missing_fclasses_and_unexplained_null_geom(self) -> None:
        bad_doc = {
            "type": "Feature",
            "@id": "urn:test:1",
            "properties": {"title": "No Fclass"},
            "geometry": {"type": "Point", "coordinates": [110.0, 34.0]},
        }
        with self.assertRaises(LPFValidationError):
            validate_lpf(bad_doc, strict_v13=True)

        bad_null = {
            "type": "Feature",
            "@id": "urn:test:2",
            "properties": {"title": "Silent No Reason", "fclasses": ["P"]},
            "geometry": None,
        }
        with self.assertRaises(LPFValidationError):
            validate_lpf(bad_null, strict_v13=True)

        # Valid collection check
        p = PlatialPlace(
            place_id="urn:test:ok",
            title="OK",
            fclasses=("P",),
            absence=AbsenceState.ABSENT,
        )
        validate_lpf(places_to_lpf_collection([p]), strict_v13=True)


if __name__ == "__main__":
    unittest.main()
