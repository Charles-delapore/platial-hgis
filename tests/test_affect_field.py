"""Unit tests for D3-P4 affective spatial field modeling."""

import unittest

from platial_hgis.affect_field import AffectiveField
from platial_hgis.primitives import (
    AffectLayer,
    CompetingGeometry,
    PlatialAttributes,
    PlatialPlace,
)


class TestAffectiveField(unittest.TestCase):
    def test_spatial_polarity_and_contested_dispersion(self) -> None:
        p_joy = PlatialPlace(
            place_id="p-hangzhou",
            title="Hangzhou",
            fclasses=("P",),
            geometries=[CompetingGeometry("h1", {"type": "Point", "coordinates": [120.15, 30.27]}, 1.0)],
            platial=PlatialAttributes(
                affect=AffectLayer(valence=0.85, arousal=0.65, dominant_mood="lyrical_serenity")
            ),
        )
        p_exile = PlatialPlace(
            place_id="p-danzhou",
            title="Danzhou",
            fclasses=("P",),
            geometries=[CompetingGeometry("h1", {"type": "Point", "coordinates": [109.58, 19.52]}, 1.0)],
            platial=PlatialAttributes(
                affect=AffectLayer(valence=-0.75, arousal=0.70, dominant_mood="exile_resilience")
            ),
        )
        field = AffectiveField.from_places([p_joy, p_exile], bandwidth_km=300.0)
        near_hz = field.evaluate(120.15, 30.27)
        near_dz = field.evaluate(109.58, 19.52)
        self.assertGreater(near_hz["valence"], 0.7)
        self.assertEqual(near_hz["dominant_mood"], "lyrical_serenity")
        self.assertLess(near_dz["valence"], -0.6)
        self.assertEqual(near_dz["dominant_mood"], "exile_resilience")

        grid = field.sample_grid(nx=4, ny=3)
        self.assertEqual(len(grid["features"]), 12)


if __name__ == "__main__":
    unittest.main()
