"""D3-P3: SVG region annotations on IIIF historical canvases bound to historical evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .georef import NonDistortingBridge
from .primitives import EvidenceRef


def parse_svg_polygon_points(svg_fragment: str) -> list[tuple[float, float]]:
    """Extract vertex coordinates from an SVG `<polygon points="...">` or `<rect>` selector."""
    poly_match = re.search(r'points\s*=\s*"([^"]+)"', svg_fragment)
    if poly_match:
        pts: list[tuple[float, float]] = []
        raw_tokens = re.split(r"\s+", poly_match.group(1).strip())
        for tok in raw_tokens:
            if "," in tok:
                xs, ys = tok.split(",", 1)
                pts.append((float(xs), float(ys)))
        if len(pts) >= 3:
            return pts

    rect_match = re.search(
        r'<rect[^>]*x="([^"]+)"[^>]*y="([^"]+)"[^>]*width="([^"]+)"[^>]*height="([^"]+)"',
        svg_fragment,
    )
    if rect_match:
        x, y, w, h = (float(rect_match.group(i)) for i in range(1, 5))
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

    raise ValueError("Could not extract polygon or rect vertices from SVG selector")


def build_svg_polygon(
    vertices: list[tuple[float, float]],
    *,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """Serialize pixel vertices as an IIIF-compliant `<svg><polygon .../></svg>` selector."""
    pts_str = " ".join(f"{round(x, 2)},{round(y, 2)}" for x, y in vertices)
    dims = ""
    if width is not None and height is not None:
        dims = f' width="{width}" height="{height}"'
    return f'<svg{dims}><polygon points="{pts_str}" /></svg>'


@dataclass(frozen=True)
class SVGMapAnnotation:
    """An evidence-bound SVG region annotation on a historical map IIIF canvas."""

    annotation_id: str
    canvas_id: str
    label: str
    svg_selector: str
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)
    place_id: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError(
                f"SVGMapAnnotation {self.annotation_id!r} must bind at least one EvidenceRef"
            )
        # Validate SVG geometry eagerly
        parse_svg_polygon_points(self.svg_selector)

    def pixel_vertices(self) -> list[tuple[float, float]]:
        return parse_svg_polygon_points(self.svg_selector)

    def to_wgs84_geojson_feature(self, bridge: NonDistortingBridge) -> dict[str, Any]:
        """Project the SVG region into a modern WGS84 GeoJSON Polygon via NonDistortingBridge."""
        ring = [list(bridge.pixel_to_lonlat(x, y)) for x, y in self.pixel_vertices()]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        return {
            "type": "Feature",
            "id": self.annotation_id,
            "properties": {
                "label": self.label,
                "canvas_id": self.canvas_id,
                "place_id": self.place_id,
                "evidence": [e.to_dict() for e in self.evidence],
                "notes": self.notes,
                "bridge_method": bridge.method,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring],
            },
        }

    def to_w3c_web_annotation(self) -> dict[str, Any]:
        """Export as W3C Web Annotation Data Model JSON-LD."""
        return {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": self.annotation_id,
            "type": "Annotation",
            "motivation": "tagging",
            "target": {
                "type": "SpecificResource",
                "source": self.canvas_id,
                "selector": {
                    "type": "SvgSelector",
                    "value": self.svg_selector,
                },
            },
            "body": {
                "type": "TextualBody",
                "value": self.label,
                "place_id": self.place_id,
                "evidence": [e.to_dict() for e in self.evidence],
                "notes": self.notes,
            },
        }
