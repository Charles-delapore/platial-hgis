"""D3-P4: Probabilistic Allen Interval Algebra over four-tuple FuzzyIntervals."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .primitives import FuzzyInterval


@dataclass(frozen=True)
class AllenProbabilities:
    """Probabilistic distribution over core Allen temporal relations between intervals A and B."""

    before: float        # A ends strictly before B starts (a_end < b_start)
    after: float         # A starts strictly after B ends (a_start > b_end)
    meets: float         # |a_end - b_start| <= tol or |b_end - a_start| <= tol
    overlaps: float      # Partial overlap (neither contains the other)
    during: float        # A is contained within B (b_start <= a_start and a_end <= b_end, not equal)
    contains: float      # A contains B (a_start <= b_start and b_end <= a_end, not equal)
    equals: float        # Both start and end match within tol
    contemporary: float  # Probability that A and B share at least one overlapping moment

    def to_dict(self) -> dict[str, float]:
        return {
            "before": round(self.before, 6),
            "after": round(self.after, 6),
            "meets": round(self.meets, 6),
            "overlaps": round(self.overlaps, 6),
            "during": round(self.during, 6),
            "contains": round(self.contains, 6),
            "equals": round(self.equals, 6),
            "contemporary": round(self.contemporary, 6),
        }


def _sample_interval(
    iv: FuzzyInterval,
    n_samples: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample valid (start, end) realizations conditioned on start <= end."""
    # Oversample and rejection-filter to enforce start <= end cleanly
    starts = np.empty(0, dtype=np.float64)
    ends = np.empty(0, dtype=np.float64)
    batch = max(n_samples * 2, 1024)

    for _ in range(12):
        s = (
            np.full(batch, iv.earliest_start, dtype=np.float64)
            if iv.earliest_start == iv.latest_start
            else rng.uniform(iv.earliest_start, iv.latest_start, size=batch)
        )
        e = (
            np.full(batch, iv.earliest_end, dtype=np.float64)
            if iv.earliest_end == iv.latest_end
            else rng.uniform(iv.earliest_end, iv.latest_end, size=batch)
        )
        valid = s <= e
        if np.any(valid):
            starts = np.concatenate([starts, s[valid]])
            ends = np.concatenate([ends, e[valid]])
        if len(starts) >= n_samples:
            break

    if len(starts) < n_samples:
        # Degenerate boundary fallback (e.g. earliest_start == latest_end)
        s_val = np.full(n_samples, iv.earliest_start, dtype=np.float64)
        e_val = np.full(n_samples, max(iv.earliest_start, iv.latest_end), dtype=np.float64)
        return s_val, e_val

    return starts[:n_samples], ends[:n_samples]


def allen_probabilities(
    a: FuzzyInterval,
    b: FuzzyInterval,
    *,
    n_samples: int = 8000,
    seed: int = 42,
    tol: float = 1e-6,
) -> AllenProbabilities:
    """Compute probabilistic Allen interval relations between fuzzy intervals A and B.

    The 7 mutually exclusive relations (before, after, meets, overlaps, during,
    contains, equals) sum to 1.0, and `contemporary = 1 - before - after`.
    """
    rng = np.random.default_rng(seed)
    as_, ae = _sample_interval(a, n_samples, rng)
    bs, be = _sample_interval(b, n_samples, rng)

    before = (ae < bs - tol)
    after = (as_ > be + tol)
    equals = (np.abs(as_ - bs) <= tol) & (np.abs(ae - be) <= tol)
    meets = (~before) & (~after) & (~equals) & (
        (np.abs(ae - bs) <= tol) | (np.abs(be - as_) <= tol)
    )
    during = (~before) & (~after) & (~equals) & (~meets) & (
        (bs <= as_ + tol) & (ae <= be + tol)
    )
    contains = (~before) & (~after) & (~equals) & (~meets) & (~during) & (
        (as_ <= bs + tol) & (be <= ae + tol)
    )
    overlaps = (~before) & (~after) & (~equals) & (~meets) & (~during) & (~contains)

    p_before = float(np.mean(before))
    p_after = float(np.mean(after))
    p_meets = float(np.mean(meets))
    p_overlaps = float(np.mean(overlaps))
    p_during = float(np.mean(during))
    p_contains = float(np.mean(contains))
    p_equals = float(np.mean(equals))
    p_contemp = float(max(0.0, min(1.0, 1.0 - p_before - p_after)))

    return AllenProbabilities(
        before=p_before,
        after=p_after,
        meets=p_meets,
        overlaps=p_overlaps,
        during=p_during,
        contains=p_contains,
        equals=p_equals,
        contemporary=p_contemp,
    )
