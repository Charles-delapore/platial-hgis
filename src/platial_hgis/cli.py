"""Unified CLI entrypoint for Platial-HGIS (`platial-hgis` / `python -m platial_hgis`)."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Sequence

from . import __version__
from .cases import (
    run_case_grand_canal_narrative,
    run_case_silk_road_contested,
    run_case_tang_song_poets,
)
from .georef import NonDistortingBridge, parse_allmaps_annotation, parse_maplat_standard
from .io_geoparquet import load_geoparquet, save_geoparquet
from .io_lpf import load_lpf, save_lpf
from .narrative import load_storyboard
from .narrative_html import compile_narrative_html
from .primitives import FuzzyInterval
from .provenance import ProvenanceLedger
from .reasoning import allen_probabilities
from .review_html import generate_review_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="platial-hgis",
        description="Platial-HGIS: Evidence-bound platial & fuzzy spatiotemporal HGIS engine",
    )
    parser.add_argument("--version", action="version", version=f"platial-hgis {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. validate-lpf
    p_lpf = sub.add_parser("validate-lpf", help="Validate an LPF JSON-LD file")
    p_lpf.add_argument("input_path", type=pathlib.Path)
    p_lpf.add_argument("--non-strict", action="store_true", help="Allow LPF v1.1/v1.2 without fclasses")

    # 2. convert-geoparquet
    p_conv = sub.add_parser("convert-geoparquet", help="Convert between LPF JSON-LD and GeoParquet")
    p_conv.add_argument("input_path", type=pathlib.Path)
    p_conv.add_argument("output_path", type=pathlib.Path)
    p_conv.add_argument("--to", choices=["geoparquet", "lpf"], required=True)

    # 3. georef-eval
    p_geo = sub.add_parser("georef-eval", help="Evaluate Allmaps/Maplat non-distorting bridge residuals")
    p_geo.add_argument("input_path", type=pathlib.Path)
    p_geo.add_argument("--format", choices=["allmaps", "maplat"], default="allmaps")
    p_geo.add_argument("--method", choices=["tps", "tin"], default="tps")

    # 4. allen-prob
    p_al = sub.add_parser("allen-prob", help="Compute probabilistic Allen relations between two fuzzy intervals")
    p_al.add_argument("--a", nargs=4, type=float, required=True, metavar=("ES", "LS", "EE", "LE"))
    p_al.add_argument("--b", nargs=4, type=float, required=True, metavar=("ES", "LS", "EE", "LE"))
    p_al.add_argument("--samples", type=int, default=8000)

    # 5. compile-narrative
    p_nar = sub.add_parser("compile-narrative", help="Compile YAML/JSON storyboard into interactive HTML")
    p_nar.add_argument("script_path", type=pathlib.Path)
    p_nar.add_argument("-o", "--output", type=pathlib.Path, required=True)

    # 6. review-verify & review-html
    p_rv = sub.add_parser("review-verify", help="Human-verify an AI extraction in a provenance ledger")
    p_rv.add_argument("ledger_path", type=pathlib.Path)
    p_rv.add_argument("--id", dest="annotation_id", required=True)
    p_rv.add_argument("--reviewer", required=True)
    p_rv.add_argument("--text", dest="corrected_text", default=None)
    p_rv.add_argument("--html-out", type=pathlib.Path, default=None)

    # 7. run-case
    p_case = sub.add_parser("run-case", help="Run one or all 3 offline empirical case packs")
    p_case.add_argument(
        "case",
        choices=["tang_song_poets", "silk_road_contested", "grand_canal_narrative", "all"],
    )
    p_case.add_argument("-o", "--output-dir", type=pathlib.Path, required=True)
    p_case.add_argument("--chgis-path", type=pathlib.Path, default=None)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-lpf":
        places = load_lpf(args.input_path, strict_v13=not args.non_strict)
        print(json.dumps({"status": "valid", "places": len(places)}, ensure_ascii=False))
        return 0

    if args.command == "convert-geoparquet":
        if args.to == "geoparquet":
            places = load_lpf(args.input_path, strict_v13=False)
            save_geoparquet(places, args.output_path)
        else:
            places = load_geoparquet(args.input_path)
            save_lpf(places, args.output_path, strict_v13=True)
        print(json.dumps({"status": "ok", "places": len(places), "output": str(args.output_path)}, ensure_ascii=False))
        return 0

    if args.command == "georef-eval":
        spec = (
            parse_allmaps_annotation(args.input_path)
            if args.format == "allmaps"
            else parse_maplat_standard(args.input_path)
        )
        bridge = NonDistortingBridge.from_spec(spec, method=args.method)
        print(json.dumps(bridge.evaluate_residuals(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "allen-prob":
        iv_a = FuzzyInterval(*args.a)
        iv_b = FuzzyInterval(*args.b)
        res = allen_probabilities(iv_a, iv_b, n_samples=args.samples)
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "compile-narrative":
        sb = load_storyboard(args.script_path)
        compile_narrative_html(sb, args.output)
        print(json.dumps({"status": "compiled", "scenes": len(sb.scenes), "output": str(args.output)}, ensure_ascii=False))
        return 0

    if args.command == "review-verify":
        ledger = ProvenanceLedger.load(args.ledger_path)
        rec = ledger.human_verify(
            args.annotation_id,
            reviewer=args.reviewer,
            corrected_text=args.corrected_text,
        )
        ledger.save(args.ledger_path)
        if args.html_out:
            generate_review_html(ledger, output_path=args.html_out)
        print(json.dumps({"status": "verified", "annotation_id": rec.annotation_id, "stats": ledger.summary_stats()}, ensure_ascii=False))
        return 0

    if args.command == "run-case":
        out = args.output_dir
        results = {}
        if args.case in {"tang_song_poets", "all"}:
            results["tang_song_poets"] = run_case_tang_song_poets(
                out / "tang_song_poets" if args.case == "all" else out,
                chgis_path=args.chgis_path,
            )
        if args.case in {"silk_road_contested", "all"}:
            results["silk_road_contested"] = run_case_silk_road_contested(
                out / "silk_road_contested" if args.case == "all" else out,
            )
        if args.case in {"grand_canal_narrative", "all"}:
            results["grand_canal_narrative"] = run_case_grand_canal_narrative(
                out / "grand_canal_narrative" if args.case == "all" else out,
            )
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
