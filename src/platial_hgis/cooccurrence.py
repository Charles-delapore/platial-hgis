"""D3-P4: Uncertain-window spatiotemporal co-occurrence trajectory network miner."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import math
from typing import Any

from .georef import haversine_m
from .primitives import EvidenceRef, FuzzyInterval
from .reasoning import allen_probabilities


@dataclass(frozen=True)
class TrajectoryEvent:
    """An attested historical actor/event occurrence with fuzzy time and spatial uncertainty."""

    event_id: str
    actor_id: str
    actor_name: str
    place_id: str
    place_name: str
    lon: float
    lat: float
    when: FuzzyInterval
    uncertainty_radius_km: float = 10.0
    valence: float = 0.0
    dominant_mood: str = "neutral"
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CooccurrenceEdge:
    """Weighted spatiotemporal co-occurrence edge between two distinct actors."""

    actor_a: str
    actor_b: str
    place_ids: tuple[str, ...]
    place_names: tuple[str, ...]
    temporal_prob: float
    spatial_prob: float
    joint_weight: float
    distance_km: float
    evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_a": self.actor_a,
            "actor_b": self.actor_b,
            "place_ids": list(self.place_ids),
            "place_names": list(self.place_names),
            "temporal_prob": round(self.temporal_prob, 4),
            "spatial_prob": round(self.spatial_prob, 4),
            "joint_weight": round(self.joint_weight, 4),
            "distance_km": round(self.distance_km, 2),
            "evidence_ids": list(self.evidence_ids),
        }


def _spatial_cooccurrence_prob(
    dist_km: float,
    radius_a_km: float,
    radius_b_km: float,
    max_radius_km: float,
) -> float:
    """Smooth spatial proximity probability accounting for both actors' uncertainty radii."""
    effective_sigma = max(1.0, max_radius_km + 0.5 * (radius_a_km + radius_b_km))
    if dist_km <= 0.25 * effective_sigma:
        return 1.0
    return float(math.exp(-0.5 * ((dist_km / effective_sigma) ** 2)))


def mine_cooccurrence_network(
    events: list[TrajectoryEvent],
    *,
    spatial_radius_km: float = 35.0,
    min_joint_prob: float = 0.15,
    n_samples: int = 3000,
    seed: int = 42,
) -> dict[str, Any]:
    """Mine spatiotemporal co-occurrence edges between actors across uncertain time & space.

    Returns a pure-Python graph dictionary (`nodes`, `edges`, `summary`) with weighted degree
    centrality and actor trajectories (no external `networkx` dependency required).
    """
    pair_records: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    actor_names: dict[str, str] = {}
    actor_events: dict[str, list[TrajectoryEvent]] = defaultdict(list)

    for ev in events:
        actor_names[ev.actor_id] = ev.actor_name
        actor_events[ev.actor_id].append(ev)

    n = len(events)
    for i in range(n):
        ei = events[i]
        for j in range(i + 1, n):
            ej = events[j]
            if ei.actor_id == ej.actor_id:
                continue
            # Fast outer-envelope reject before Monte Carlo Allen
            if not ei.when.overlaps_window(ej.when.earliest_start, ej.when.latest_end):
                continue
            dist_km = haversine_m(ei.lon, ei.lat, ej.lon, ej.lat) / 1000.0
            s_prob = _spatial_cooccurrence_prob(
                dist_km, ei.uncertainty_radius_km, ej.uncertainty_radius_km, spatial_radius_km
            )
            if s_prob < min_joint_prob:
                continue

            t_prob = allen_probabilities(ei.when, ej.when, n_samples=n_samples, seed=seed + i + j).contemporary
            joint = t_prob * s_prob
            if joint < min_joint_prob:
                continue

            pair = tuple(sorted((ei.actor_id, ej.actor_id)))
            ev_ids = tuple(
                dict.fromkeys(
                    [e.source_id for e in ei.evidence] + [e.source_id for e in ej.evidence]
                )
            )
            pair_records[pair].append(
                {
                    "place_ids": (ei.place_id, ej.place_id),
                    "place_names": (ei.place_name, ej.place_name),
                    "temporal_prob": t_prob,
                    "spatial_prob": s_prob,
                    "joint": joint,
                    "distance_km": dist_km,
                    "evidence_ids": ev_ids,
                }
            )

    edges: list[CooccurrenceEdge] = []
    weighted_degree: dict[str, float] = defaultdict(float)
    degree: dict[str, int] = defaultdict(int)

    for (a, b), recs in sorted(pair_records.items()):
        # Aggregate independent meeting opportunities: 1 - prod(1 - p_k)
        not_meet = 1.0
        for r in recs:
            not_meet *= 1.0 - r["joint"]
        agg_joint = 1.0 - not_meet
        best = max(recs, key=lambda r: r["joint"])
        all_pids = tuple(dict.fromkeys(pid for r in recs for pid in r["place_ids"]))
        all_pnames = tuple(dict.fromkeys(pn for r in recs for pn in r["place_names"]))
        all_eids = tuple(dict.fromkeys(eid for r in recs for eid in r["evidence_ids"]))

        edge = CooccurrenceEdge(
            actor_a=a,
            actor_b=b,
            place_ids=all_pids,
            place_names=all_pnames,
            temporal_prob=best["temporal_prob"],
            spatial_prob=best["spatial_prob"],
            joint_weight=agg_joint,
            distance_km=best["distance_km"],
            evidence_ids=all_eids,
        )
        edges.append(edge)
        weighted_degree[a] += agg_joint
        weighted_degree[b] += agg_joint
        degree[a] += 1
        degree[b] += 1

    nodes = [
        {
            "actor_id": aid,
            "actor_name": actor_names[aid],
            "event_count": len(actor_events[aid]),
            "degree": degree[aid],
            "weighted_degree": round(weighted_degree[aid], 4),
            "mean_valence": round(
                sum(e.valence for e in actor_events[aid]) / max(1, len(actor_events[aid])), 4
            ),
        }
        for aid in sorted(actor_names)
    ]

    return {
        "nodes": nodes,
        "edges": [e.to_dict() for e in edges],
        "summary": {
            "actor_count": len(nodes),
            "edge_count": len(edges),
            "event_count": len(events),
            "spatial_radius_km": spatial_radius_km,
            "min_joint_prob": min_joint_prob,
        },
    }
