"""D3-P2: Cross-dynasty toponym disambiguation using temporal windows & admin hierarchy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .gazetteer import GazetteerIndex
from .primitives import EvidenceRef, FuzzyInterval, PlatialPlace


@dataclass(frozen=True)
class DisambiguationCandidate:
    """Ranked historical toponym match with confidence, uncertainty radius, and citations."""

    place: PlatialPlace
    score: float
    temporal_score: float
    hierarchy_score: float
    lexical_score: float
    uncertainty_radius_km: float
    evidence: tuple[EvidenceRef, ...]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "place_id": self.place.place_id,
            "title": self.place.title,
            "score": round(self.score, 4),
            "temporal_score": round(self.temporal_score, 4),
            "hierarchy_score": round(self.hierarchy_score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "uncertainty_radius_km": round(self.uncertainty_radius_km, 2),
            "evidence": [e.to_dict() for e in self.evidence],
            "rationale": self.rationale,
        }


def _temporal_overlap_score(place_when: FuzzyInterval | None, target: FuzzyInterval | None) -> float:
    if target is None:
        return 0.6
    if place_when is None:
        return 0.45
    # Overlap between outer envelopes
    ov_start = max(place_when.earliest_start, target.earliest_start)
    ov_end = min(place_when.latest_end, target.latest_end)
    if ov_end >= ov_start:
        ov_len = (ov_end - ov_start) + 1.0
        target_len = max(1.0, (target.latest_end - target.earliest_start) + 1.0)
        return min(1.0, 0.55 + 0.45 * min(1.0, ov_len / target_len))
    # Soft decay by gap in years
    gap = ov_start - ov_end
    return max(0.0, 0.4 * (1.0 / (1.0 + gap / 50.0)))


def _lexical_score(query: str, place: PlatialPlace) -> float:
    q = query.strip().lower()
    if not q:
        return 0.0
    titles = [place.title.lower()] + [str(n.get("toponym", "")).lower() for n in place.names]
    if any(t == q for t in titles):
        return 1.0
    if any(t.startswith(q) or q.startswith(t) for t in titles if t):
        return 0.85
    if any(q in t for t in titles):
        return 0.7
    return 0.35


def _hierarchy_score(
    place: PlatialPlace,
    *,
    expected_dynasty: str | None = None,
    expected_admin_type: str | None = None,
    expected_lev_rank: int | None = None,
    parent_hint: str | None = None,
) -> float:
    loc = place.platial.location
    checks = 0
    hits = 0.0
    if expected_dynasty:
        checks += 1
        if str(loc.get("dynasty", "")).lower() == expected_dynasty.lower():
            hits += 1.0
    if expected_admin_type:
        checks += 1
        actual_type = str(loc.get("type_ch") or place.platial.locale.get("admin_type") or "")
        if expected_admin_type.lower() in actual_type.lower():
            hits += 1.0
    if expected_lev_rank is not None:
        checks += 1
        actual_rank = loc.get("lev_rank")
        try:
            if actual_rank is not None and int(actual_rank) == int(expected_lev_rank):
                hits += 1.0
            elif actual_rank is not None and abs(int(actual_rank) - int(expected_lev_rank)) == 1:
                hits += 0.5
        except (TypeError, ValueError):
            pass
    if parent_hint:
        checks += 1
        haystack = " ".join(
            str(v)
            for v in (
                loc.get("parent_id", ""),
                loc.get("parent_name", ""),
                loc.get("pres_loc", ""),
                place.title,
            )
        ).lower()
        if parent_hint.lower() in haystack:
            hits += 1.0
    if checks == 0:
        return 0.7
    return hits / checks


class CrossDynastyDisambiguator:
    """Disambiguates historical toponyms across dynasties with temporal & hierarchy priors."""

    def __init__(self, index: GazetteerIndex) -> None:
        self.index = index

    def disambiguate(
        self,
        toponym: str,
        *,
        when: FuzzyInterval | None = None,
        dynasty: str | None = None,
        admin_type: str | None = None,
        lev_rank: int | None = None,
        parent_hint: str | None = None,
        top_k: int = 5,
    ) -> list[DisambiguationCandidate]:
        """Return top-k ranked candidates with uncertainty radius and provenance citations."""
        # Retrieve broad candidate pool without hard-dropping close dynasties so scoring ranks them
        pool = self.index.search(toponym, limit=max(30, top_k * 5))
        scored: list[DisambiguationCandidate] = []

        for place in pool:
            lex = _lexical_score(toponym, place)
            temp = _temporal_overlap_score(place.when, when)
            hier = _hierarchy_score(
                place,
                expected_dynasty=dynasty,
                expected_admin_type=admin_type,
                expected_lev_rank=lev_rank,
                parent_hint=parent_hint,
            )
            total = 0.35 * lex + 0.40 * temp + 0.25 * hier

            base_radius = (
                place.primary_geometry.uncertainty_radius_km
                if place.primary_geometry is not None and place.primary_geometry.uncertainty_radius_km > 0
                else 20.0
            )
            # Scale uncertainty radius inversely with disambiguation confidence
            adj_radius = round(base_radius * (1.0 + (1.0 - total)), 2)

            ev_list = list(place.evidence)
            if place.primary_geometry and place.primary_geometry.evidence:
                for e in place.primary_geometry.evidence:
                    if e not in ev_list:
                        ev_list.append(e)

            rationale = (
                f"lex={lex:.2f}, temporal={temp:.2f}, hierarchy={hier:.2f}; "
                f"dynasty={place.platial.location.get('dynasty', 'n/a')}, "
                f"type={place.platial.location.get('type_ch', 'n/a')}"
            )
            scored.append(
                DisambiguationCandidate(
                    place=place,
                    score=total,
                    temporal_score=temp,
                    hierarchy_score=hier,
                    lexical_score=lex,
                    uncertainty_radius_km=adj_radius,
                    evidence=tuple(ev_list),
                    rationale=rationale,
                )
            )

        scored.sort(key=lambda c: (-c.score, c.uncertainty_radius_km, c.place.place_id))
        return scored[:top_k]
