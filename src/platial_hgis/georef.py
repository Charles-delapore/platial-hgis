"""D3-P3: Allmaps/Maplat parsers and non-distorting bidirectional coordinate bridge (TPS & TIN)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import pathlib
from typing import Any

import numpy as np
from scipy.spatial import Delaunay

EARTH_RADIUS_M = 6378137.0


def lonlat_to_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Convert WGS84 (lon, lat) in degrees to Web Mercator (EPSG:3857) meters."""
    x = EARTH_RADIUS_M * math.radians(lon)
    lat_clamped = max(-85.05112878, min(85.05112878, lat))
    y = EARTH_RADIUS_M * math.log(math.tan(math.pi / 4.0 + math.radians(lat_clamped) / 2.0))
    return x, y


def mercator_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator (EPSG:3857) meters to WGS84 (lon, lat) in degrees."""
    lon = math.degrees(x / EARTH_RADIUS_M)
    lat = math.degrees(2.0 * math.atan(math.exp(y / EARTH_RADIUS_M)) - math.pi / 2.0)
    return lon, lat


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in meters between two WGS84 points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * 6371008.8 * math.asin(min(1.0, math.sqrt(a)))


@dataclass(frozen=True)
class GroundControlPoint:
    """Single pixel <-> WGS84 ground control point."""

    pixel_x: float
    pixel_y: float
    lon: float
    lat: float
    gcp_id: str | None = None


@dataclass(frozen=True)
class HistoricalMapSpec:
    """Parsed metadata and GCPs from an Allmaps Web Annotation or Maplat JSON."""

    map_id: str
    title: str
    width: int
    height: int
    gcps: tuple[GroundControlPoint, ...]
    source_format: str
    iiif_service_id: str | None = None
    svg_mask: str | None = None
    transformation_hint: str = "thinPlateSpline"
    attribution: str | None = None


def parse_allmaps_annotation(path_or_data: str | pathlib.Path | dict[str, Any]) -> HistoricalMapSpec:
    """Parse an Allmaps IIIF Georeference Web Annotation JSON."""
    if isinstance(path_or_data, (str, pathlib.Path)):
        data = json.loads(pathlib.Path(path_or_data).read_text(encoding="utf-8"))
    else:
        data = path_or_data

    target = data.get("target", {})
    source = target.get("source", {})
    selector = target.get("selector", {})
    body = data.get("body", {})

    # Extract title from manifest label if present
    title = str(data.get("id", "allmaps-annotation"))
    part_of = source.get("partOf", [])
    if part_of and isinstance(part_of, list):
        manifest_list = part_of[0].get("partOf", [])
        if manifest_list and isinstance(manifest_list, list):
            lbl = manifest_list[0].get("label", {})
            if isinstance(lbl, dict):
                for vals in lbl.values():
                    if isinstance(vals, list) and vals:
                        title = str(vals[0])
                        break

    gcps: list[GroundControlPoint] = []
    for idx, feat in enumerate(body.get("features", [])):
        props = feat.get("properties", {})
        rc = props.get("resourceCoords")
        coords = feat.get("geometry", {}).get("coordinates")
        if rc and coords and len(rc) >= 2 and len(coords) >= 2:
            gcps.append(
                GroundControlPoint(
                    pixel_x=float(rc[0]),
                    pixel_y=float(rc[1]),
                    lon=float(coords[0]),
                    lat=float(coords[1]),
                    gcp_id=f"gcp-{idx}",
                )
            )
    if len(gcps) < 3:
        raise ValueError(f"Allmaps annotation requires at least 3 GCPs, got {len(gcps)}")

    tf_type = str(body.get("transformation", {}).get("type", "thinPlateSpline"))
    return HistoricalMapSpec(
        map_id=str(data.get("id", "allmaps-map")),
        title=title,
        width=int(source.get("width", 0)),
        height=int(source.get("height", 0)),
        gcps=tuple(gcps),
        source_format="allmaps_web_annotation",
        iiif_service_id=source.get("id"),
        svg_mask=selector.get("value") if selector.get("type") == "SvgSelector" else None,
        transformation_hint=tf_type,
        attribution="Allmaps Georeference Annotation (CC0)",
    )


def parse_maplat_standard(path_or_data: str | pathlib.Path | dict[str, Any]) -> HistoricalMapSpec:
    """Parse a Maplat standard-format JSON (`gcps`: [[imgX, imgY], [mercX, mercY]])."""
    if isinstance(path_or_data, (str, pathlib.Path)):
        data = json.loads(pathlib.Path(path_or_data).read_text(encoding="utf-8"))
    else:
        data = path_or_data

    gcps: list[GroundControlPoint] = []
    for idx, pair in enumerate(data.get("gcps", [])):
        img_xy, merc_xy = pair[0], pair[1]
        lon, lat = mercator_to_lonlat(float(merc_xy[0]), float(merc_xy[1]))
        gcps.append(
            GroundControlPoint(
                pixel_x=float(img_xy[0]),
                pixel_y=float(img_xy[1]),
                lon=lon,
                lat=lat,
                gcp_id=f"maplat-gcp-{idx}",
            )
        )
    if len(gcps) < 3:
        raise ValueError(f"Maplat standard JSON requires at least 3 GCPs, got {len(gcps)}")

    return HistoricalMapSpec(
        map_id=str(data.get("url") or data.get("title") or "maplat-map"),
        title=str(data.get("title", "Maplat Historical Map")),
        width=int(data.get("width", 0)),
        height=int(data.get("height", 0)),
        gcps=tuple(gcps),
        source_format="maplat_standard",
        transformation_hint="tin",
        attribution=data.get("attr"),
    )


def _tps_kernel(r: np.ndarray) -> np.ndarray:
    """Thin-plate spline radial basis function U(r) = r^2 * ln(r), with U(0) = 0."""
    out = np.zeros_like(r, dtype=np.float64)
    mask = r > 1e-12
    rm = r[mask]
    out[mask] = (rm ** 2) * np.log(rm)
    return out


class _TPSModel:
    """Normalized 2D Thin-Plate Spline mapping R^2 -> R^2."""

    def __init__(self, src: np.ndarray, dst: np.ndarray, reg: float = 1e-8) -> None:
        self.src_mean = src.mean(axis=0)
        self.src_scale = np.maximum(src.std(axis=0), 1e-9)
        self.dst_mean = dst.mean(axis=0)
        self.dst_scale = np.maximum(dst.std(axis=0), 1e-9)

        s = (src - self.src_mean) / self.src_scale
        d = (dst - self.dst_mean) / self.dst_scale
        self.ctrl = s
        n = s.shape[0]

        diff = s[:, None, :] - s[None, :, :]
        dist = np.sqrt(np.sum(diff ** 2, axis=2))
        K = _tps_kernel(dist) + reg * np.eye(n)
        P = np.hstack([np.ones((n, 1)), s])

        L = np.zeros((n + 3, n + 3), dtype=np.float64)
        L[:n, :n] = K
        L[:n, n:] = P
        L[n:, :n] = P.T

        Y = np.zeros((n + 3, 2), dtype=np.float64)
        Y[:n, :] = d

        # Use least-squares solve for robustness against near-collinear GCPs
        sol, *_ = np.linalg.lstsq(L, Y, rcond=None)
        self.weights = sol[:n, :]
        self.affine = sol[n:, :]

    def predict(self, pts: np.ndarray) -> np.ndarray:
        arr = np.atleast_2d(np.asarray(pts, dtype=np.float64))
        s = (arr - self.src_mean) / self.src_scale
        diff = s[:, None, :] - self.ctrl[None, :, :]
        dist = np.sqrt(np.sum(diff ** 2, axis=2))
        K = _tps_kernel(dist)
        P = np.hstack([np.ones((s.shape[0], 1)), s])
        pred_norm = K @ self.weights + P @ self.affine
        return pred_norm * self.dst_scale + self.dst_mean


class _TINModel:
    """Delaunay triangulation piecewise affine transform (Maplat-style non-distorting TIN)."""

    def __init__(self, src: np.ndarray, dst: np.ndarray) -> None:
        self.src = np.asarray(src, dtype=np.float64)
        self.dst = np.asarray(dst, dtype=np.float64)
        self.tri = Delaunay(self.src)
        self.centroids = self.src[self.tri.simplices].mean(axis=1)
        # Precompute affine matrix for each triangle
        self.affines: list[np.ndarray] = []
        for simp in self.tri.simplices:
            A = np.hstack([self.src[simp], np.ones((3, 1))])
            B = self.dst[simp]
            M, *_ = np.linalg.lstsq(A, B, rcond=None)
            self.affines.append(M)

    def predict(self, pts: np.ndarray) -> np.ndarray:
        arr = np.atleast_2d(np.asarray(pts, dtype=np.float64))
        simp_ids = self.tri.find_simplex(arr)
        out = np.zeros((arr.shape[0], 2), dtype=np.float64)
        for i, sid in enumerate(simp_ids):
            if sid < 0:
                # Nearest triangle extrapolation outside convex hull
                dists = np.sum((self.centroids - arr[i]) ** 2, axis=1)
                sid = int(np.argmin(dists))
            M = self.affines[int(sid)]
            out[i] = np.array([arr[i, 0], arr[i, 1], 1.0]) @ M
        return out


class NonDistortingBridge:
    """Bidirectional pixel <-> WGS84 coordinate bridge without warping the historical raster.

    Supports:
      - `method="tps"`: Thin-Plate Spline with Newton-Raphson inverse refinement for
        homeomorphic bijectivity.
      - `method="tin"`: Delaunay piecewise affine triangulation (Maplat-style).
    """

    def __init__(
        self,
        gcps: list[GroundControlPoint] | tuple[GroundControlPoint, ...],
        *,
        method: str = "tps",
        tps_reg: float = 1e-8,
    ) -> None:
        if len(gcps) < 3:
            raise ValueError("NonDistortingBridge requires at least 3 GCPs")
        if method not in {"tps", "tin"}:
            raise ValueError(f"Unsupported method {method!r}; expected 'tps' or 'tin'")
        self.gcps = tuple(gcps)
        self.method = method
        self.tps_reg = tps_reg

        self._px = np.array([[g.pixel_x, g.pixel_y] for g in self.gcps], dtype=np.float64)
        self._geo = np.array([[g.lon, g.lat] for g in self.gcps], dtype=np.float64)

        if method == "tps":
            self._fwd = _TPSModel(self._px, self._geo, reg=tps_reg)
            self._inv = _TPSModel(self._geo, self._px, reg=tps_reg)
        else:
            self._fwd = _TINModel(self._px, self._geo)
            self._inv = _TINModel(self._geo, self._px)

    @classmethod
    def from_spec(cls, spec: HistoricalMapSpec, *, method: str = "tps") -> "NonDistortingBridge":
        return cls(spec.gcps, method=method)

    def pixel_to_lonlat(self, pixel_x: float, pixel_y: float) -> tuple[float, float]:
        res = self._fwd.predict(np.array([[pixel_x, pixel_y]]))[0]
        return float(res[0]), float(res[1])

    def lonlat_to_pixel(self, lon: float, lat: float, *, refine: bool = True) -> tuple[float, float]:
        guess = self._inv.predict(np.array([[lon, lat]]))[0]
        if not refine or self.method != "tps":
            return float(guess[0]), float(guess[1])

        # Gauss-Newton refinement for exact homeomorphic inverse of forward TPS
        px = guess.copy()
        target = np.array([lon, lat], dtype=np.float64)
        eps = 1e-2
        for _ in range(8):
            f0 = self._fwd.predict(px)[0]
            err = target - f0
            if np.linalg.norm(err) < 1e-11:
                break
            fx = (self._fwd.predict(px + np.array([eps, 0.0]))[0] - f0) / eps
            fy = (self._fwd.predict(px + np.array([0.0, eps]))[0] - f0) / eps
            J = np.column_stack([fx, fy])
            try:
                step = np.linalg.solve(J, err)
            except np.linalg.LinAlgError:
                break
            px = px + step
        return float(px[0]), float(px[1])

    def local_viewport_transform(self, pixel_x: float, pixel_y: float, delta_px: float = 50.0) -> dict[str, float]:
        """Compute Maplat-style local scale (m/px) and rotation (deg) at viewport center."""
        lon0, lat0 = self.pixel_to_lonlat(pixel_x, pixel_y)
        lon_x, lat_x = self.pixel_to_lonlat(pixel_x + delta_px, pixel_y)
        lon_y, lat_y = self.pixel_to_lonlat(pixel_x, pixel_y + delta_px)

        mx0, my0 = lonlat_to_mercator(lon0, lat0)
        mxx, myx = lonlat_to_mercator(lon_x, lat_x)
        mxy, myy = lonlat_to_mercator(lon_y, lat_y)

        vx = np.array([mxx - mx0, myx - my0])
        vy = np.array([mxy - mx0, myy - my0])
        scale_x = float(np.linalg.norm(vx) / delta_px)
        scale_y = float(np.linalg.norm(vy) / delta_px)
        rotation_deg = float(math.degrees(math.atan2(vx[1], vx[0])))
        return {
            "center_lon": lon0,
            "center_lat": lat0,
            "scale_x_m_per_px": round(scale_x, 6),
            "scale_y_m_per_px": round(scale_y, 6),
            "mean_scale_m_per_px": round(0.5 * (scale_x + scale_y), 6),
            "rotation_deg": round(rotation_deg, 4),
        }

    def evaluate_residuals(self) -> dict[str, Any]:
        """Compute in-sample RMSE, round-trip closure error, and LOOCV residuals (m & px)."""
        in_sample_m: list[float] = []
        roundtrip_px: list[float] = []
        loocv_m: list[float] = []
        loocv_px: list[float] = []
        per_gcp: list[dict[str, Any]] = []

        n = len(self.gcps)
        for i, g in enumerate(self.gcps):
            plon, plat = self.pixel_to_lonlat(g.pixel_x, g.pixel_y)
            err_m = haversine_m(g.lon, g.lat, plon, plat)
            in_sample_m.append(err_m)

            rx, ry = self.lonlat_to_pixel(plon, plat)
            rt_err = math.hypot(rx - g.pixel_x, ry - g.pixel_y)
            roundtrip_px.append(rt_err)

            loo_err_m: float | None = None
            loo_err_px: float | None = None
            if n >= 4:
                sub_gcps = [self.gcps[j] for j in range(n) if j != i]
                try:
                    sub = NonDistortingBridge(sub_gcps, method=self.method, tps_reg=self.tps_reg)
                    llon, llat = sub.pixel_to_lonlat(g.pixel_x, g.pixel_y)
                    loo_err_m = haversine_m(g.lon, g.lat, llon, llat)
                    lpx, lpy = sub.lonlat_to_pixel(g.lon, g.lat, refine=False)
                    loo_err_px = math.hypot(lpx - g.pixel_x, lpy - g.pixel_y)
                    loocv_m.append(loo_err_m)
                    loocv_px.append(loo_err_px)
                except Exception:
                    pass

            per_gcp.append(
                {
                    "gcp_id": g.gcp_id or f"gcp-{i}",
                    "in_sample_m": round(err_m, 4),
                    "roundtrip_px": round(rt_err, 6),
                    "loocv_m": round(loo_err_m, 2) if loo_err_m is not None else None,
                    "loocv_px": round(loo_err_px, 2) if loo_err_px is not None else None,
                }
            )

        def _rmse(vals: list[float]) -> float | None:
            if not vals:
                return None
            return round(math.sqrt(sum(v * v for v in vals) / len(vals)), 4)

        return {
            "method": self.method,
            "gcp_count": n,
            "in_sample_rmse_m": _rmse(in_sample_m),
            "roundtrip_rmse_px": _rmse(roundtrip_px),
            "roundtrip_max_px": round(max(roundtrip_px), 6),
            "loocv_rmse_m": _rmse(loocv_m),
            "loocv_rmse_px": _rmse(loocv_px),
            "per_gcp": per_gcp,
        }
