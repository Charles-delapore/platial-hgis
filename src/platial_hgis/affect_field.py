"""D3-P4: Spatial emotional valence, dispersion, and atmospheric mood field modeling."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Any

from .georef import haversine_m
from .primitives import PlatialPlace


@dataclass(frozen=True)
class AffectSample:
    """A georeferenced affective observation with valence, arousal, mood, and confidence."""

    place_id: str
    title: str
    lon: float
    lat: float
    valence: float
    arousal: float
    dominant_mood: str
    weight: float = 1.0


def extract_affect_samples(places: list[PlatialPlace]) -> list[AffectSample]:
    """Extract georeferenced AffectSamples from a collection of PlatialPlace objects."""
    samples: list[AffectSample] = []
    for p in places:
        pg = p.primary_geometry
        if pg is None:
            continue
        geom = pg.geometry
        if geom.get("type") == "Point":
            lon, lat = float(geom["coordinates"][0]), float(geom["coordinates"][1])
        else:
            from shapely.geometry import shape

            c = shape(geom).centroid
            lon, lat = float(c.x), float(c.y)

        aff = p.platial.affect
        samples.append(
            AffectSample(
                place_id=p.place_id,
                title=p.title,
                lon=lon,
                lat=lat,
                valence=aff.valence,
                arousal=aff.arousal,
                dominant_mood=aff.dominant_mood,
                weight=max(0.1, pg.weight),
            )
        )
    return samples


class AffectiveField:
    """Kernel-smoothed spatial field of emotional valence, arousal, and mood dispersion."""

    def __init__(self, samples: list[AffectSample], *, bandwidth_km: float = 250.0) -> None:
        if not samples:
            raise ValueError("AffectiveField requires at least one georeferenced AffectSample")
        if bandwidth_km <= 0:
            raise ValueError("bandwidth_km must be positive")
        self.samples = list(samples)
        self.bandwidth_km = float(bandwidth_km)

    @classmethod
    def from_places(cls, places: list[PlatialPlace], *, bandwidth_km: float = 250.0) -> "AffectiveField":
        return cls(extract_affect_samples(places), bandwidth_km=bandwidth_km)

    def evaluate(self, lon: float, lat: float) -> dict[str, Any]:
        """Evaluate local smoothed valence, arousal, emotional dispersion, and dominant mood."""
        weights: list[float] = []
        valences: list[float] = []
        arousals: list[float] = []
        mood_weights: Counter[str] = Counter()

        for s in self.samples:
            d_km = haversine_m(lon, lat, s.lon, s.lat) / 1000.0
            k = math.exp(-0.5 * ((d_km / self.bandwidth_km) ** 2))
            w = s.weight * k
            weights.append(w)
            valences.append(s.valence)
            arousals.append(s.arousal)
            mood_weights[s.dominant_mood] += w

        w_sum = sum(weights)
        if w_sum <= 1e-12:
            return {
                "lon": lon,
                "lat": lat,
                "valence": 0.0,
                "arousal": 0.0,
                "dispersion": 0.0,
                "dominant_mood": "unobserved",
                "effective_support": 0.0,
            }

        mean_v = sum(w * v for w, v in zip(weights, valences)) / w_sum
        mean_a = sum(w * a for w, a in zip(weights, arousals)) / w_sum
        var_v = sum(w * ((v - mean_v) ** 2) for w, v in zip(weights, valences)) / w_sum
        dispersion = math.sqrt(max(0.0, var_v))
        top_mood = mood_weights.most_common(1)[0][0]

        return {
            "lon": round(lon, 5),
            "lat": round(lat, 5),
            "valence": round(mean_v, 4),
            "arousal": round(mean_a, 4),
            "dispersion": round(dispersion, 4),
            "dominant_mood": top_mood,
            "effective_support": round(w_sum, 4),
        }

    def sample_grid(
        self,
        *,
        nx: int = 8,
        ny: int = 6,
        pad_deg: float = 0.5,
    ) -> dict[str, Any]:
        """Generate a regular GeoJSON FeatureCollection grid of affective field cells."""
        lons = [s.lon for s in self.samples]
        lats = [s.lat for s in self.samples]
        min_lon, max_lon = min(lons) - pad_deg, max(lons) + pad_deg
        min_lat, max_lat = min(lats) - pad_deg, max(lats) + pad_deg

        features: list[dict[str, Any]] = []
        for iy in range(ny):
            lat = min_lat + (max_lat - min_lat) * (iy / max(1, ny - 1))
            for ix in range(nx):
                lon = min_lon + (max_lon - min_lon) * (ix / max(1, nx - 1))
                cell = self.evaluate(lon, lat)
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [cell["lon"], cell["lat"]]},
                        "properties": {
                            "valence": cell["valence"],
                            "arousal": cell["arousal"],
                            "dispersion": cell["dispersion"],
                            "dominant_mood": cell["dominant_mood"],
                            "effective_support": cell["effective_support"],
                        },
                    }
                )
        return {
            "type": "FeatureCollection",
            "metadata": {
                "bandwidth_km": self.bandwidth_km,
                "sample_count": len(self.samples),
                "grid": [nx, ny],
            },
            "features": features,
        }
