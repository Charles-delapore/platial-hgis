"""D3-P2: Connectors for CHGIS (external path), WHG LPF, PeriodO, CBDB schema, and Cliopatria."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
import pathlib
from typing import Any

import pyarrow.parquet as pq
import shapely
from shapely.geometry import mapping

from .io_lpf import load_lpf
from .primitives import (
    CompetingGeometry,
    EvidenceRef,
    FuzzyInterval,
    PlatialAttributes,
    PlatialPlace,
)

CHGIS_MANDATORY_CITATION = (
    '"CHGIS Version 6." (c) Fairbank Center for Chinese Studies and the '
    "Institute for Chinese Historical Geography at Fudan University, Dec 2016."
)

CBDB_REQUIRED_FIELDS = (
    "cbdb_person_id",
    "name_ch",
    "name_py",
    "dynasty",
    "birth_year",
    "death_year",
    "index_year",
    "birth_place",
    "index_place",
    "entry_method",
    "social_status",
    "source_text",
    "cbdb_release",
    "license_tier",
)

ALLOWED_CBDB_PUBLIC_TIERS = frozenset({"CC BY-NC-SA 4.0 (in-release)"})


def _estimate_chgis_uncertainty_km(lev_rank: Any, geom_type: str, beg_rule: Any = None) -> float:
    """Estimate spatial/contextual uncertainty radius (km) from CHGIS admin level & rule."""
    try:
        rank = int(lev_rank)
    except (TypeError, ValueError):
        rank = 3
    base = {1: 80.0, 2: 35.0, 3: 15.0, 4: 5.0}.get(rank, 15.0)
    if geom_type in {"Polygon", "MultiPolygon"}:
        base *= 0.6
    # CHGIS beg_rule/end_rule: 4 = exact year, 1-3 or 5-6 = fuzzy/inferred
    if beg_rule is not None and str(beg_rule) not in {"4", "4.0"}:
        base *= 1.25
    return round(base, 2)


def load_chgis_geoparquet(
    path: str | pathlib.Path,
    *,
    limit: int | None = None,
    dynasty_filter: str | None = None,
) -> list[PlatialPlace]:
    """Load an external CHGIS GeoParquet snapshot safely via PyArrow + Shapely.

    Avoids geopandas pyproj CRS84 parsing bugs and respects CHGIS V6 EULA by reading
    only from a user-supplied local path without bundling CHGIS data in the package.
    """
    pq_path = pathlib.Path(path)
    if not pq_path.exists():
        raise FileNotFoundError(f"CHGIS GeoParquet file not found: {pq_path}")

    table = pq.read_table(pq_path)
    cols = table.column_names
    rows = table.to_pylist()
    places: list[PlatialPlace] = []

    for row in rows:
        dyn = str(row.get("dynasty") or "")
        if dynasty_filter and dyn.lower() != dynasty_filter.lower():
            continue

        wkb = row.get("geometry")
        if wkb is None:
            continue
        geom_obj = shapely.from_wkb(wkb)
        geojson_geom = mapping(geom_obj)

        sys_id = str(row.get("sys_id") or row.get("SYS_ID") or len(places))
        name_ch = str(row.get("name_ch") or row.get("NAME_CH") or "")
        name_py = str(row.get("name_py") or row.get("NAME_PY") or "")
        name_ft = str(row.get("name_ft") or row.get("NAME_FT") or "")
        type_ch = str(row.get("type_ch") or row.get("TYPE_CH") or "")
        lev_rank = row.get("lev_rank", row.get("LEV_RANK", 3))
        beg_yr = row.get("beg_yr", row.get("BEG_YR"))
        end_yr = row.get("end_yr", row.get("END_YR"))
        snap_yr = row.get("snapshot_year")

        when_obj: FuzzyInterval | None = None
        if beg_yr is not None and end_yr is not None:
            b, e = float(beg_yr), float(end_yr)
            if b <= e:
                when_obj = FuzzyInterval.from_crisp(b, e, label=dyn or None)

        ev = EvidenceRef(
            source_id=f"chgis:v6:{sys_id}",
            label=CHGIS_MANDATORY_CITATION,
            uri="https://dataverse.harvard.edu/dataverse/chgis_v6",
            evidence_level="verified",
            locator=f"sys_id={sys_id}" + (f", snapshot_year={snap_yr}" if snap_yr else ""),
        )
        radius = _estimate_chgis_uncertainty_km(lev_rank, geom_obj.geom_type)
        names = []
        if name_ch:
            names.append({"toponym": name_ch, "lang": "zh-Hans"})
        if name_ft and name_ft != name_ch:
            names.append({"toponym": name_ft, "lang": "zh-Hant"})
        if name_py:
            names.append({"toponym": name_py, "lang": "zh-Latn-pinyin"})

        places.append(
            PlatialPlace(
                place_id=f"chgis:{sys_id}" + (f":{snap_yr}" if snap_yr else ""),
                title=name_ch or name_py or sys_id,
                fclasses=("A",),
                names=names,
                when=when_obj,
                geometries=[
                    CompetingGeometry(
                        hypothesis_id=f"chgis-v6-{sys_id}",
                        geometry=geojson_geom,
                        weight=1.0,
                        evidence=(ev,),
                        uncertainty_radius_km=radius,
                        certainty="certain",
                    )
                ],
                platial=PlatialAttributes(
                    location={
                        "dynasty": dyn,
                        "lev_rank": lev_rank,
                        "type_ch": type_ch,
                        "snapshot_year": snap_yr,
                        "columns_present": len(cols),
                    },
                    locale={"admin_type": type_ch, "fclasses": ["A"]},
                ),
                evidence=[ev],
                ccodes=["CN"],
                provenance="chgis_v6_external",
            )
        )
        if limit is not None and len(places) >= limit:
            break
    return places


def load_chgis_shapefile_zip(
    path: str | pathlib.Path,
    *,
    limit: int | None = None,
) -> list[PlatialPlace]:
    """Load an external CHGIS V6 shapefile .zip (e.g. v6_time_pref_pts_utf_wgs84.zip)."""
    import geopandas as gpd

    zip_path = pathlib.Path(path)
    if not zip_path.exists():
        raise FileNotFoundError(f"CHGIS shapefile zip not found: {zip_path}")

    gdf = gpd.read_file(f"zip://{zip_path}")
    places: list[PlatialPlace] = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        sys_id = str(row.get("SYS_ID") or idx)
        name_ch = str(row.get("NAME_CH") or "")
        name_ft = str(row.get("NAME_FT") or "")
        name_py = str(row.get("NAME_PY") or "")
        type_ch = str(row.get("TYPE_CH") or "")
        pres_loc = str(row.get("PRES_LOC") or "")
        lev_rank = row.get("LEV_RANK", 3)
        beg_yr = row.get("BEG_YR")
        end_yr = row.get("END_YR")
        beg_rule = row.get("BEG_RULE")

        when_obj = None
        if beg_yr is not None and end_yr is not None:
            try:
                b, e = float(beg_yr), float(end_yr)
                if b <= e and b > -5000 and e < 3000:
                    when_obj = FuzzyInterval.from_crisp(b, e)
            except (TypeError, ValueError):
                when_obj = None

        ev = EvidenceRef(
            source_id=f"chgis:v6:{sys_id}",
            label=CHGIS_MANDATORY_CITATION,
            uri="https://dataverse.harvard.edu/dataverse/chgis_v6",
            evidence_level="verified",
            locator=f"SYS_ID={sys_id}, GEO_SRC={row.get('GEO_SRC', '')}",
        )
        names = []
        if name_ch:
            names.append({"toponym": name_ch, "lang": "zh-Hans"})
        if name_ft and name_ft != name_ch:
            names.append({"toponym": name_ft, "lang": "zh-Hant"})
        if name_py:
            names.append({"toponym": name_py, "lang": "zh-Latn-pinyin"})

        places.append(
            PlatialPlace(
                place_id=f"chgis:pt:{sys_id}",
                title=name_ch or name_py or sys_id,
                fclasses=("A", "P"),
                names=names,
                when=when_obj,
                geometries=[
                    CompetingGeometry(
                        hypothesis_id=f"chgis-pt-{sys_id}",
                        geometry=mapping(geom),
                        weight=1.0,
                        evidence=(ev,),
                        uncertainty_radius_km=_estimate_chgis_uncertainty_km(
                            lev_rank, geom.geom_type, beg_rule
                        ),
                        certainty="certain" if str(beg_rule) in {"4", "4.0"} else "uncertain",
                    )
                ],
                platial=PlatialAttributes(
                    location={
                        "pres_loc": pres_loc,
                        "lev_rank": int(lev_rank) if str(lev_rank).isdigit() else lev_rank,
                        "type_ch": type_ch,
                        "beg_chg_ty": str(row.get("BEG_CHG_TY") or ""),
                        "end_chg_ty": str(row.get("END_CHG_TY") or ""),
                    },
                    locale={"admin_type": type_ch, "fclasses": ["A", "P"]},
                ),
                evidence=[ev],
                ccodes=["CN"],
                provenance="chgis_v6_external",
            )
        )
        if limit is not None and len(places) >= limit:
            break
    return places


def load_whg_lpf(path: str | pathlib.Path) -> list[PlatialPlace]:
    """Load a WHG Entity API JSON or LPF FeatureCollection."""
    return load_lpf(path, strict_v13=False)


def load_periodo_json(path: str | pathlib.Path) -> dict[str, Any]:
    """Load a PeriodO JSON-LD period definition and parse its FuzzyInterval + spatial coverage."""
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    interval = FuzzyInterval.from_periodo(data)
    return {
        "id": data.get("id"),
        "label": data.get("label"),
        "authority": data.get("authority"),
        "interval": interval,
        "spatial_coverage": data.get("spatialCoverage", []),
        "spatial_description": data.get("spatialCoverageDescription"),
        "source": data.get("source"),
    }


def load_cbdb_sources_inventory(path: str | pathlib.Path) -> list[dict[str, str]]:
    """Load the public CBDB Sources inventory CSV (bibliography metadata, zero person rows)."""
    with pathlib.Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class CBDBLicenseError(ValueError):
    """Raised when a CBDB record violates licensing boundaries or lacks primary citation."""


@dataclass(frozen=True)
class CBDBSchemaValidator:
    """Validates schema-compliant CBDB sample rows per cbdb-sample-schema-template.md.

    Strictly enforces:
      - Required template columns present
      - Non-empty `source_text` (original primary historical source)
      - Non-empty `cbdb_release` (e.g., CBDB_bi_20250520 or CBDB_BJ_20260602)
      - Rejects out-of-release records (`CBDB-2026-terms`) from public/redistributable exports
    """

    allow_out_of_release: bool = False

    def validate_row(self, row: dict[str, Any]) -> None:
        missing = [k for k in CBDB_REQUIRED_FIELDS if k not in row]
        if missing:
            raise CBDBLicenseError(f"CBDB row missing required schema fields: {missing}")
        if not str(row.get("source_text", "")).strip():
            raise CBDBLicenseError("CBDB row missing mandatory 'source_text' citation")
        if not str(row.get("cbdb_release", "")).strip():
            raise CBDBLicenseError("CBDB row missing mandatory 'cbdb_release' version anchor")
        tier = str(row.get("license_tier", "")).strip()
        if not self.allow_out_of_release and tier not in ALLOWED_CBDB_PUBLIC_TIERS:
            raise CBDBLicenseError(
                f"CBDB record license_tier {tier!r} is not permitted for public export; "
                f"only {sorted(ALLOWED_CBDB_PUBLIC_TIERS)} allowed under 2026-08-20 terms."
            )


def load_cliopatria_geojson(
    path: str | pathlib.Path,
    *,
    year: int | None = None,
    polity_name: str | None = None,
    limit: int | None = None,
) -> list[PlatialPlace]:
    """Load external Cliopatria (Seshat) GeoJSON polities (CC BY 4.0)."""
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    features = data.get("features", [])
    places: list[PlatialPlace] = []
    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        name = str(props.get("Name") or "")
        from_yr = props.get("FromYear")
        to_yr = props.get("ToYear")
        if polity_name and polity_name.lower() not in name.lower():
            continue
        if year is not None and from_yr is not None and to_yr is not None:
            if not (int(from_yr) <= year <= int(to_yr)):
                continue

        geom = feat.get("geometry")
        if not geom:
            continue
        when_obj = (
            FuzzyInterval.from_crisp(float(from_yr), float(to_yr), label=name)
            if from_yr is not None and to_yr is not None and float(from_yr) <= float(to_yr)
            else None
        )
        wd = props.get("Wikidata")
        seshat_id = props.get("SeshatID")
        ev = EvidenceRef(
            source_id=f"cliopatria:{seshat_id or idx}",
            label="Cliopatria / Seshat Global History Databank (CC BY 4.0)",
            uri="https://zenodo.org/records/13363121",
            evidence_level="verified",
            locator=f"Name={name}, Years={from_yr}..{to_yr}",
        )
        links = []
        if wd:
            links.append({"type": "closeMatch", "identifier": f"http://www.wikidata.org/entity/{wd}"})
        places.append(
            PlatialPlace(
                place_id=f"cliopatria:{idx}:{name}",
                title=name or f"polity-{idx}",
                fclasses=("A",),
                names=[{"toponym": name, "lang": "en"}],
                when=when_obj,
                geometries=[
                    CompetingGeometry(
                        hypothesis_id=f"cliopatria-{idx}",
                        geometry=geom,
                        weight=1.0,
                        evidence=(ev,),
                        uncertainty_radius_km=50.0,
                        certainty="uncertain",
                    )
                ],
                platial=PlatialAttributes(
                    location={
                        "area_km2": props.get("Area"),
                        "polity_type": props.get("Type"),
                        "seshat_id": seshat_id,
                    },
                    locale={"fclasses": ["A"], "entity_type": props.get("Type", "POLITY")},
                ),
                evidence=[ev],
                links=links,
                provenance="cliopatria_cc_by_4",
            )
        )
        if limit is not None and len(places) >= limit:
            break
    return places
