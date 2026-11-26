"""D3-P1: Lossless GeoParquet v1.0.0 and JSON bidirectional I/O for PlatialPlace collections."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import shape
import shapely

from .primitives import PlatialPlace


def save_json(places: list[PlatialPlace], path: str | pathlib.Path) -> None:
    """Serialize PlatialPlace list to canonical JSON."""
    out = pathlib.Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "platial-hgis/places/v1",
        "count": len(places),
        "places": [p.to_dict() for p in places],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: str | pathlib.Path) -> list[PlatialPlace]:
    """Load PlatialPlace list from canonical JSON."""
    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    items = raw["places"] if isinstance(raw, dict) and "places" in raw else raw
    return [PlatialPlace.from_dict(item) for item in items]


def save_geoparquet(places: list[PlatialPlace], path: str | pathlib.Path) -> None:
    """Write PlatialPlace records losslessly to a GeoParquet v1.0.0 file.

    Primary geometry is stored as WKB in `geometry` (null for archival-silence places),
    while full competing geometries, fuzzy time, 3-layer platial attributes, and citations
    are preserved in structured columns so round-trip deserialization is lossless.
    """
    out = pathlib.Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    wkb_list: list[bytes | None] = []
    geom_types: set[str] = set()
    bounds_list: list[tuple[float, float, float, float]] = []

    rows: dict[str, list[Any]] = {
        "place_id": [],
        "title": [],
        "fclasses_json": [],
        "earliest_start": [],
        "latest_start": [],
        "earliest_end": [],
        "latest_end": [],
        "absence": [],
        "absence_reason": [],
        "valence": [],
        "dominant_mood": [],
        "provenance": [],
        "full_record_json": [],
    }

    for p in places:
        pg = p.primary_geometry
        if pg is not None and "coordinates" in pg.geometry:
            geom_obj = shape(pg.geometry)
            wkb_list.append(shapely.to_wkb(geom_obj))
            geom_types.add(geom_obj.geom_type)
            bounds_list.append(geom_obj.bounds)
        else:
            wkb_list.append(None)

        rows["place_id"].append(p.place_id)
        rows["title"].append(p.title)
        rows["fclasses_json"].append(json.dumps(list(p.fclasses), ensure_ascii=False))
        rows["earliest_start"].append(p.when.earliest_start if p.when else None)
        rows["latest_start"].append(p.when.latest_start if p.when else None)
        rows["earliest_end"].append(p.when.earliest_end if p.when else None)
        rows["latest_end"].append(p.when.latest_end if p.when else None)
        rows["absence"].append(p.absence.value if p.absence else None)
        rows["absence_reason"].append(p.absence_reason)
        rows["valence"].append(p.platial.affect.valence)
        rows["dominant_mood"].append(p.platial.affect.dominant_mood)
        rows["provenance"].append(p.provenance)
        rows["full_record_json"].append(json.dumps(p.to_dict(), ensure_ascii=False))

    schema = pa.schema(
        [
            ("place_id", pa.string()),
            ("title", pa.string()),
            ("fclasses_json", pa.string()),
            ("earliest_start", pa.float64()),
            ("latest_start", pa.float64()),
            ("earliest_end", pa.float64()),
            ("latest_end", pa.float64()),
            ("absence", pa.string()),
            ("absence_reason", pa.string()),
            ("valence", pa.float64()),
            ("dominant_mood", pa.string()),
            ("provenance", pa.string()),
            ("full_record_json", pa.string()),
            ("geometry", pa.binary()),
        ]
    )

    geo_col_meta: dict[str, Any] = {
        "encoding": "WKB",
        "geometry_types": sorted(geom_types),
    }
    if bounds_list:
        geo_col_meta["bbox"] = [
            min(b[0] for b in bounds_list),
            min(b[1] for b in bounds_list),
            max(b[2] for b in bounds_list),
            max(b[3] for b in bounds_list),
        ]

    geo_meta = {
        "version": "1.0.0",
        "primary_column": "geometry",
        "columns": {"geometry": geo_col_meta},
    }
    schema = schema.with_metadata({b"geo": json.dumps(geo_meta).encode("utf-8")})

    arrays = [pa.array(rows[col], type=schema.field(col).type) for col in rows]
    arrays.append(pa.array(wkb_list, type=pa.binary()))
    table = pa.Table.from_arrays(arrays, schema=schema)
    pq.write_table(table, out)


def load_geoparquet(path: str | pathlib.Path) -> list[PlatialPlace]:
    """Read PlatialPlace records losslessly from a GeoParquet file."""
    table = pq.read_table(pathlib.Path(path))
    if "full_record_json" not in table.column_names:
        raise ValueError(
            "Parquet file is not a PlatialPlace GeoParquet (missing 'full_record_json'). "
            "Use connectors.load_chgis_geoparquet() for CHGIS GeoParquet snapshots."
        )
    col = table["full_record_json"].to_pylist()
    return [PlatialPlace.from_dict(json.loads(item)) for item in col]
