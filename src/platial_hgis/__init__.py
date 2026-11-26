"""Platial-HGIS: Evidence-bound platial and fuzzy spatiotemporal historical GIS engine."""

from .affect_field import AffectiveField, AffectSample
from .annotations import SVGMapAnnotation, build_svg_polygon, parse_svg_polygon_points
from .cases import (
    run_case_grand_canal_narrative,
    run_case_silk_road_contested,
    run_case_tang_song_poets,
)
from .connectors import (
    CBDBLicenseError,
    CBDBSchemaValidator,
    load_cbdb_sources_inventory,
    load_chgis_geoparquet,
    load_chgis_shapefile_zip,
    load_cliopatria_geojson,
    load_periodo_json,
    load_whg_lpf,
)
from .cooccurrence import CooccurrenceEdge, TrajectoryEvent, mine_cooccurrence_network
from .disambiguate import CrossDynastyDisambiguator, DisambiguationCandidate
from .gazetteer import GazetteerIndex, duckdb_available
from .georef import (
    GroundControlPoint,
    HistoricalMapSpec,
    NonDistortingBridge,
    parse_allmaps_annotation,
    parse_maplat_standard,
)
from .io_geoparquet import load_geoparquet, load_json, save_geoparquet, save_json
from .io_lpf import LPFValidationError, load_lpf, save_lpf, validate_lpf
from .narrative import (
    CameraSpec,
    NarrativeScene,
    NarrativeStoryboard,
    NarrativeValidationError,
    load_storyboard,
    parse_storyboard_dict,
)
from .narrative_html import compile_narrative_html
from .primitives import (
    AbsenceState,
    AffectLayer,
    CompetingGeometry,
    EvidenceRef,
    FuzzyInterval,
    PlatialAttributes,
    PlatialPlace,
    normalize_hypothesis_weights,
)
from .provenance import DualTrackRecord, ProvenanceLedger, RevisionEntry, SpatialAnchor
from .reasoning import AllenProbabilities, allen_probabilities
from .review_html import generate_review_html

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "AbsenceState",
    "AffectLayer",
    "AffectSample",
    "AffectiveField",
    "AllenProbabilities",
    "CBDBLicenseError",
    "CBDBSchemaValidator",
    "CameraSpec",
    "CompetingGeometry",
    "CooccurrenceEdge",
    "CrossDynastyDisambiguator",
    "DisambiguationCandidate",
    "DualTrackRecord",
    "EvidenceRef",
    "FuzzyInterval",
    "GazetteerIndex",
    "GroundControlPoint",
    "HistoricalMapSpec",
    "LPFValidationError",
    "NarrativeScene",
    "NarrativeStoryboard",
    "NarrativeValidationError",
    "NonDistortingBridge",
    "PlatialAttributes",
    "PlatialPlace",
    "ProvenanceLedger",
    "RevisionEntry",
    "SVGMapAnnotation",
    "SpatialAnchor",
    "TrajectoryEvent",
    "allen_probabilities",
    "build_svg_polygon",
    "compile_narrative_html",
    "duckdb_available",
    "generate_review_html",
    "load_cbdb_sources_inventory",
    "load_chgis_geoparquet",
    "load_chgis_shapefile_zip",
    "load_cliopatria_geojson",
    "load_geoparquet",
    "load_json",
    "load_lpf",
    "load_periodo_json",
    "load_storyboard",
    "load_whg_lpf",
    "mine_cooccurrence_network",
    "normalize_hypothesis_weights",
    "parse_allmaps_annotation",
    "parse_maplat_standard",
    "parse_storyboard_dict",
    "parse_svg_polygon_points",
    "run_case_grand_canal_narrative",
    "run_case_silk_road_contested",
    "run_case_tang_song_poets",
    "save_geoparquet",
    "save_json",
    "save_lpf",
    "validate_lpf",
]
