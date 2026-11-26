"""D3-P1: Lossless LPF JSON-LD (v1.1 / v1.2.2 / v1.3) I/O and strict JSON Schema validation."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import jsonschema

from .primitives import (
    AbsenceState,
    CompetingGeometry,
    EvidenceRef,
    FuzzyInterval,
    PlatialAttributes,
    PlatialPlace,
    VALID_FCLASSES,
)

LPF_CONTEXT_V11 = (
    "https://raw.githubusercontent.com/LinkedPasts/linked-places-format/master/"
    "linkedplaces-context-v1.1.jsonld"
)

LPF_FEATURE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["type", "@id", "properties"],
    "properties": {
        "@context": {"type": ["string", "object", "array"]},
        "type": {"const": "Feature"},
        "@id": {"type": "string", "minLength": 1},
        "properties": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string", "minLength": 1},
                "fclasses": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"enum": sorted(VALID_FCLASSES)},
                },
                "ccodes": {"type": "array", "items": {"type": "string"}},
            },
        },
        "geometry": {"type": ["object", "null"]},
        "when": {"type": "object"},
        "names": {"type": "array"},
        "types": {"type": "array"},
        "relations": {"type": "array"},
        "links": {"type": "array"},
        "descriptions": {"type": "array"},
    },
}

LPF_COLLECTION_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["type", "features"],
    "properties": {
        "@context": {"type": ["string", "object", "array"]},
        "type": {"const": "FeatureCollection"},
        "features": {
            "type": "array",
            "items": LPF_FEATURE_SCHEMA,
        },
    },
}


class LPFValidationError(ValueError):
    """Raised when an LPF JSON-LD document violates schema constraints."""


def validate_lpf(doc: dict[str, Any], *, strict_v13: bool = True) -> None:
    """Validate an LPF Feature or FeatureCollection against JSON Schema & v1.3 rules."""
    doc_type = doc.get("type")
    if doc_type == "FeatureCollection":
        try:
            jsonschema.validate(instance=doc, schema=LPF_COLLECTION_SCHEMA)
        except jsonschema.ValidationError as exc:
            raise LPFValidationError(f"LPF FeatureCollection schema error: {exc.message}") from exc
        features = doc.get("features", [])
    elif doc_type == "Feature":
        try:
            jsonschema.validate(instance=doc, schema=LPF_FEATURE_SCHEMA)
        except jsonschema.ValidationError as exc:
            raise LPFValidationError(f"LPF Feature schema error: {exc.message}") from exc
        features = [doc]
    else:
        raise LPFValidationError(
            f"Unsupported LPF root type {doc_type!r}; expected 'Feature' or 'FeatureCollection'"
        )

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        if strict_v13 and not props.get("fclasses"):
            raise LPFValidationError(
                f"Feature[{idx}] ({feat.get('@id')}) missing required LPF v1.3 'properties.fclasses'"
            )
        geom = feat.get("geometry")
        absence = props.get("platial:absence") or feat.get("platial:absence")
        if geom is None and absence is None:
            raise LPFValidationError(
                f"Feature[{idx}] ({feat.get('@id')}) has null geometry without explicit archival silence 'platial:absence'"
            )
        if absence is not None and absence not in {s.value for s in AbsenceState}:
            raise LPFValidationError(
                f"Feature[{idx}] has invalid platial:absence {absence!r}"
            )


def _infer_fclasses(feat: dict[str, Any]) -> tuple[str, ...]:
    props = feat.get("properties", {})
    raw = props.get("fclasses")
    if raw:
        valid = tuple(c for c in raw if c in VALID_FCLASSES)
        if valid:
            return valid
    # Infer from WHG types[*].label (e.g. "P" or "P.PPLA")
    inferred: list[str] = []
    for t in feat.get("types", []):
        lbl = str(t.get("label", "")).strip()
        if lbl in VALID_FCLASSES and lbl not in inferred:
            inferred.append(lbl)
        elif "." in str(t.get("sourceLabel", "")):
            prefix = str(t["sourceLabel"]).split(".")[0]
            if prefix in VALID_FCLASSES and prefix not in inferred:
                inferred.append(prefix)
    return tuple(inferred) if inferred else ("P",)


def place_to_lpf_feature(place: PlatialPlace, *, include_context: bool = False) -> dict[str, Any]:
    """Serialize a PlatialPlace into a lossless LPF v1.3 JSON-LD Feature."""
    props: dict[str, Any] = {
        "title": place.title,
        "fclasses": list(place.fclasses),
    }
    if place.ccodes:
        props["ccodes"] = list(place.ccodes)
    if place.absence is not None:
        props["platial:absence"] = place.absence.value
    if place.absence_reason:
        props["platial:absence_reason"] = place.absence_reason
    props["platial:attributes"] = place.platial.to_dict()
    props["platial:provenance"] = place.provenance
    if place.evidence:
        props["platial:evidence"] = [e.to_dict() for e in place.evidence]

    geometry: dict[str, Any] | None
    if not place.geometries:
        geometry = None
    elif len(place.geometries) == 1:
        g = place.geometries[0]
        geometry = dict(g.geometry)
        geometry["hypothesis_id"] = g.hypothesis_id
        geometry["weight"] = g.weight
        geometry["uncertainty_radius_km"] = g.uncertainty_radius_km
        geometry["certainty"] = g.certainty
        if g.when is not None:
            geometry["when"] = {"timespans": [g.when.to_lpf_timespan()]}
        if g.evidence:
            geometry["citations"] = [e.to_dict() for e in g.evidence]
        if g.notes:
            geometry["notes"] = g.notes
    else:
        geoms = []
        for g in place.geometries:
            sub = dict(g.geometry)
            sub["hypothesis_id"] = g.hypothesis_id
            sub["weight"] = g.weight
            sub["uncertainty_radius_km"] = g.uncertainty_radius_km
            sub["certainty"] = g.certainty
            if g.when is not None:
                sub["when"] = {"timespans": [g.when.to_lpf_timespan()]}
            if g.evidence:
                sub["citations"] = [e.to_dict() for e in g.evidence]
            if g.notes:
                sub["notes"] = g.notes
            geoms.append(sub)
        geometry = {"type": "GeometryCollection", "geometries": geoms}

    feat: dict[str, Any] = {}
    if include_context:
        feat["@context"] = LPF_CONTEXT_V11
    feat["@id"] = place.place_id
    feat["type"] = "Feature"
    feat["properties"] = props
    feat["geometry"] = geometry

    if place.names:
        feat["names"] = list(place.names)
    if place.types:
        feat["types"] = list(place.types)
    if place.when is not None:
        feat["when"] = {"timespans": [place.when.to_lpf_timespan()]}
    if place.relations:
        feat["relations"] = list(place.relations)
    if place.links:
        feat["links"] = list(place.links)
    if place.descriptions:
        feat["descriptions"] = list(place.descriptions)
    return feat


def places_to_lpf_collection(places: list[PlatialPlace]) -> dict[str, Any]:
    """Serialize a list of PlatialPlace objects into an LPF JSON-LD FeatureCollection."""
    return {
        "@context": LPF_CONTEXT_V11,
        "type": "FeatureCollection",
        "features": [place_to_lpf_feature(p, include_context=False) for p in places],
    }


def _parse_citations(raw_cits: list[dict[str, Any]] | None) -> tuple[EvidenceRef, ...]:
    if not raw_cits:
        return ()
    out: list[EvidenceRef] = []
    for idx, c in enumerate(raw_cits):
        if "source_id" in c:
            out.append(EvidenceRef.from_dict(c))
        else:
            out.append(
                EvidenceRef(
                    source_id=str(c.get("@id") or c.get("id") or f"cit-{idx}"),
                    label=str(c.get("label") or c.get("@id") or "citation"),
                    uri=c.get("@id") if str(c.get("@id", "")).startswith("http") else None,
                    evidence_level="verified",
                )
            )
    return tuple(out)


def _parse_geometry_entry(raw: dict[str, Any], idx: int) -> CompetingGeometry:
    geom_core = {
        k: v for k, v in raw.items() if k in {"type", "coordinates", "geometries", "geowkt"}
    }
    when_obj = None
    if isinstance(raw.get("when"), dict) and raw["when"].get("timespans"):
        when_obj = FuzzyInterval.from_lpf_timespan(raw["when"]["timespans"][0])
    return CompetingGeometry(
        hypothesis_id=str(raw.get("hypothesis_id", f"hyp-{idx}")),
        geometry=geom_core,
        weight=float(raw.get("weight", 1.0)),
        evidence=_parse_citations(raw.get("citations")),
        uncertainty_radius_km=float(raw.get("uncertainty_radius_km", 0.0)),
        when=when_obj,
        certainty=str(raw.get("certainty", "certain")),
        notes=raw.get("notes"),
    )


def lpf_feature_to_place(feat: dict[str, Any]) -> PlatialPlace:
    """Deserialize an LPF v1.1/v1.2.2/v1.3 Feature into a PlatialPlace."""
    props = feat.get("properties", {})
    place_id = str(feat.get("@id") or feat.get("id") or props.get("source_id") or "")
    title = str(props.get("title") or place_id)
    fclasses = _infer_fclasses(feat)

    when_obj = None
    when_raw = feat.get("when")
    if isinstance(when_raw, dict) and when_raw.get("timespans"):
        when_obj = FuzzyInterval.from_lpf_timespan(when_raw["timespans"][0])

    geometries: list[CompetingGeometry] = []
    raw_geom = feat.get("geometry")
    if isinstance(raw_geom, dict):
        if raw_geom.get("type") == "GeometryCollection":
            sub_geoms = raw_geom.get("geometries", [])
            n = max(1, len(sub_geoms))
            for idx, sg in enumerate(sub_geoms):
                entry = dict(sg)
                if "weight" not in entry:
                    entry["weight"] = round(1.0 / n, 6)
                geometries.append(_parse_geometry_entry(entry, idx))
        elif "type" in raw_geom:
            geometries.append(_parse_geometry_entry(raw_geom, 0))

    absence_raw = props.get("platial:absence") or feat.get("platial:absence")
    absence = AbsenceState(absence_raw) if absence_raw else None
    if absence is None and not geometries:
        absence = AbsenceState.UNRECORDED

    platial_raw = props.get("platial:attributes")
    if platial_raw:
        platial = PlatialAttributes.from_dict(platial_raw)
    else:
        platial = PlatialAttributes(
            location={"ccodes": list(props.get("ccodes", []))},
            locale={"fclasses": list(fclasses), "types": list(feat.get("types", []))},
        )

    evidence = [EvidenceRef.from_dict(e) for e in props.get("platial:evidence", [])]
    if not evidence and isinstance(feat.get("attribution"), dict):
        attr = feat["attribution"]
        evidence.append(
            EvidenceRef(
                source_id=str(attr.get("id", "whg-attribution")),
                label=str(attr.get("citation_text") or attr.get("name") or "WHG Attribution"),
                uri=attr.get("source_url"),
                evidence_level="verified",
            )
        )

    return PlatialPlace(
        place_id=place_id,
        title=title,
        fclasses=fclasses,
        names=list(feat.get("names", [])),
        when=when_obj,
        geometries=geometries,
        absence=absence,
        absence_reason=props.get("platial:absence_reason"),
        platial=platial,
        evidence=evidence,
        ccodes=list(props.get("ccodes", [])),
        types=list(feat.get("types", [])),
        relations=list(feat.get("relations", [])),
        links=list(feat.get("links", [])),
        descriptions=list(feat.get("descriptions", [])),
        provenance=str(props.get("platial:provenance", "lpf_import")),
    )


def load_lpf(path_or_data: str | pathlib.Path | dict[str, Any], *, strict_v13: bool = False) -> list[PlatialPlace]:
    """Load an LPF Feature or FeatureCollection from a JSON file or dict."""
    if isinstance(path_or_data, (str, pathlib.Path)):
        doc = json.loads(pathlib.Path(path_or_data).read_text(encoding="utf-8"))
    else:
        doc = path_or_data
    validate_lpf(doc, strict_v13=strict_v13)
    if doc.get("type") == "FeatureCollection":
        return [lpf_feature_to_place(f) for f in doc.get("features", [])]
    return [lpf_feature_to_place(doc)]


def save_lpf(places: list[PlatialPlace], path: str | pathlib.Path, *, strict_v13: bool = True) -> dict[str, Any]:
    """Serialize places to an LPF JSON-LD FeatureCollection, validate, and write to disk."""
    doc = places_to_lpf_collection(places)
    validate_lpf(doc, strict_v13=strict_v13)
    out_path = pathlib.Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
