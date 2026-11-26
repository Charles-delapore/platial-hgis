"""Unit tests for D3-P2 cross-dynasty toponym disambiguator."""

import unittest

from platial_hgis.disambiguate import CrossDynastyDisambiguator
from platial_hgis.gazetteer import GazetteerIndex
from platial_hgis.primitives import (
    CompetingGeometry,
    EvidenceRef,
    FuzzyInterval,
    PlatialAttributes,
    PlatialPlace,
)


class TestCrossDynastyDisambiguator(unittest.TestCase):
    def test_disambiguate_same_name_across_dynasties_and_levels(self) -> None:
        ev_tang = EvidenceRef("src-tang", "Tang Administrative Gazetteer", evidence_level="verified")
        ev_song = EvidenceRef("src-song", "Song Administrative Gazetteer", evidence_level="verified")

        p1 = PlatialPlace(
            place_id="demo:yangzhou-tang",
            title="扬州",
            fclasses=("A",),
            names=[{"toponym": "广陵郡", "lang": "zh"}, {"toponym": "Yangzhou", "lang": "en"}],
            when=FuzzyInterval.from_crisp(618, 907, label="Tang"),
            geometries=[
                CompetingGeometry("h1", {"type": "Point", "coordinates": [119.41, 32.39]}, 1.0, (ev_tang,), 12.0)
            ],
            platial=PlatialAttributes(location={"dynasty": "Tang", "type_ch": "州", "lev_rank": 3, "parent_name": "淮南道"}),
            evidence=[ev_tang],
        )
        p2 = PlatialPlace(
            place_id="demo:yangzhou-song",
            title="扬州",
            fclasses=("A",),
            names=[{"toponym": "扬州", "lang": "zh"}],
            when=FuzzyInterval.from_crisp(960, 1279, label="Song"),
            geometries=[
                CompetingGeometry("h1", {"type": "Point", "coordinates": [119.42, 32.40]}, 1.0, (ev_song,), 10.0)
            ],
            platial=PlatialAttributes(location={"dynasty": "Song", "type_ch": "州", "lev_rank": 3, "parent_name": "淮南东路"}),
            evidence=[ev_song],
        )

        with GazetteerIndex(":memory:") as idx:
            idx.add_places([p1, p2])
            dis = CrossDynastyDisambiguator(idx)

            res_tang = dis.disambiguate(
                "扬州",
                when=FuzzyInterval.from_crisp(740, 755),
                dynasty="Tang",
                parent_hint="淮南道",
            )
            self.assertEqual(res_tang[0].place.place_id, "demo:yangzhou-tang")
            self.assertGreater(res_tang[0].score, res_tang[1].score)
            self.assertGreater(res_tang[0].uncertainty_radius_km, 0.0)
            self.assertEqual(res_tang[0].evidence[0].source_id, "src-tang")

            res_song = dis.disambiguate(
                "扬州",
                when=FuzzyInterval.from_crisp(1090, 1100),
                dynasty="Song",
                parent_hint="淮南东路",
            )
            self.assertEqual(res_song[0].place.place_id, "demo:yangzhou-song")


if __name__ == "__main__":
    unittest.main()
