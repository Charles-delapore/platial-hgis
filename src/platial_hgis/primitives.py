"""D3-P1: Fuzzy spatiotemporal primitives, archival silence, and 3-layer platial data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any


VALID_FCLASSES = frozenset({"A", "H", "L", "P", "R", "S", "T"})
VALID_EVIDENCE_LEVELS = frozenset({"verified", "indirect", "speculative"})


class AbsenceState(str, Enum):
    """Three-state archival silence semantics."""

    ABSENT = "absent"          # Positively attested as not existing in the period
    UNRECORDED = "unrecorded"  # Archival silence / no surviving attestation
    CONTESTED = "contested"    # Conflicting scholarly or primary-source claims


@dataclass(frozen=True)
class EvidenceRef:
    """Citation reference binding a claim to a historical or scholarly source."""

    source_id: str
    label: str
    uri: str | None = None
    evidence_level: str = "verified"
    locator: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("EvidenceRef.source_id must be non-empty")
        if not self.label.strip():
            raise ValueError("EvidenceRef.label must be non-empty")
        if self.evidence_level not in VALID_EVIDENCE_LEVELS:
            raise ValueError(
                f"Invalid evidence_level {self.evidence_level!r}; "
                f"expected one of {sorted(VALID_EVIDENCE_LEVELS)}"
            )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "source_id": self.source_id,
            "label": self.label,
            "evidence_level": self.evidence_level,
        }
        if self.uri is not None:
            out["uri"] = self.uri
        if self.locator is not None:
            out["locator"] = self.locator
        if self.notes is not None:
            out["notes"] = self.notes
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRef":
        return cls(
            source_id=str(data["source_id"]),
            label=str(data["label"]),
            uri=data.get("uri"),
            evidence_level=str(data.get("evidence_level", "verified")),
            locator=data.get("locator"),
            notes=data.get("notes"),
        )


def _parse_iso_year(value: str | int | float) -> float:
    """Parse astronomical year (PeriodO xsd:gYear: '0000' = 1 BCE, '-1099' = 1100 BCE)."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        raise ValueError("Empty year string")
    # Handle YYYY-MM-DD or -YYYY-MM-DD
    sign = -1.0 if s.startswith("-") else 1.0
    body = s[1:] if s[0] in "+-" else s
    parts = body.split("-")
    year = int(parts[0])
    frac = 0.0
    if len(parts) >= 2 and parts[1].isdigit():
        month = max(1, min(12, int(parts[1])))
        day = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
        frac = ((month - 1) + (day - 1) / 31.0) / 12.0
    return sign * year + (frac if sign > 0 else -frac)


@dataclass(frozen=True)
class FuzzyInterval:
    """Four-tuple fuzzy historical time interval with PeriodO & CIDOC-CRM alignment.

    Astronomical year convention (matching PeriodO xsd:gYear):
      - 1 CE = 1.0, 1 BCE = 0.0, 2 BCE = -1.0, etc.
    Invariant:
      earliest_start <= latest_start
      earliest_end <= latest_end
      earliest_start <= latest_end
    """

    earliest_start: float
    latest_start: float
    earliest_end: float
    latest_end: float
    label: str | None = None
    periodo_id: str | None = None
    certainty: str = "certain"

    def __post_init__(self) -> None:
        if any(
            math.isnan(v) or math.isinf(v)
            for v in (
                self.earliest_start,
                self.latest_start,
                self.earliest_end,
                self.latest_end,
            )
        ):
            raise ValueError("FuzzyInterval bounds must be finite numbers")
        if self.earliest_start > self.latest_start:
            raise ValueError(
                f"earliest_start ({self.earliest_start}) > latest_start ({self.latest_start})"
            )
        if self.earliest_end > self.latest_end:
            raise ValueError(
                f"earliest_end ({self.earliest_end}) > latest_end ({self.latest_end})"
            )
        if self.earliest_start > self.latest_end:
            raise ValueError(
                f"earliest_start ({self.earliest_start}) > latest_end ({self.latest_end})"
            )

    @property
    def start_uncertainty(self) -> float:
        return self.latest_start - self.earliest_start

    @property
    def end_uncertainty(self) -> float:
        return self.latest_end - self.earliest_end

    @property
    def midpoint(self) -> float:
        s_mid = 0.5 * (self.earliest_start + self.latest_start)
        e_mid = 0.5 * (self.earliest_end + self.latest_end)
        return 0.5 * (s_mid + e_mid)

    @property
    def min_duration(self) -> float:
        return max(0.0, self.earliest_end - self.latest_start)

    @property
    def max_duration(self) -> float:
        return max(0.0, self.latest_end - self.earliest_start)

    def overlaps_window(self, start_year: float, end_year: float) -> bool:
        """Return True if the fuzzy interval could overlap [start_year, end_year]."""
        return not (self.latest_end < start_year or self.earliest_start > end_year)

    def to_cidoc_crm(self) -> dict[str, Any]:
        """Export as CIDOC-CRM v7.1.3 E52_Time-Span structure."""
        out: dict[str, Any] = {
            "type": "crm:E52_Time-Span",
            "crm:P82a_begin_of_the_begin": self.earliest_start,
            "crm:P81a_end_of_the_begin": self.latest_start,
            "crm:P81b_begin_of_the_end": self.earliest_end,
            "crm:P82b_end_of_the_end": self.latest_end,
        }
        if self.label:
            out["rdfs:label"] = self.label
        if self.periodo_id:
            out["owl:sameAs"] = f"http://n2t.net/ark:/99152/{self.periodo_id}"
        return out

    def to_lpf_timespan(self) -> dict[str, Any]:
        """Convert to an LPF `when.timespans` item."""
        start_obj: dict[str, Any] = {}
        if self.earliest_start == self.latest_start:
            start_obj["in"] = _format_year(self.earliest_start)
        else:
            start_obj["earliest"] = _format_year(self.earliest_start)
            start_obj["latest"] = _format_year(self.latest_start)

        end_obj: dict[str, Any] = {}
        if self.earliest_end == self.latest_end:
            end_obj["in"] = _format_year(self.earliest_end)
        else:
            end_obj["earliest"] = _format_year(self.earliest_end)
            end_obj["latest"] = _format_year(self.latest_end)

        ts: dict[str, Any] = {"start": start_obj, "end": end_obj}
        if self.certainty:
            ts["certainty"] = self.certainty
        if self.label:
            ts["label"] = self.label
        if self.periodo_id:
            ts["periodo_id"] = self.periodo_id
        return ts

    def to_dict(self) -> dict[str, Any]:
        return {
            "earliest_start": self.earliest_start,
            "latest_start": self.latest_start,
            "earliest_end": self.earliest_end,
            "latest_end": self.latest_end,
            "label": self.label,
            "periodo_id": self.periodo_id,
            "certainty": self.certainty,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FuzzyInterval":
        return cls(
            earliest_start=float(data["earliest_start"]),
            latest_start=float(data["latest_start"]),
            earliest_end=float(data["earliest_end"]),
            latest_end=float(data["latest_end"]),
            label=data.get("label"),
            periodo_id=data.get("periodo_id"),
            certainty=str(data.get("certainty", "certain")),
        )

    @classmethod
    def from_crisp(
        cls,
        start_year: float,
        end_year: float,
        label: str | None = None,
        periodo_id: str | None = None,
        certainty: str = "certain",
    ) -> "FuzzyInterval":
        return cls(
            earliest_start=float(start_year),
            latest_start=float(start_year),
            earliest_end=float(end_year),
            latest_end=float(end_year),
            label=label,
            periodo_id=periodo_id,
            certainty=certainty,
        )

    @classmethod
    def from_periodo(cls, data: dict[str, Any]) -> "FuzzyInterval":
        """Parse a PeriodO JSON-LD Period definition into a FuzzyInterval."""
        start_in = data.get("start", {}).get("in", {})
        stop_in = data.get("stop", {}).get("in", {})

        if "year" in start_in:
            es = ls = _parse_iso_year(start_in["year"])
        elif "earliestYear" in start_in or "latestYear" in start_in:
            es = _parse_iso_year(start_in.get("earliestYear", start_in["latestYear"]))
            ls = _parse_iso_year(start_in.get("latestYear", start_in["earliestYear"]))
        else:
            raise ValueError("PeriodO record missing start.in year/earliestYear/latestYear")

        if "year" in stop_in:
            ee = le = _parse_iso_year(stop_in["year"])
        elif "earliestYear" in stop_in or "latestYear" in stop_in:
            ee = _parse_iso_year(stop_in.get("earliestYear", stop_in["latestYear"]))
            le = _parse_iso_year(stop_in.get("latestYear", stop_in["earliestYear"]))
        else:
            ee, le = es, ls

        return cls(
            earliest_start=es,
            latest_start=ls,
            earliest_end=ee,
            latest_end=le,
            label=data.get("label"),
            periodo_id=data.get("id"),
            certainty="uncertain" if (es != ls or ee != le) else "certain",
        )

    @classmethod
    def from_lpf_timespan(cls, ts: dict[str, Any]) -> "FuzzyInterval":
        """Parse an LPF `when.timespans[i]` object into a FuzzyInterval."""
        start = ts.get("start") or {}
        end = ts.get("end") or {}

        if "in" in start:
            es = ls = _parse_iso_year(start["in"])
        elif "earliest" in start or "latest" in start:
            es = _parse_iso_year(start.get("earliest", start["latest"]))
            ls = _parse_iso_year(start.get("latest", start["earliest"]))
        else:
            raise ValueError("LPF timespan missing start bound")

        if "in" in end:
            ee = le = _parse_iso_year(end["in"])
        elif "earliest" in end or "latest" in end:
            ee = _parse_iso_year(end.get("earliest", end["latest"]))
            le = _parse_iso_year(end.get("latest", end["earliest"]))
        else:
            ee, le = es, ls

        return cls(
            earliest_start=es,
            latest_start=ls,
            earliest_end=ee,
            latest_end=le,
            label=ts.get("label"),
            periodo_id=ts.get("periodo_id"),
            certainty=str(ts.get("certainty", "certain")),
        )


def _format_year(year: float) -> str:
    y_int = int(round(year))
    if y_int < 0:
        return f"-{abs(y_int):04d}"
    return f"{y_int:04d}"


@dataclass(frozen=True)
class CompetingGeometry:
    """A candidate spatial hypothesis with belief weight, uncertainty radius, and citations."""

    hypothesis_id: str
    geometry: dict[str, Any]
    weight: float
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)
    uncertainty_radius_km: float = 0.0
    when: FuzzyInterval | None = None
    certainty: str = "uncertain"
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.hypothesis_id.strip():
            raise ValueError("CompetingGeometry.hypothesis_id must be non-empty")
        if not isinstance(self.geometry, dict) or "type" not in self.geometry:
            raise ValueError("CompetingGeometry.geometry must be a GeoJSON geometry dict")
        if not (0.0 < self.weight <= 1.0):
            raise ValueError(f"weight must be in (0, 1], got {self.weight}")
        if self.uncertainty_radius_km < 0.0:
            raise ValueError("uncertainty_radius_km must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "hypothesis_id": self.hypothesis_id,
            "geometry": self.geometry,
            "weight": self.weight,
            "uncertainty_radius_km": self.uncertainty_radius_km,
            "certainty": self.certainty,
            "evidence": [e.to_dict() for e in self.evidence],
        }
        if self.when is not None:
            out["when"] = self.when.to_dict()
        if self.notes is not None:
            out["notes"] = self.notes
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompetingGeometry":
        when_raw = data.get("when")
        return cls(
            hypothesis_id=str(data["hypothesis_id"]),
            geometry=dict(data["geometry"]),
            weight=float(data["weight"]),
            evidence=tuple(EvidenceRef.from_dict(e) for e in data.get("evidence", [])),
            uncertainty_radius_km=float(data.get("uncertainty_radius_km", 0.0)),
            when=FuzzyInterval.from_dict(when_raw) if when_raw else None,
            certainty=str(data.get("certainty", "uncertain")),
            notes=data.get("notes"),
        )


def normalize_hypothesis_weights(
    hypotheses: list[CompetingGeometry] | tuple[CompetingGeometry, ...],
) -> list[CompetingGeometry]:
    """Return competing geometries with weights normalized to sum to 1.0."""
    if not hypotheses:
        return []
    total = sum(h.weight for h in hypotheses)
    if total <= 0:
        raise ValueError("Total hypothesis weight must be positive")
    return [
        CompetingGeometry(
            hypothesis_id=h.hypothesis_id,
            geometry=h.geometry,
            weight=round(h.weight / total, 6),
            evidence=h.evidence,
            uncertainty_radius_km=h.uncertainty_radius_km,
            when=h.when,
            certainty=h.certainty,
            notes=h.notes,
        )
        for h in hypotheses
    ]


@dataclass(frozen=True)
class AffectLayer:
    """Sense-of-place / affective dimension (provisional open taxonomy per NARRATIVE_SCHEMA §3)."""

    valence: float = 0.0          # [-1.0 (grief/exile/dread), +1.0 (belonging/joy/reverence)]
    arousal: float = 0.5          # [0.0 (serene), 1.0 (intense)]
    dominant_mood: str = "neutral"
    tags: tuple[str, ...] = field(default_factory=tuple)
    sensory_notes: str | None = None
    taxonomy_status: str = "provisional_agnew_triad"
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not (-1.0 <= self.valence <= 1.0):
            raise ValueError(f"valence must be in [-1, 1], got {self.valence}")
        if not (0.0 <= self.arousal <= 1.0):
            raise ValueError(f"arousal must be in [0, 1], got {self.arousal}")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "valence": self.valence,
            "arousal": self.arousal,
            "dominant_mood": self.dominant_mood,
            "tags": list(self.tags),
            "taxonomy_status": self.taxonomy_status,
            "evidence": [e.to_dict() for e in self.evidence],
        }
        if self.sensory_notes is not None:
            out["sensory_notes"] = self.sensory_notes
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AffectLayer":
        return cls(
            valence=float(data.get("valence", 0.0)),
            arousal=float(data.get("arousal", 0.5)),
            dominant_mood=str(data.get("dominant_mood", "neutral")),
            tags=tuple(data.get("tags", ())),
            sensory_notes=data.get("sensory_notes"),
            taxonomy_status=str(data.get("taxonomy_status", "provisional_agnew_triad")),
            evidence=tuple(EvidenceRef.from_dict(e) for e in data.get("evidence", [])),
        )


@dataclass(frozen=True)
class PlatialAttributes:
    """Three-layer platial attribute bundle: location / locale / affect."""

    location: dict[str, Any] = field(default_factory=dict)
    locale: dict[str, Any] = field(default_factory=dict)
    affect: AffectLayer = field(default_factory=AffectLayer)

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": dict(self.location),
            "locale": dict(self.locale),
            "affect": self.affect.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlatialAttributes":
        return cls(
            location=dict(data.get("location", {})),
            locale=dict(data.get("locale", {})),
            affect=AffectLayer.from_dict(data.get("affect", {})),
        )


@dataclass
class PlatialPlace:
    """Core platial historical entity with fuzzy time, competing geometries, and archival silence."""

    place_id: str
    title: str
    fclasses: tuple[str, ...] = ("P",)
    names: list[dict[str, Any]] = field(default_factory=list)
    when: FuzzyInterval | None = None
    geometries: list[CompetingGeometry] = field(default_factory=list)
    absence: AbsenceState | None = None
    absence_reason: str | None = None
    platial: PlatialAttributes = field(default_factory=PlatialAttributes)
    evidence: list[EvidenceRef] = field(default_factory=list)
    ccodes: list[str] = field(default_factory=list)
    types: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    descriptions: list[dict[str, Any]] = field(default_factory=list)
    provenance: str = "unspecified"

    def __post_init__(self) -> None:
        if not self.place_id.strip():
            raise ValueError("PlatialPlace.place_id must be non-empty")
        if not self.title.strip():
            raise ValueError("PlatialPlace.title must be non-empty")
        if not self.fclasses:
            raise ValueError("LPF v1.3 requires at least one fclass in {A,H,L,P,R,S,T}")
        invalid = set(self.fclasses) - VALID_FCLASSES
        if invalid:
            raise ValueError(f"Invalid fclasses {sorted(invalid)}; allowed: {sorted(VALID_FCLASSES)}")
        if isinstance(self.absence, str):
            self.absence = AbsenceState(self.absence)
        if self.absence is None and not self.geometries:
            raise ValueError(
                "A PlatialPlace without geometries must declare an explicit AbsenceState "
                "(absent / unrecorded / contested)"
            )

    @property
    def primary_geometry(self) -> CompetingGeometry | None:
        if not self.geometries:
            return None
        return max(self.geometries, key=lambda g: g.weight)

    def to_dict(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "title": self.title,
            "fclasses": list(self.fclasses),
            "names": list(self.names),
            "when": self.when.to_dict() if self.when else None,
            "geometries": [g.to_dict() for g in self.geometries],
            "absence": self.absence.value if self.absence else None,
            "absence_reason": self.absence_reason,
            "platial": self.platial.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "ccodes": list(self.ccodes),
            "types": list(self.types),
            "relations": list(self.relations),
            "links": list(self.links),
            "descriptions": list(self.descriptions),
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlatialPlace":
        when_raw = data.get("when")
        absence_raw = data.get("absence")
        return cls(
            place_id=str(data["place_id"]),
            title=str(data["title"]),
            fclasses=tuple(data.get("fclasses", ("P",))),
            names=list(data.get("names", [])),
            when=FuzzyInterval.from_dict(when_raw) if when_raw else None,
            geometries=[CompetingGeometry.from_dict(g) for g in data.get("geometries", [])],
            absence=AbsenceState(absence_raw) if absence_raw else None,
            absence_reason=data.get("absence_reason"),
            platial=PlatialAttributes.from_dict(data.get("platial", {})),
            evidence=[EvidenceRef.from_dict(e) for e in data.get("evidence", [])],
            ccodes=list(data.get("ccodes", [])),
            types=list(data.get("types", [])),
            relations=list(data.get("relations", [])),
            links=list(data.get("links", [])),
            descriptions=list(data.get("descriptions", [])),
            provenance=str(data.get("provenance", "unspecified")),
        )
