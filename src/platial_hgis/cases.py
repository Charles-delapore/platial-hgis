"""D3-P7: Three one-click offline reproducible historical humanities empirical case packs."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import yaml

from .affect_field import AffectiveField
from .annotations import SVGMapAnnotation
from .connectors import load_chgis_geoparquet, load_periodo_json, load_whg_lpf
from .cooccurrence import TrajectoryEvent, mine_cooccurrence_network
from .disambiguate import CrossDynastyDisambiguator
from .gazetteer import GazetteerIndex
from .georef import NonDistortingBridge, parse_allmaps_annotation, parse_maplat_standard
from .io_geoparquet import save_geoparquet
from .io_lpf import save_lpf
from .narrative import load_storyboard
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
from .provenance import ProvenanceLedger, SpatialAnchor
from .reasoning import allen_probabilities
from .review_html import generate_review_html


def _default_fixtures_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent.parent / "fixtures"


def run_case_tang_song_poets(
    output_dir: str | pathlib.Path,
    *,
    chgis_path: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Case 1: Tang-Song Poets Migration & Affective Platial Topology.

    Provenance:
      - Biographical stops & affective annotations: `open_historical_demo` (structured
        public literary-historical facts; ZERO CBDB person rows fabricated or embedded).
      - Optional external CHGIS V6 Tang/Song prefecture polygons loaded only if `chgis_path`
        is explicitly supplied by the user (respecting CHGIS V6 EULA).
    """
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ev_tang = EvidenceRef(
        source_id="open-hist-tang-poets",
        label="Open Tang literary chronology (Li Bai / Du Fu standard annals, demo)",
        evidence_level="verified",
    )
    ev_song = EvidenceRef(
        source_id="open-hist-song-poets",
        label="Open Northern Song literary chronology (Su Shi standard annals, demo)",
        evidence_level="verified",
    )

    places = [
        PlatialPlace(
            place_id="urn:platial:changan",
            title="长安 (Chang'an)",
            fclasses=("A", "P"),
            names=[{"toponym": "长安", "lang": "zh"}, {"toponym": "京兆府", "lang": "zh"}, {"toponym": "Chang'an", "lang": "en"}],
            when=FuzzyInterval.from_crisp(618, 907, label="Tang Dynasty"),
            geometries=[CompetingGeometry("h-changan", {"type": "Point", "coordinates": [108.9402, 34.2658]}, 1.0, (ev_tang,), 6.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Tang", "type_ch": "府", "lev_rank": 3},
                locale={"setting": "imperial capital"},
                affect=AffectLayer(valence=0.55, arousal=0.80, dominant_mood="imperial_ambition_and_melancholy", tags=("court", "departure")),
            ),
            evidence=[ev_tang],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:luoyang",
            title="洛阳 (Luoyang)",
            fclasses=("A", "P"),
            names=[{"toponym": "洛阳", "lang": "zh"}, {"toponym": "河南府", "lang": "zh"}, {"toponym": "Luoyang", "lang": "en"}],
            when=FuzzyInterval.from_crisp(618, 907, label="Tang Dynasty"),
            geometries=[CompetingGeometry("h-luoyang", {"type": "Point", "coordinates": [112.454, 34.619]}, 1.0, (ev_tang,), 7.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Tang", "type_ch": "府", "lev_rank": 3},
                locale={"setting": "eastern capital"},
                affect=AffectLayer(valence=0.70, arousal=0.65, dominant_mood="poetic_camaraderie", tags=("meeting", "friendship")),
            ),
            evidence=[ev_tang],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:chengdu",
            title="成都 (Chengdu)",
            fclasses=("A", "P"),
            names=[{"toponym": "成都", "lang": "zh"}, {"toponym": "益州", "lang": "zh"}, {"toponym": "Chengdu", "lang": "en"}],
            when=FuzzyInterval.from_crisp(618, 907, label="Tang Dynasty"),
            geometries=[CompetingGeometry("h-chengdu", {"type": "Point", "coordinates": [104.0668, 30.5728]}, 1.0, (ev_tang,), 8.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Tang", "type_ch": "府", "lev_rank": 3},
                locale={"setting": "basin refuge / thatched cottage"},
                affect=AffectLayer(valence=0.25, arousal=0.50, dominant_mood="refuge_and_war_sorrow", tags=("exile_refuge", "river")),
            ),
            evidence=[ev_tang],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:huangzhou",
            title="黄州 (Huangzhou)",
            fclasses=("A", "P"),
            names=[{"toponym": "黄州", "lang": "zh"}, {"toponym": "Huangzhou", "lang": "en"}],
            when=FuzzyInterval.from_crisp(960, 1127, label="Northern Song"),
            geometries=[CompetingGeometry("h-huangzhou", {"type": "Point", "coordinates": [114.872, 30.453]}, 1.0, (ev_song,), 9.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Song", "type_ch": "州", "lev_rank": 3},
                locale={"setting": "Yangtze cliff / exile farm"},
                affect=AffectLayer(valence=-0.15, arousal=0.72, dominant_mood="transcendent_exile", tags=("red_cliff", "resilience")),
            ),
            evidence=[ev_song],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:hangzhou",
            title="杭州 (Hangzhou)",
            fclasses=("A", "P"),
            names=[{"toponym": "杭州", "lang": "zh"}, {"toponym": "Hangzhou", "lang": "en"}],
            when=FuzzyInterval.from_crisp(960, 1127, label="Northern Song"),
            geometries=[CompetingGeometry("h-hangzhou", {"type": "Point", "coordinates": [120.1551, 30.2741]}, 1.0, (ev_song,), 6.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Song", "type_ch": "州", "lev_rank": 3},
                locale={"setting": "lakefront prefecture"},
                affect=AffectLayer(valence=0.88, arousal=0.60, dominant_mood="lyrical_belonging", tags=("west_lake", "civic_care")),
            ),
            evidence=[ev_song],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:danzhou",
            title="儋州 (Danzhou)",
            fclasses=("A", "P"),
            names=[{"toponym": "儋州", "lang": "zh"}, {"toponym": "Danzhou", "lang": "en"}],
            when=FuzzyInterval.from_crisp(960, 1127, label="Northern Song"),
            geometries=[CompetingGeometry("h-danzhou", {"type": "Point", "coordinates": [109.576, 19.517]}, 1.0, (ev_song,), 15.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Song", "type_ch": "军", "lev_rank": 3},
                locale={"setting": "maritime island frontier"},
                affect=AffectLayer(valence=-0.65, arousal=0.68, dominant_mood="remote_exile_stoicism", tags=("frontier", "island")),
            ),
            evidence=[ev_song],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
    ]

    events = [
        TrajectoryEvent("ev-lb-1", "li_bai", "李白 (Li Bai)", "urn:platial:changan", "长安", 108.9402, 34.2658, FuzzyInterval(742, 742, 744, 744), 6.0, 0.55, "imperial_ambition", (ev_tang,)),
        TrajectoryEvent("ev-lb-2", "li_bai", "李白 (Li Bai)", "urn:platial:luoyang", "洛阳", 112.454, 34.619, FuzzyInterval(744, 744, 745, 745), 7.0, 0.75, "poetic_camaraderie", (ev_tang,)),
        TrajectoryEvent("ev-df-1", "du_fu", "杜甫 (Du Fu)", "urn:platial:luoyang", "洛阳", 112.460, 34.622, FuzzyInterval(744, 744, 745, 746), 7.0, 0.65, "poetic_camaraderie", (ev_tang,)),
        TrajectoryEvent("ev-df-2", "du_fu", "杜甫 (Du Fu)", "urn:platial:changan", "长安", 108.9402, 34.2658, FuzzyInterval(746, 747, 755, 756), 6.0, -0.35, "anxious_waiting", (ev_tang,)),
        TrajectoryEvent("ev-df-3", "du_fu", "杜甫 (Du Fu)", "urn:platial:chengdu", "成都", 104.0668, 30.5728, FuzzyInterval(759, 760, 765, 765), 8.0, 0.25, "refuge_and_war_sorrow", (ev_tang,)),
        TrajectoryEvent("ev-gs-1", "gao_shi", "高适 (Gao Shi)", "urn:platial:luoyang", "洛阳", 112.48, 34.63, FuzzyInterval(744, 744, 745, 745), 10.0, 0.60, "poetic_camaraderie", (ev_tang,)),
        TrajectoryEvent("ev-ss-1", "su_shi", "苏轼 (Su Shi)", "urn:platial:hangzhou", "杭州", 120.1551, 30.2741, FuzzyInterval(1071, 1071, 1074, 1074), 6.0, 0.88, "lyrical_belonging", (ev_song,)),
        TrajectoryEvent("ev-ss-2", "su_shi", "苏轼 (Su Shi)", "urn:platial:huangzhou", "黄州", 114.872, 30.453, FuzzyInterval(1080, 1080, 1084, 1084), 9.0, -0.15, "transcendent_exile", (ev_song,)),
        TrajectoryEvent("ev-ss-3", "su_shi", "苏轼 (Su Shi)", "urn:platial:danzhou", "儋州", 109.576, 19.517, FuzzyInterval(1097, 1097, 1100, 1100), 15.0, -0.65, "remote_exile_stoicism", (ev_song,)),
    ]

    chgis_loaded = 0
    if chgis_path and pathlib.Path(chgis_path).exists():
        tang_chgis = load_chgis_geoparquet(chgis_path, dynasty_filter="Tang")
        song_chgis = load_chgis_geoparquet(chgis_path, dynasty_filter="Northern Song")
        chgis_loaded = len(tang_chgis) + len(song_chgis)

    network = mine_cooccurrence_network(events, spatial_radius_km=35.0, min_joint_prob=0.2)
    field = AffectiveField.from_places(places, bandwidth_km=320.0)
    grid = field.sample_grid(nx=8, ny=6)

    lpf_path = out / "tang_song_poets.lpf.jsonld"
    pq_path = out / "tang_song_poets.geoparquet"
    net_path = out / "cooccurrence_network.json"
    aff_path = out / "affect_field.geojson"
    summary_path = out / "summary.json"

    save_lpf(places, lpf_path, strict_v13=True)
    save_geoparquet(places, pq_path)
    net_path.write_text(json.dumps(network, ensure_ascii=False, indent=2), encoding="utf-8")
    aff_path.write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "case": "tang_song_poets",
        "data_provenance": {
            "biographical_demo": "open_historical_demo (zero CBDB person rows fabricated)",
            "external_chgis_records_loaded": chgis_loaded,
        },
        "places_count": len(places),
        "cooccurrence_summary": network["summary"],
        "cooccurrence_edges": network["edges"],
        "affect_grid_cells": len(grid["features"]),
        "outputs": {
            "lpf": str(lpf_path),
            "geoparquet": str(pq_path),
            "cooccurrence_network": str(net_path),
            "affect_field": str(aff_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def run_case_silk_road_contested(
    output_dir: str | pathlib.Path,
    *,
    fixtures_dir: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Case 2: Silk Road Contested Toponyms & Archival Silence Graph.

    Provenance:
      - Real Muse open fixtures: WHG GeoNames Istanbul (`whg-place-sample.json`, CC BY 4.0)
        and PeriodO samples (`periodo-sample-darkage.json`, PD).
      - Silk Road contested oasis & archival-silence nodes: `open_historical_demo`.
    """
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fdir = pathlib.Path(fixtures_dir) if fixtures_dir else _default_fixtures_dir()

    ev_han = EvidenceRef("src-hanshu", "Hanshu Xiyuzhuan (open historical demo)", evidence_level="verified")
    ev_stein = EvidenceRef("src-stein", "Lop Nor archaeological survey hypotheses (open demo)", evidence_level="indirect")
    ev_dun = EvidenceRef("src-dunhuang", "Dunhuang manuscripts & Tang gazetteers (open demo)", evidence_level="verified")

    loulan_geoms = normalize_hypothesis_weights(
        [
            CompetingGeometry("h-loulan-la", {"type": "Point", "coordinates": [89.91, 40.51]}, 0.70, (ev_han, ev_stein), 8.5, notes="LA Ruin Complex"),
            CompetingGeometry("h-loulan-south", {"type": "Point", "coordinates": [89.42, 39.88]}, 0.30, (ev_stein,), 24.0, notes="Southern Lop shifting channel hypothesis"),
        ]
    )

    silk_places = [
        PlatialPlace(
            place_id="urn:platial:loulan",
            title="楼兰 / Krorän",
            fclasses=("S", "P"),
            names=[{"toponym": "楼兰", "lang": "zh"}, {"toponym": "鄯善", "lang": "zh"}, {"toponym": "Krorän", "lang": "xpg"}],
            when=FuzzyInterval(-176, -150, 330, 420, label="Han-Wei-Jin Oasis", certainty="uncertain"),
            geometries=loulan_geoms,
            absence=AbsenceState.CONTESTED,
            absence_reason="Multiple candidate ruin sites across shifting Lop Nor channels",
            platial=PlatialAttributes(
                location={"dynasty": "Han-Jin", "region": "Tarim Basin"},
                locale={"setting": "desert oasis hub"},
                affect=AffectLayer(valence=-0.40, arousal=0.68, dominant_mood="frontier_desolation"),
            ),
            evidence=[ev_han, ev_stein],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:dunhuang",
            title="敦煌 (Dunhuang)",
            fclasses=("A", "P"),
            names=[{"toponym": "敦煌", "lang": "zh"}, {"toponym": "沙州", "lang": "zh"}, {"toponym": "Dunhuang", "lang": "en"}],
            when=FuzzyInterval(-111, -108, 907, 1036, label="Han-Tang-Guiyijun", certainty="certain"),
            geometries=[CompetingGeometry("h-dh", {"type": "Point", "coordinates": [94.661, 40.142]}, 1.0, (ev_dun,), 5.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Tang", "type_ch": "州", "lev_rank": 3},
                locale={"setting": "Hexi corridor oasis & cave sanctuary"},
                affect=AffectLayer(valence=0.50, arousal=0.62, dominant_mood="sacred_crossroads"),
            ),
            evidence=[ev_dun],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:gaochang",
            title="高昌 (Gaochang / Qocho)",
            fclasses=("A", "S"),
            names=[{"toponym": "高昌", "lang": "zh"}, {"toponym": "西州", "lang": "zh"}, {"toponym": "Qocho", "lang": "ug"}],
            when=FuzzyInterval(460, 460, 640, 803, label="Gaochang-Xizhou", certainty="uncertain"),
            geometries=[CompetingGeometry("h-gc", {"type": "Point", "coordinates": [89.53, 42.85]}, 1.0, (ev_dun,), 7.0)],
            platial=PlatialAttributes(
                location={"dynasty": "Tang", "type_ch": "州", "lev_rank": 3},
                locale={"setting": "Turpan depression oasis"},
                affect=AffectLayer(valence=0.20, arousal=0.58, dominant_mood="multilingual_entrepot"),
            ),
            evidence=[ev_dun],
            ccodes=["CN"],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:tarim-silent-post",
            title="漠南失考驿站 (Unrecorded Tarim Post)",
            fclasses=("R",),
            when=FuzzyInterval(400, 450, 600, 640, label="Northern & Southern Dynasties gap", certainty="uncertain"),
            absence=AbsenceState.UNRECORDED,
            absence_reason="Archival silence between Jin withdrawal and Tang Anxi Protectorate",
            platial=PlatialAttributes(location={"region": "Southern Tarim"}, locale={"setting": "relay station"}),
            evidence=[ev_stein],
            provenance="open_historical_demo",
        ),
        PlatialPlace(
            place_id="urn:platial:loulan-post-tang",
            title="楼兰城 (Tang-era Absence)",
            fclasses=("S",),
            when=FuzzyInterval(640, 650, 900, 907, label="Tang"),
            absence=AbsenceState.ABSENT,
            absence_reason="Positively attested abandoned after Lop Nor hydrological shift",
            platial=PlatialAttributes(location={"region": "Lop Nor"}, locale={"setting": "abandoned ruin"}),
            evidence=[ev_dun],
            provenance="open_historical_demo",
        ),
    ]

    real_whg_loaded = 0
    whg_file = fdir / "whg-place-sample.json"
    if whg_file.exists():
        whg_places = load_whg_lpf(whg_file)
        silk_places.extend(whg_places)
        real_whg_loaded = len(whg_places)

    periodo_loaded = 0
    with GazetteerIndex(":memory:") as idx:
        idx.add_places(silk_places)
        per_file = fdir / "periodo-sample-darkage.json"
        if per_file.exists():
            idx.add_period(load_periodo_json(per_file))
            periodo_loaded = 1

        dis = CrossDynastyDisambiguator(idx)
        dis_loulan = dis.disambiguate("楼兰", when=FuzzyInterval.from_crisp(100, 300), top_k=3)
        dis_ist = dis.disambiguate("Constantinople", top_k=2)

    # Allen temporal overlap between Loulan and Dunhuang
    allen_ld = allen_probabilities(silk_places[0].when, silk_places[1].when, n_samples=5000)

    lpf_path = out / "silk_road_contested.lpf.jsonld"
    pq_path = out / "silk_road_contested.geoparquet"
    summary_path = out / "summary.json"

    save_lpf(silk_places, lpf_path, strict_v13=True)
    save_geoparquet(silk_places, pq_path)

    silence_counts = {
        s.value: sum(1 for p in silk_places if p.absence == s) for s in AbsenceState
    }

    summary = {
        "case": "silk_road_contested",
        "data_provenance": {
            "real_whg_cc_by_4_records": real_whg_loaded,
            "real_periodo_pd_records": periodo_loaded,
            "silk_road_nodes": "open_historical_demo",
        },
        "places_count": len(silk_places),
        "archival_silence_counts": silence_counts,
        "allen_loulan_vs_dunhuang": allen_ld.to_dict(),
        "disambiguation_loulan_top": [c.to_dict() for c in dis_loulan],
        "disambiguation_constantinople_top": [c.to_dict() for c in dis_ist],
        "outputs": {
            "lpf": str(lpf_path),
            "geoparquet": str(pq_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def run_case_grand_canal_narrative(
    output_dir: str | pathlib.Path,
    *,
    fixtures_dir: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Case 3: Grand Canal Linear Cultural Heritage Evidence-Bound Cinematic Narrative Map.

    Provenance:
      - Grand Canal narrative storyboard (Qingjiangpu, Yangzhou, Zhenjiang, Suzhou, Hangzhou):
        `open_historical_demo` aligned to IJDE 2026 summary-level schema (`NARRATIVE_SCHEMA.md` §1).
      - Real Allmaps (CC0) & Maplat worked-example Saigon 6-GCP coordinate bridge residual
        benchmark + SVG mask projection (since thematic China IIIF maps were NOT_OBTAINED).
      - Necessary Reunions-inspired dual-track AI vs. Human Verified ledger & HTML workbench.
    """
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fdir = pathlib.Path(fixtures_dir) if fixtures_dir else _default_fixtures_dir()

    storyboard_dict = {
        "storyboard_id": "grand-canal-cinematic-2026",
        "title": "大运河线性文化遗产：证据绑定式电影感时空叙事地图",
        "subtitle": "清江浦—扬州—镇江—苏州—杭州 · 遵循 NARRATIVE_SCHEMA.md 证据门禁与三层地方感模型",
        "provenance_notice": (
            "本案例大运河分镜节点采用公开史实结构化示范数据 (open_historical_demo)；"
            "古地图非扭曲配准残差基准采用真实 Allmaps CC0 西贡标注 (1bfb1eb4198e7240)。"
        ),
        "sources": [
            {
                "source_id": "ming-shi-hequ",
                "label": "《明史·河渠志》清江浦开凿与漕运闸坝记载（公开史实示范）",
                "evidence_level": "verified",
                "locator": "卷八十五·河渠三",
            },
            {
                "source_id": "qing-cao-yun",
                "label": "《清史稿·河渠志》与淮扬运河水工图志（公开史实示范）",
                "evidence_level": "verified",
                "locator": "运河淮扬段",
            },
            {
                "source_id": "jiangnan-gazetteer",
                "label": "江南运河方志与明清市镇游记（公开史实示范）",
                "evidence_level": "indirect",
                "locator": "镇江—苏州—杭州段",
            },
        ],
        "scenes": [
            {
                "narrative_unit_id": "u-qjp",
                "map_scene_id": "scene-qingjiangpu",
                "title": "清江浦 · 黄淮运交汇闸口",
                "heritage_element": "清江浦船闸群与转搬仓枢纽",
                "narrative_text": "永乐十三年（1415年）陈瑄开清江浦，设移风、清江、福兴、新庄四闸节水通漕，成为明清漕运总督驻节与南北转运咽喉。",
                "when": {"earliest_start": 1415, "latest_start": 1415, "earliest_end": 1855, "latest_end": 1855},
                "camera": {"center": [119.015, 33.610], "zoom": 10.5, "bearing": -18, "pitch": 40, "shot_type": "establishing"},
                "evidence_level": "verified",
                "evidence_ids": ["ming-shi-hequ", "qing-cao-yun"],
                "shot_sequence": ["establishing", "push_in"],
                "scale": "hub",
                "temporal_shift": "chronological",
                "duration_sec": 10.0,
                "pace": "measured",
                "transition": "fly_to",
                "valence": 0.45,
                "dominant_mood": "hydraulic_order",
            },
            {
                "narrative_unit_id": "u-yz",
                "map_scene_id": "scene-yangzhou",
                "title": "扬州 · 盐漕交汇与瓜洲渡",
                "heritage_element": "邵伯古堤、扬州城河与瓜洲入江口",
                "narrative_text": "漕船南下经高邮、邵伯入扬州，淮盐与漕粮在此汇聚；瓜洲渡口见证了大运河与长江水系交汇处的繁华与水患张力。",
                "when": {"earliest_start": 605, "latest_start": 618, "earliest_end": 1850, "latest_end": 1911},
                "camera": {"center": [119.412, 32.394], "zoom": 10.0, "bearing": 12, "pitch": 35, "shot_type": "tracking"},
                "evidence_level": "verified",
                "evidence_ids": ["qing-cao-yun"],
                "shot_sequence": ["tracking", "pan"],
                "scale": "corridor",
                "temporal_shift": "flashback",
                "duration_sec": 9.0,
                "pace": "flowing",
                "transition": "fly_to",
                "valence": 0.72,
                "dominant_mood": "commercial_vibrancy",
            },
            {
                "narrative_unit_id": "u-zj",
                "map_scene_id": "scene-zhenjiang",
                "title": "镇江 · 江南运河入江门户",
                "heritage_element": "京口闸与西津渡古街区",
                "narrative_text": "跨江抵达京口，江南运河由此南启。潮汐与江岸泥沙推移塑造了西津渡不断前移的岸线记忆。",
                "when": {"earliest_start": 1368, "latest_start": 1400, "earliest_end": 1900, "latest_end": 1911},
                "camera": {"center": [119.425, 32.204], "zoom": 11.0, "bearing": 25, "pitch": 30, "shot_type": "push_in"},
                "evidence_level": "indirect",
                "evidence_ids": ["jiangnan-gazetteer"],
                "shot_sequence": ["push_in", "orbit"],
                "scale": "site",
                "temporal_shift": "chronological",
                "duration_sec": 8.0,
                "pace": "medium",
                "transition": "dissolve",
                "valence": 0.35,
                "dominant_mood": "liminal_crossing",
            },
            {
                "narrative_unit_id": "u-sz",
                "map_scene_id": "scene-suzhou",
                "title": "苏州 · 宝带桥与水巷织网",
                "heritage_element": "盘门水陆城门、山塘河与宝带桥",
                "narrative_text": "运河绕城分流，织入市井水巷与丝绸市镇网络；夜间灯火与舟楫声构成了江南最具辨识度的日常地方感。",
                "when": {"earliest_start": 816, "latest_start": 820, "earliest_end": 1911, "latest_end": 1911},
                "camera": {"center": [120.619, 31.299], "zoom": 10.8, "bearing": -8, "pitch": 32, "shot_type": "pan"},
                "evidence_level": "verified",
                "evidence_ids": ["jiangnan-gazetteer", "qing-cao-yun"],
                "shot_sequence": ["pan", "tracking"],
                "scale": "urban",
                "temporal_shift": "parallel",
                "duration_sec": 9.0,
                "pace": "gentle",
                "transition": "fly_to",
                "valence": 0.85,
                "dominant_mood": "intimate_watertown",
            },
            {
                "narrative_unit_id": "u-hz",
                "map_scene_id": "scene-hangzhou",
                "title": "杭州 · 拱宸桥与运河南端终章",
                "heritage_element": "拱宸桥、富义仓与钱塘江转运终端",
                "narrative_text": "过拱宸桥入武林门北关，大运河在此完成千里漕运的南端收束；围绕晚清民初埠头口述声景的复原仍带推测色彩。",
                "when": {"earliest_start": 1631, "latest_start": 1631, "earliest_end": 1911, "latest_end": 1911},
                "camera": {"center": [120.143, 30.319], "zoom": 10.5, "bearing": 0, "pitch": 25, "shot_type": "pull_out"},
                "evidence_level": "speculative",
                "evidence_ids": ["jiangnan-gazetteer"],
                "shot_sequence": ["orbit", "pull_out"],
                "scale": "terminal",
                "temporal_shift": "chronological",
                "duration_sec": 10.0,
                "pace": "slow",
                "transition": "fade",
                "valence": 0.68,
                "dominant_mood": "reflective_closure",
            },
        ],
    }

    yaml_path = out / "grand_canal_storyboard.yaml"
    yaml_path.write_text(yaml.safe_dump(storyboard_dict, allow_unicode=True, sort_keys=False), encoding="utf-8")
    storyboard = load_storyboard(yaml_path)

    html_path = out / "grand_canal_narrative.html"
    compile_narrative_html(storyboard, html_path)

    # Real Allmaps/Maplat non-distorting bridge residual benchmark
    georef_report: dict[str, Any] = {}
    am_file = fdir / "allmaps-example-saigon-annotation.json"
    ml_file = fdir / "allmaps-saigon-maplat-standard.json"
    if am_file.exists():
        am_spec = parse_allmaps_annotation(am_file)
        tps = NonDistortingBridge.from_spec(am_spec, method="tps")
        tin = NonDistortingBridge.from_spec(am_spec, method="tin")
        ev_am = EvidenceRef(
            source_id="allmaps-saigon-cc0",
            label="Allmaps Georeference Annotation 1bfb1eb4198e7240 (CC0)",
            uri="https://annotations.allmaps.org/maps/1bfb1eb4198e7240",
            evidence_level="verified",
        )
        svg_feat = None
        if am_spec.svg_mask:
            ann = SVGMapAnnotation(
                annotation_id="urn:anno:saigon-mask",
                canvas_id=am_spec.iiif_service_id or "iiif:saigon",
                label="BnF Saigon Map Mask",
                svg_selector=am_spec.svg_mask,
                evidence=(ev_am,),
            )
            svg_feat = ann.to_wgs84_geojson_feature(tps)
        georef_report = {
            "source_fixture": am_file.name,
            "tps_residuals": tps.evaluate_residuals(),
            "tin_residuals": tin.evaluate_residuals(),
            "viewport_sample": tps.local_viewport_transform(7500.0, 7000.0),
            "svg_mask_projected_vertices": len(svg_feat["geometry"]["coordinates"][0]) if svg_feat else 0,
            "maplat_cross_check_gcps": len(parse_maplat_standard(ml_file).gcps) if ml_file.exists() else 0,
        }

    # Dual-track AI vs. Human Verified review ledger & HTML workbench
    ledger = ProvenanceLedger()
    ledger.propose_ai_extraction(
        annotation_id="canal-htr-01",
        annotation_type="Text Spotting",
        source="Loghi AI",
        extracted_text="清江蒲船闸",
        normalized_toponym="清江浦",
        confidence=0.82,
        spatial_anchor=SpatialAnchor("iiif:canal-demo/c1", (1420.0, 810.0), "urn:platial:qingjiangpu", 1),
        source_citation="明清运河图志示范切片",
    )
    ledger.human_verify(
        "canal-htr-01",
        reviewer="editor-chen",
        corrected_text="清江浦船闸",
        summary="修正 HTR 形近字（蒲→浦）并绑定清江浦空间锚点",
    )
    ledger.propose_ai_extraction(
        annotation_id="canal-vlm-02",
        annotation_type="Iconography",
        source="Other AI",
        extracted_text="拱宸桥三孔石拱图标",
        normalized_toponym="拱宸桥",
        confidence=0.76,
        spatial_anchor=SpatialAnchor("iiif:canal-demo/c5", (2890.0, 1650.0), None, 2),
        source_citation="江南运河图志示范切片（待人工复核）",
    )
    ledger_path = out / "dual_track_ledger.json"
    review_html_path = out / "dual_track_review.html"
    ledger.save(ledger_path)
    generate_review_html(
        ledger,
        title="大运河古图与方志 VLM/HTR 人机分级复核台",
        output_path=review_html_path,
    )

    summary = {
        "case": "grand_canal_narrative",
        "data_provenance": {
            "canal_storyboard": "open_historical_demo (IJDE 2026 summary-reconstructed schema)",
            "georef_benchmark": "real Allmaps CC0 Saigon annotation (1bfb1eb4198e7240) & Maplat worked example",
            "review_ledger": "Necessary Reunions-inspired dual-track demo",
        },
        "scenes_count": len(storyboard.scenes),
        "evidence_levels": {
            lvl: sum(1 for s in storyboard.scenes if s.evidence_level == lvl)
            for lvl in ("verified", "indirect", "speculative")
        },
        "narrative_html_bytes": html_path.stat().st_size,
        "georef_benchmark": georef_report,
        "provenance_stats": ledger.summary_stats(),
        "outputs": {
            "storyboard_yaml": str(yaml_path),
            "narrative_html": str(html_path),
            "ledger_json": str(ledger_path),
            "review_html": str(review_html_path),
        },
    }
    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
