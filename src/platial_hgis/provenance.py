"""D3-P6: Necessary Reunions-inspired dual-track AI vs. Human Verified provenance ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import pathlib
from typing import Any

VALID_ANNOTATION_TYPES = frozenset({"Text Spotting", "Iconography", "Georeferencing", "Linking"})
VALID_SOURCES = frozenset({"Loghi AI", "Other AI", "Human"})
VALID_VERIFICATION_STATUS = frozenset({"AI", "Human Verified"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compute_stamp(payload: dict[str, Any], prev_hash: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(b"|")
    h.update(canonical.encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True)
class SpatialAnchor:
    """Spatial anchor combining IIIF canvas coordinates, reading order, and gazetteer URI."""

    canvas_id: str
    canvas_xy: tuple[float, float]
    geotag_uri: str | None = None
    reading_order: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "canvas_id": self.canvas_id,
            "canvas_xy": [self.canvas_xy[0], self.canvas_xy[1]],
            "geotag_uri": self.geotag_uri,
            "reading_order": self.reading_order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpatialAnchor":
        xy = data["canvas_xy"]
        return cls(
            canvas_id=str(data["canvas_id"]),
            canvas_xy=(float(xy[0]), float(xy[1])),
            geotag_uri=data.get("geotag_uri"),
            reading_order=data.get("reading_order"),
        )


@dataclass(frozen=True)
class RevisionEntry:
    """Immutable hash-chained revision entry in an annotation's audit history."""

    revision_no: int
    timestamp: str
    actor: str
    action: str  # "propose" | "edit" | "verify" | "revoke"
    verification_status: str
    assessment_checked: bool
    summary: str
    payload_snapshot: dict[str, Any]
    prev_hash: str
    stamp_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_no": self.revision_no,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "verification_status": self.verification_status,
            "assessment_checked": self.assessment_checked,
            "summary": self.summary,
            "payload_snapshot": self.payload_snapshot,
            "prev_hash": self.prev_hash,
            "stamp_sha256": self.stamp_sha256,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RevisionEntry":
        return cls(
            revision_no=int(data["revision_no"]),
            timestamp=str(data["timestamp"]),
            actor=str(data["actor"]),
            action=str(data["action"]),
            verification_status=str(data["verification_status"]),
            assessment_checked=bool(data["assessment_checked"]),
            summary=str(data["summary"]),
            payload_snapshot=dict(data["payload_snapshot"]),
            prev_hash=str(data["prev_hash"]),
            stamp_sha256=str(data["stamp_sha256"]),
        )


@dataclass
class DualTrackRecord:
    """Single VLM/HTR or human historical map/gazetteer extraction with dual-track stamp."""

    annotation_id: str
    annotation_type: str
    source: str
    verification_status: str
    assessment_checked: bool
    assessment_by: str | None
    extracted_text: str
    normalized_toponym: str | None = None
    confidence: float = 0.0
    spatial_anchor: SpatialAnchor | None = None
    source_citation: str = ""
    revisions: list[RevisionEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.annotation_type not in VALID_ANNOTATION_TYPES:
            raise ValueError(f"Invalid annotation_type {self.annotation_type!r}")
        if self.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source {self.source!r}")
        if self.verification_status not in VALID_VERIFICATION_STATUS:
            raise ValueError(f"Invalid verification_status {self.verification_status!r}")
        # Guard invariant: AI-only records cannot silently be marked checked without a human assessor
        if self.assessment_checked and not (self.assessment_by and self.assessment_by.strip()):
            raise ValueError("assessment_checked=True requires a non-empty assessment_by human reviewer")

    @property
    def is_verified_layer_eligible(self) -> bool:
        """Strictly matches Necessary Reunions gate: only checked Human Verified enter verified layer."""
        return (
            self.verification_status == "Human Verified"
            and self.assessment_checked
            and bool(self.assessment_by and self.assessment_by.strip())
        )

    def _current_payload(self) -> dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "annotation_type": self.annotation_type,
            "source": self.source,
            "extracted_text": self.extracted_text,
            "normalized_toponym": self.normalized_toponym,
            "confidence": self.confidence,
            "spatial_anchor": self.spatial_anchor.to_dict() if self.spatial_anchor else None,
            "source_citation": self.source_citation,
        }

    def verify_integrity(self) -> bool:
        """Verify SHA-256 hash chain across all revisions."""
        prev = "GENESIS"
        for rev in self.revisions:
            if rev.prev_hash != prev:
                return False
            expected = _compute_stamp(rev.payload_snapshot, prev)
            if rev.stamp_sha256 != expected:
                return False
            prev = rev.stamp_sha256
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "annotation_type": self.annotation_type,
            "source": self.source,
            "verification_status": self.verification_status,
            "assessment_checked": self.assessment_checked,
            "assessment_by": self.assessment_by,
            "extracted_text": self.extracted_text,
            "normalized_toponym": self.normalized_toponym,
            "confidence": self.confidence,
            "spatial_anchor": self.spatial_anchor.to_dict() if self.spatial_anchor else None,
            "source_citation": self.source_citation,
            "revisions": [r.to_dict() for r in self.revisions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DualTrackRecord":
        sa = data.get("spatial_anchor")
        return cls(
            annotation_id=str(data["annotation_id"]),
            annotation_type=str(data["annotation_type"]),
            source=str(data["source"]),
            verification_status=str(data["verification_status"]),
            assessment_checked=bool(data["assessment_checked"]),
            assessment_by=data.get("assessment_by"),
            extracted_text=str(data["extracted_text"]),
            normalized_toponym=data.get("normalized_toponym"),
            confidence=float(data.get("confidence", 0.0)),
            spatial_anchor=SpatialAnchor.from_dict(sa) if sa else None,
            source_citation=str(data.get("source_citation", "")),
            revisions=[RevisionEntry.from_dict(r) for r in data.get("revisions", [])],
        )


class ProvenanceLedger:
    """Manages dual-track AI/Human extraction records, human sign-off, and verified layer export."""

    def __init__(self, records: list[DualTrackRecord] | None = None) -> None:
        self._records: dict[str, DualTrackRecord] = {}
        for r in records or []:
            self._records[r.annotation_id] = r

    def propose_ai_extraction(
        self,
        *,
        annotation_id: str,
        annotation_type: str,
        extracted_text: str,
        source: str = "Other AI",
        normalized_toponym: str | None = None,
        confidence: float = 0.8,
        spatial_anchor: SpatialAnchor | None = None,
        source_citation: str = "",
    ) -> DualTrackRecord:
        """Create a new AI-proposed record (starts strictly in unverified 'AI' track)."""
        if annotation_id in self._records:
            raise ValueError(f"Duplicate annotation_id: {annotation_id!r}")
        rec = DualTrackRecord(
            annotation_id=annotation_id,
            annotation_type=annotation_type,
            source=source,
            verification_status="AI",
            assessment_checked=False,
            assessment_by=None,
            extracted_text=extracted_text,
            normalized_toponym=normalized_toponym,
            confidence=confidence,
            spatial_anchor=spatial_anchor,
            source_citation=source_citation,
        )
        snap = rec._current_payload()
        stamp = _compute_stamp(snap, "GENESIS")
        rec.revisions.append(
            RevisionEntry(
                revision_no=1,
                timestamp=_utc_now(),
                actor=source,
                action="propose",
                verification_status="AI",
                assessment_checked=False,
                summary=f"Initial {source} extraction ({annotation_type})",
                payload_snapshot=snap,
                prev_hash="GENESIS",
                stamp_sha256=stamp,
            )
        )
        self._records[annotation_id] = rec
        return rec

    def human_verify(
        self,
        annotation_id: str,
        *,
        reviewer: str,
        corrected_text: str | None = None,
        corrected_toponym: str | None = None,
        geotag_uri: str | None = None,
        summary: str = "Human verified against primary map/gazetteer",
    ) -> DualTrackRecord:
        """Apply Human Verified checkmark sign-off with optional correction and hash-chained revision."""
        if not reviewer.strip():
            raise ValueError("Human verification requires a non-empty reviewer identifier")
        if annotation_id not in self._records:
            raise KeyError(f"Unknown annotation_id: {annotation_id!r}")
        rec = self._records[annotation_id]
        if corrected_text is not None:
            rec.extracted_text = corrected_text
        if corrected_toponym is not None:
            rec.normalized_toponym = corrected_toponym
        if geotag_uri is not None and rec.spatial_anchor is not None:
            rec.spatial_anchor = SpatialAnchor(
                canvas_id=rec.spatial_anchor.canvas_id,
                canvas_xy=rec.spatial_anchor.canvas_xy,
                geotag_uri=geotag_uri,
                reading_order=rec.spatial_anchor.reading_order,
            )
        rec.verification_status = "Human Verified"
        rec.assessment_checked = True
        rec.assessment_by = reviewer.strip()

        prev_hash = rec.revisions[-1].stamp_sha256 if rec.revisions else "GENESIS"
        snap = rec._current_payload()
        stamp = _compute_stamp(snap, prev_hash)
        rec.revisions.append(
            RevisionEntry(
                revision_no=len(rec.revisions) + 1,
                timestamp=_utc_now(),
                actor=reviewer.strip(),
                action="verify",
                verification_status="Human Verified",
                assessment_checked=True,
                summary=summary,
                payload_snapshot=snap,
                prev_hash=prev_hash,
                stamp_sha256=stamp,
            )
        )
        return rec

    def all_records(self) -> list[DualTrackRecord]:
        return list(self._records.values())

    def export_verified_layer(self) -> list[DualTrackRecord]:
        """Export ONLY Human Verified & checked records (unverified AI is strictly excluded)."""
        return [r for r in self._records.values() if r.is_verified_layer_eligible]

    def summary_stats(self) -> dict[str, int]:
        total = len(self._records)
        verified = sum(1 for r in self._records.values() if r.is_verified_layer_eligible)
        return {
            "total": total,
            "human_verified": verified,
            "ai_pending": total - verified,
        }

    def save(self, path: str | pathlib.Path) -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "platial-hgis/provenance-ledger/v1",
            "stats": self.summary_stats(),
            "records": [r.to_dict() for r in self._records.values()],
        }
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | pathlib.Path) -> "ProvenanceLedger":
        raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls([DualTrackRecord.from_dict(r) for r in raw.get("records", [])])
