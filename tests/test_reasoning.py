"""Unit tests for D3-P4 probabilistic Allen temporal reasoning."""

import unittest

from platial_hgis.primitives import FuzzyInterval
from platial_hgis.reasoning import allen_probabilities


class TestAllenReasoning(unittest.TestCase):
    def test_crisp_before_during_overlaps(self) -> None:
        a = FuzzyInterval.from_crisp(701, 740)
        b = FuzzyInterval.from_crisp(750, 770)
        p_ab = allen_probabilities(a, b, n_samples=2000)
        self.assertAlmostEqual(p_ab.before, 1.0, places=4)
        self.assertAlmostEqual(p_ab.contemporary, 0.0, places=4)

        # During
        c = FuzzyInterval.from_crisp(744, 745)
        d = FuzzyInterval.from_crisp(742, 755)
        p_cd = allen_probabilities(c, d, n_samples=2000)
        self.assertAlmostEqual(p_cd.during, 1.0, places=4)
        self.assertAlmostEqual(p_cd.contemporary, 1.0, places=4)

        # Partial overlap
        e = FuzzyInterval.from_crisp(740, 755)
        f = FuzzyInterval.from_crisp(750, 765)
        p_ef = allen_probabilities(e, f, n_samples=2000)
        self.assertAlmostEqual(p_ef.overlaps, 1.0, places=4)

    def test_fuzzy_uncertain_overlap_sums_to_one(self) -> None:
        # Overlapping uncertain boundaries
        a = FuzzyInterval(740, 748, 750, 758)
        b = FuzzyInterval(752, 760, 762, 770)
        res = allen_probabilities(a, b, n_samples=10000, seed=123)
        partition_sum = (
            res.before + res.after + res.meets + res.overlaps + res.during + res.contains + res.equals
        )
        self.assertAlmostEqual(partition_sum, 1.0, places=5)
        self.assertGreater(res.before, 0.2)
        self.assertGreater(res.contemporary, 0.05)
        self.assertLess(res.contemporary, 0.95)


if __name__ == "__main__":
    unittest.main()
