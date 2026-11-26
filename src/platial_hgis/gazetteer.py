"""D3-P2: Local SQLite FTS5 spatiotemporal gazetteer index with optional DuckDB adapter."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
from typing import Any

from .primitives import FuzzyInterval, PlatialPlace


def duckdb_available() -> bool:
    """Return True if the optional `duckdb` package is installed."""
    return importlib.util.find_spec("duckdb") is not None


class GazetteerIndex:
    """Local SQLite + FTS5 index for multi-source historical gazetteers & periods.

    Primary engine is SQLite 3 with FTS5 (stdlib, guaranteed offline). If `duckdb` is
    installed, `query_geoparquet_duckdb()` can also execute analytical SQL over Parquet.
    """

    def __init__(self, db_path: str | pathlib.Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS places (
                place_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                all_names TEXT NOT NULL,
                dynasty TEXT,
                admin_type TEXT,
                lev_rank INTEGER,
                parent_id TEXT,
                earliest_start REAL,
                latest_start REAL,
                earliest_end REAL,
                latest_end REAL,
                lon REAL,
                lat REAL,
                uncertainty_radius_km REAL,
                absence TEXT,
                provenance TEXT,
                record_json TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS places_fts USING fts5(
                place_id UNINDEXED,
                title,
                all_names,
                dynasty,
                admin_type,
                tokenize = 'unicode61'
            );

            CREATE TABLE IF NOT EXISTS periods (
                periodo_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                earliest_start REAL NOT NULL,
                latest_start REAL NOT NULL,
                earliest_end REAL NOT NULL,
                latest_end REAL NOT NULL,
                spatial_desc TEXT,
                record_json TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "GazetteerIndex":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @staticmethod
    def _extract_centroid(place: PlatialPlace) -> tuple[float | None, float | None, float]:
        pg = place.primary_geometry
        if pg is None:
            return None, None, 0.0
        g = pg.geometry
        gtype = g.get("type")
        coords = g.get("coordinates")
        if gtype == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return float(coords[0]), float(coords[1]), pg.uncertainty_radius_km
        try:
            from shapely.geometry import shape

            c = shape(g).centroid
            return float(c.x), float(c.y), pg.uncertainty_radius_km
        except Exception:
            return None, None, pg.uncertainty_radius_km

    def add_places(self, places: list[PlatialPlace]) -> int:
        """Index a batch of PlatialPlace records into SQLite + FTS5."""
        cur = self.conn.cursor()
        count = 0
        for p in places:
            name_tokens = [p.title] + [str(n.get("toponym", "")) for n in p.names if n.get("toponym")]
            # Preserve CJK substrings by also space-separating unique tokens
            all_names = " | ".join(dict.fromkeys(t for t in name_tokens if t))
            loc = p.platial.location
            dynasty = str(loc.get("dynasty") or "")
            admin_type = str(loc.get("type_ch") or p.platial.locale.get("admin_type") or "")
            lev_raw = loc.get("lev_rank")
            lev_rank = int(lev_raw) if isinstance(lev_raw, (int, float)) or str(lev_raw).isdigit() else None
            parent_id = str(loc.get("parent_id") or "")

            es = p.when.earliest_start if p.when else None
            ls = p.when.latest_start if p.when else None
            ee = p.when.earliest_end if p.when else None
            le = p.when.latest_end if p.when else None
            lon, lat, rad = self._extract_centroid(p)
            rec_json = json.dumps(p.to_dict(), ensure_ascii=False)

            cur.execute("DELETE FROM places_fts WHERE place_id = ?", (p.place_id,))
            cur.execute(
                """
                INSERT OR REPLACE INTO places (
                    place_id, title, all_names, dynasty, admin_type, lev_rank, parent_id,
                    earliest_start, latest_start, earliest_end, latest_end,
                    lon, lat, uncertainty_radius_km, absence, provenance, record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p.place_id,
                    p.title,
                    all_names,
                    dynasty,
                    admin_type,
                    lev_rank,
                    parent_id,
                    es,
                    ls,
                    ee,
                    le,
                    lon,
                    lat,
                    rad,
                    p.absence.value if p.absence else None,
                    p.provenance,
                    rec_json,
                ),
            )
            cur.execute(
                "INSERT INTO places_fts (place_id, title, all_names, dynasty, admin_type) VALUES (?, ?, ?, ?, ?)",
                (p.place_id, p.title, all_names, dynasty, admin_type),
            )
            count += 1
        self.conn.commit()
        return count

    def add_period(self, periodo_record: dict[str, Any]) -> None:
        """Index a parsed PeriodO record."""
        iv: FuzzyInterval = periodo_record["interval"]
        self.conn.execute(
            """
            INSERT OR REPLACE INTO periods (
                periodo_id, label, earliest_start, latest_start, earliest_end, latest_end,
                spatial_desc, record_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(periodo_record.get("id") or iv.periodo_id or iv.label),
                str(periodo_record.get("label") or iv.label or ""),
                iv.earliest_start,
                iv.latest_start,
                iv.earliest_end,
                iv.latest_end,
                str(periodo_record.get("spatial_description") or ""),
                json.dumps(
                    {k: (v.to_dict() if isinstance(v, FuzzyInterval) else v) for k, v in periodo_record.items()},
                    ensure_ascii=False,
                ),
            ),
        )
        self.conn.commit()

    def count_places(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM places").fetchone()
        return int(row["c"])

    def search(
        self,
        query: str,
        *,
        year_start: float | None = None,
        year_end: float | None = None,
        dynasty: str | None = None,
        limit: int = 20,
    ) -> list[PlatialPlace]:
        """Search indexed places using SQLite FTS5 with LIKE fallback for CJK substrings."""
        q_clean = query.strip()
        if not q_clean:
            return []

        params: list[Any] = []
        where_clauses: list[str] = []

        if year_start is not None and year_end is not None:
            where_clauses.append(
                "(p.earliest_start IS NULL OR (p.latest_end >= ? AND p.earliest_start <= ?))"
            )
            params.extend([year_start, year_end])
        elif year_start is not None:
            where_clauses.append(
                "(p.earliest_start IS NULL OR (p.latest_end >= ? AND p.earliest_start <= ?))"
            )
            params.extend([year_start, year_start])

        if dynasty:
            where_clauses.append("LOWER(p.dynasty) = LOWER(?)")
            params.append(dynasty)

        extra_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""

        # Try FTS5 match first
        fts_term = '"' + q_clean.replace('"', '""') + '"'
        try:
            sql_fts = f"""
                SELECT p.record_json
                FROM places_fts f
                JOIN places p ON p.place_id = f.place_id
                WHERE places_fts MATCH ? {extra_sql}
                ORDER BY bm25(places_fts)
                LIMIT ?
            """
            rows = self.conn.execute(sql_fts, [fts_term, *params, limit]).fetchall()
        except sqlite3.OperationalError:
            rows = []

        # Substring fallback (essential for CJK partial names like "高平" matching "高平郡")
        if len(rows) < limit:
            seen_ids: set[str] = set()
            results: list[PlatialPlace] = []
            for r in rows:
                pl = PlatialPlace.from_dict(json.loads(r["record_json"]))
                seen_ids.add(pl.place_id)
                results.append(pl)

            like_pat = f"%{q_clean}%"
            sql_like = f"""
                SELECT p.record_json
                FROM places p
                WHERE (p.title LIKE ? OR p.all_names LIKE ?) {extra_sql}
                LIMIT ?
            """
            like_rows = self.conn.execute(
                sql_like, [like_pat, like_pat, *params, limit * 2]
            ).fetchall()
            for r in like_rows:
                pl = PlatialPlace.from_dict(json.loads(r["record_json"]))
                if pl.place_id not in seen_ids:
                    seen_ids.add(pl.place_id)
                    results.append(pl)
                if len(results) >= limit:
                    break
            return results

        return [PlatialPlace.from_dict(json.loads(r["record_json"])) for r in rows]

    @staticmethod
    def query_geoparquet_duckdb(path: str | pathlib.Path, sql_where: str = "1=1", limit: int = 50) -> list[dict[str, Any]]:
        """Optional DuckDB analytical query over a Parquet file if duckdb is installed."""
        if not duckdb_available():
            raise RuntimeError(
                "Optional dependency 'duckdb' is not installed in this offline environment; "
                "use GazetteerIndex (SQLite FTS5) or connectors.load_chgis_geoparquet() instead."
            )
        import duckdb  # type: ignore[import-not-found]

        con = duckdb.connect(":memory:")
        try:
            rel = con.execute(
                f"SELECT * EXCLUDE (geometry) FROM read_parquet(?) WHERE {sql_where} LIMIT ?",
                [str(path), limit],
            )
            cols = [d[0] for d in rel.description]
            return [dict(zip(cols, row)) for row in rel.fetchall()]
        finally:
            con.close()
