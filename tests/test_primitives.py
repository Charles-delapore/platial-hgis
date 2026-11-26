"""Unit tests for D3-P1 fuzzy spatiotemporal primitives and platial data model."""

import json
import pathlib
import unittest

from platial_hgis.primitives import (
    AbsenceState,
    AffectLayer,
    CompetingGeometry,
    EvidenceRef,
    FuzzyInterval,
    PlatialAttributes,
    PlatialPlace,
    normalize_hypothesis_weights,
)

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


class TestPrimitives(unittest.TestCase):
    def test_fuzzy_interval_validation_and_crm_export(self) -> None:
        iv = FuzzyInterval(742, 745, 756, 758, label="Tianbao Era", certainty="uncertain")
        self.assertEqual(iv.start_uncertainty, 3.0)
        self.assertEqual(iv.end_uncertainty, 2.0)
        self.assertAlmostEqual(iv.midpoint, 750.25)
        self.assertTrue(iv.overlaps_window(750, 755))
        self.assertFalse(iv.overlaps_window(800, 820))

        crm = iv.to_cidoc_crm()
        self.assertEqual(crm["type"], "crm:E52_Time-Span")
        self.assertEqual(crm["crm:P82a_begin_of_the_begin"], 742)
        self.assertEqual(crm["crm:P82b_end_of_the_end"], 758)

        with self.assertRaises(ValueError):
            FuzzyInterval(750, 740, 760, 770)
        with self.assertRaises(ValueError):
            FuzzyInterval(750, 760, 740, 745)

    def test_periodo_real_samples_parsing(self) -> None:
        dark_age = json.loads((FIXTURES / "periodo-sample-darkage.json").read_text(encoding="utf-8"))
        iv_da = FuzzyInterval.from_periodo(dark_age)
        self.assertEqual(iv_da.earliest_start, -1099.0)
        self.assertEqual(iv_da.latest_end, -899.0)
        self.assertEqual(iv_da.periodo_id, "p05krdxmkzt")

        cr = json.loads(
            (FIXTURES / "periodo-sample-cultural-revolution.json").read_text(encoding="utf-8")
        )
        iv_cr = FuzzyInterval.from_periodo(cr)
        self.assertEqual(iv_cr.earliest_start, 1966.0)
        self.assertEqual(iv_cr.earliest_end, 1969.0)
        self.assertEqual(iv_cr.latest_end, 1976.0)
        self.assertEqual(iv_cr.certainty, "uncertain")

    def test_competing_geometries_and_normalization(self) -> None:
        ev1 = EvidenceRef(source_id="src-1", label="Hanshu Xiyuzhuan", evidence_level="verified")
        ev2 = EvidenceRef(source_id="src-2", label="Modern Survey", evidence_level="indirect")
        g1 = CompetingGeometry(
            hypothesis_id="h-north",
            geometry={"type": "Point", "coordinates": [89.91, 40.51]},
            weight=0.6,
            evidence=(ev1,),
            uncertainty_radius_km=12.5,
        )
        g2 = CompetingGeometry(
            hypothesis_id="h-south",
            geometry={"type": "Point", "coordinates": [89.55, 40.15]},
            weight=0.2,
            evidence=(ev2,),
            uncertainty_radius_km=25.0,
        )
        norm = normalize_hypothesis_weights([g1, g2])
        self.assertAlmostEqual(sum(g.weight for g in norm), 1.0, places=5)
        self.assertAlmostEqual(norm[0].weight, 0.75, places=5)

    def test_archival_silence_three_states(self) -> None:
        # Must declare AbsenceState when geometries are empty
        with self.assertRaises(ValueError):
            PlatialPlace(place_id="p-empty", title="Unknown Site")

        p_unrec = PlatialPlace(
            place_id="p-silence",
            title="Lost Relay Station",
            fclasses=("S",),
            absence=AbsenceState.UNRECORDED,
            absence_reason="No surviving Tang gazetteer entry for this desert post",
        )
        self.assertEqual(p_unrec.absence, AbsenceState.UNRECORDED)
        self.assertIsNone(p_unrec.primary_geometry)

        # Round-trip dict serialization
        rt = PlatialPlace.from_dict(p_unrec.to_dict())
        self.assertEqual(rt.absence, AbsenceState.UNRECORDED)
        self.assertEqual(rt.absence_reason, p_unrec.absence_reason)

    def test_platial_three_layers_and_fclass_validation(self) -> None:
        pl = PlatialPlace(
            place_id="p-changan",
            title="Chang'an",
            fclasses=("A", "P"),
            when=FuzzyInterval.from_crisp(618, 907, label="Tang Dynasty"),
            geometries=[
                CompetingGeometry(
                    hypothesis_id="h-main",
                    geometry={"type": "Point", "coordinates": [108.9402, 34.2658]},
                    weight=1.0,
                )
            ],
            platial=PlatialAttributes(
                location={"modern_admin": "Xi'an, Shaanxi"},
                locale={"setting": "imperial capital", "aat": "capital city"},
                affect=AffectLayer(
                    valence=0.65,
                    arousal=0.72,
                    dominant_mood="grandeur_and_longing",
                    tags=("cosmopolitan", "imperial", "departure"),
                ),
            ),
        )
        rt = PlatialPlace.from_dict(pl.to_dict())
        self.assertEqual(rt.platial.affect.dominant_mood, "grandeur_and_longing")
        self.assertEqual(rt.primary_geometry.hypothesis_id, "h-main")

        with self.assertRaises(ValueError):
            PlatialPlace(
                place_id="p-bad",
                title="Bad",
                fclasses=("Z",),
                absence=AbsenceState.ABSENT,
            )


if __name__ == "__main__":
    unittest.main()
