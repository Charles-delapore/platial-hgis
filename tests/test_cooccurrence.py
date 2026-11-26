"""Unit tests for D3-P4 spatiotemporal co-occurrence trajectory network miner."""

import unittest

from platial_hgis.cooccurrence import TrajectoryEvent, mine_cooccurrence_network
from platial_hgis.primitives import EvidenceRef, FuzzyInterval


class TestCooccurrenceNetwork(unittest.TestCase):
    def test_tang_poets_luoyang_cooccurrence_detected_and_song_separated(self) -> None:
        ev = EvidenceRef("open-demo-bio", "Open historical literary chronology (demo)", evidence_level="verified")
        events = [
            TrajectoryEvent(
                event_id="e1",
                actor_id="libai",
                actor_name="Li Bai",
                place_id="luoyang",
                place_name="Luoyang",
                lon=112.454,
                lat=34.619,
                when=FuzzyInterval(744, 744, 745, 745),
                valence=0.6,
                evidence=(ev,),
            ),
            TrajectoryEvent(
                event_id="e2",
                actor_id="dufu",
                actor_name="Du Fu",
                place_id="luoyang",
                place_name="Luoyang",
                lon=112.460,
                lat=34.622,
                when=FuzzyInterval(744, 744, 745, 746),
                valence=0.4,
                evidence=(ev,),
            ),
            TrajectoryEvent(
                event_id="e3",
                actor_id="sushi",
                actor_name="Su Shi",
                place_id="luoyang",
                place_name="Luoyang",
                lon=112.454,
                lat=34.619,
                when=FuzzyInterval(1060, 1061, 1062, 1063),
                valence=0.5,
                evidence=(ev,),
            ),
        ]

        net = mine_cooccurrence_network(events, spatial_radius_km=30.0, min_joint_prob=0.2)
        self.assertEqual(net["summary"]["actor_count"], 3)
        self.assertEqual(net["summary"]["edge_count"], 1)
        edge = net["edges"][0]
        self.assertEqual({edge["actor_a"], edge["actor_b"]}, {"libai", "dufu"})
        self.assertGreater(edge["joint_weight"], 0.9)


if __name__ == "__main__":
    unittest.main()
