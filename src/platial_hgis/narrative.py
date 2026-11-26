"""D3-P5: Evidence-bound spatiotemporal narrative storyboard schema and compiler validator."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import pathlib
from typing import Any

import yaml

from .primitives import EvidenceRef, FuzzyInterval, VALID_EVIDENCE_LEVELS

VALID_SHOT_TYPES = frozenset({"establishing", "push_in", "pull_out", "pan", "orbit", "cut", "tracking"})
VALID_TEMPORAL_SHIFTS = frozenset({"chronological", "flashback", "flashforward", "parallel", "still"})
VALID_TRANSITIONS = frozenset({"fly_to", "dissolve", "cut", "wipe", "fade"})
VALID_MAP_VIEWS = frozenset({"modern", "historical", "split"})


class NarrativeValidationError(ValueError):
    """Raised when a narrative storyboard violates evidence-binding or camera rules."""


@dataclass(frozen=True)
class CameraSpec:
    """Cinematic map camera parameters for a narrative scene."""

    center: tuple[float, float]  # (lon, lat)
    zoom: float
    bearing: float = 0.0
    pitch: float = 0.0
    shot_type: str = "establishing"

    def __post_init__(self) -> None:
        lon, lat = self.center
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise NarrativeValidationError(f"Camera center out of WGS84 bounds: {self.center}")
        if self.zoom <= 0 or self.zoom > 22:
            raise NarrativeValidationError(f"Camera zoom must be in (0, 22], got {self.zoom}")
        if not (0.0 <= self.pitch <= 85.0):
            raise NarrativeValidationError(f"Camera pitch must be in [0, 85], got {self.pitch}")
        if self.shot_type not in VALID_SHOT_TYPES:
            raise NarrativeValidationError(
                f"Invalid shot_type {self.shot_type!r}; expected one of {sorted(VALID_SHOT_TYPES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "center": [self.center[0], self.center[1]],
            "zoom": self.zoom,
            "bearing": self.bearing,
            "pitch": self.pitch,
            "shot_type": self.shot_type,
        }


@dataclass(frozen=True)
class NarrativeScene:
    """Single evidence-bound narrative unit & map scene (per NARRATIVE_SCHEMA.md §1)."""

    narrative_unit_id: str
    map_scene_id: str
    title: str
    heritage_element: str
    narrative_text: str
    when: FuzzyInterval
    camera: CameraSpec
    evidence_level: str
    evidence_ids: tuple[str, ...]
    unit_type: str = "node"
    spatial_extent: list[float] | None = None  # [min_lon, min_lat, max_lon, max_lat]
    shot_sequence: tuple[str, ...] = field(default_factory=tuple)
    scale: str = "regional"
    temporal_shift: str = "chronological"
    duration_sec: float = 8.0
    pace: str = "medium"
    transition: str = "fly_to"
    map_view: str = "modern"
    valence: float = 0.0
    dominant_mood: str = "neutral"

    def to_dict(self) -> dict[str, Any]:
        return {
            "narrative_unit_id": self.narrative_unit_id,
            "map_scene_id": self.map_scene_id,
            "title": self.title,
            "heritage_element": self.heritage_element,
            "narrative_text": self.narrative_text,
            "when": self.when.to_dict(),
            "camera": self.camera.to_dict(),
            "evidence_level": self.evidence_level,
            "evidence_ids": list(self.evidence_ids),
            "unit_type": self.unit_type,
            "spatial_extent": self.spatial_extent,
            "shot_sequence": list(self.shot_sequence),
            "scale": self.scale,
            "temporal_shift": self.temporal_shift,
            "duration_sec": self.duration_sec,
            "pace": self.pace,
            "transition": self.transition,
            "map_view": self.map_view,
            "valence": self.valence,
            "dominant_mood": self.dominant_mood,
        }


@dataclass(frozen=True)
class NarrativeStoryboard:
    """Validated evidence-bound spatiotemporal narrative storyboard."""

    storyboard_id: str
    title: str
    subtitle: str
    provenance_notice: str
    sources: dict[str, EvidenceRef]
    scenes: tuple[NarrativeScene, ...]
    schema_status: str = "ijde_2026_summary_reconstructed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "storyboard_id": self.storyboard_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "provenance_notice": self.provenance_notice,
            "schema_status": self.schema_status,
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
            "scenes": [s.to_dict() for s in self.scenes],
        }


def parse_storyboard_dict(raw: dict[str, Any]) -> NarrativeStoryboard:
    """Validate and parse a storyboard dictionary, enforcing strict evidence binding."""
    if not isinstance(raw, dict):
        raise NarrativeValidationError("Storyboard root must be a YAML/JSON mapping")

    sb_id = str(raw.get("storyboard_id", "")).strip()
    title = str(raw.get("title", "")).strip()
    if not sb_id or not title:
        raise NarrativeValidationError("Storyboard requires non-empty 'storyboard_id' and 'title'")

    raw_sources = raw.get("sources") or []
    sources: dict[str, EvidenceRef] = {}
    if isinstance(raw_sources, dict):
        for sid, sdata in raw_sources.items():
            d = dict(sdata)
            d.setdefault("source_id", sid)
            ref = EvidenceRef.from_dict(d)
            sources[ref.source_id] = ref
    elif isinstance(raw_sources, list):
        for sdata in raw_sources:
            ref = EvidenceRef.from_dict(sdata)
            sources[ref.source_id] = ref
    else:
        raise NarrativeValidationError("'sources' must be a list or mapping of source entries")

    raw_scenes = raw.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise NarrativeValidationError("Storyboard must contain at least one scene in 'scenes'")

    scenes: list[NarrativeScene] = []
    seen_ids: set[str] = set()
    for idx, sc in enumerate(raw_scenes):
        if not isinstance(sc, dict):
            raise NarrativeValidationError(f"Scene[{idx}] must be an object")

        unit_id = str(sc.get("narrative_unit_id") or f"unit-{idx+1}")
        scene_id = str(sc.get("map_scene_id") or f"scene-{idx+1}")
        if scene_id in seen_ids:
            raise NarrativeValidationError(f"Duplicate map_scene_id: {scene_id!r}")
        seen_ids.add(scene_id)

        ev_level = str(sc.get("evidence_level", "")).strip()
        if ev_level not in VALID_EVIDENCE_LEVELS:
            raise NarrativeValidationError(
                f"Scene {scene_id!r} has invalid or missing evidence_level {ev_level!r}; "
                f"expected one of {sorted(VALID_EVIDENCE_LEVELS)}"
            )

        ev_ids = tuple(str(x) for x in (sc.get("evidence_ids") or []) if str(x).strip())
        # HARD GATE: reject uncited scenes unless explicitly marked speculative
        if not ev_ids and ev_level != "speculative":
            raise NarrativeValidationError(
                f"Scene {scene_id!r} has no 'evidence_ids' but evidence_level is {ev_level!r}; "
                "uncited nodes are strictly rejected unless marked 'speculative'."
            )
        unknown_ev = [eid for eid in ev_ids if eid not in sources]
        if unknown_ev:
            raise NarrativeValidationError(
                f"Scene {scene_id!r} references undeclared evidence_ids: {unknown_ev}"
            )

        cam_raw = sc.get("camera")
        if not isinstance(cam_raw, dict) or "center" not in cam_raw or "zoom" not in cam_raw:
            raise NarrativeValidationError(
                f"Scene {scene_id!r} missing required camera parameters ('center' and 'zoom')"
            )
        center_raw = cam_raw["center"]
        if not isinstance(center_raw, (list, tuple)) or len(center_raw) != 2:
            raise NarrativeValidationError(f"Scene {scene_id!r} camera.center must be [lon, lat]")
        camera = CameraSpec(
            center=(float(center_raw[0]), float(center_raw[1])),
            zoom=float(cam_raw["zoom"]),
            bearing=float(cam_raw.get("bearing", 0.0)),
            pitch=float(cam_raw.get("pitch", 0.0)),
            shot_type=str(cam_raw.get("shot_type", "establishing")),
        )

        when_raw = sc.get("when")
        if not isinstance(when_raw, dict):
            raise NarrativeValidationError(f"Scene {scene_id!r} missing required 'when' FuzzyInterval")
        when = FuzzyInterval.from_dict(when_raw)

        t_shift = str(sc.get("temporal_shift", "chronological"))
        if t_shift not in VALID_TEMPORAL_SHIFTS:
            raise NarrativeValidationError(f"Scene {scene_id!r} invalid temporal_shift {t_shift!r}")
        trans = str(sc.get("transition", "fly_to"))
        if trans not in VALID_TRANSITIONS:
            raise NarrativeValidationError(f"Scene {scene_id!r} invalid transition {trans!r}")
        mview = str(sc.get("map_view", "modern"))
        if mview not in VALID_MAP_VIEWS:
            raise NarrativeValidationError(f"Scene {scene_id!r} invalid map_view {mview!r}")

        scenes.append(
            NarrativeScene(
                narrative_unit_id=unit_id,
                map_scene_id=scene_id,
                title=str(sc.get("title", scene_id)),
                heritage_element=str(sc.get("heritage_element", "")),
                narrative_text=str(sc.get("narrative_text", "")),
                when=when,
                camera=camera,
                evidence_level=ev_level,
                evidence_ids=ev_ids,
                unit_type=str(sc.get("unit_type", "node")),
                spatial_extent=sc.get("spatial_extent"),
                shot_sequence=tuple(sc.get("shot_sequence") or (camera.shot_type,)),
                scale=str(sc.get("scale", "regional")),
                temporal_shift=t_shift,
                duration_sec=float(sc.get("duration_sec", 8.0)),
                pace=str(sc.get("pace", "medium")),
                transition=trans,
                map_view=mview,
                valence=float(sc.get("valence", 0.0)),
                dominant_mood=str(sc.get("dominant_mood", "neutral")),
            )
        )

    return NarrativeStoryboard(
        storyboard_id=sb_id,
        title=title,
        subtitle=str(raw.get("subtitle", "")),
        provenance_notice=str(
            raw.get("provenance_notice", "Open historical demonstration storyboard")
        ),
        sources=sources,
        scenes=tuple(scenes),
    )


def load_storyboard(path: str | pathlib.Path) -> NarrativeStoryboard:
    """Load and validate a YAML or JSON narrative storyboard file."""
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        raw = yaml.safe_load(text)
    else:
        raw = json.loads(text)
    return parse_storyboard_dict(raw)
