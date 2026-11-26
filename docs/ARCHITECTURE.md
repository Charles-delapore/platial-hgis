# Platial-HGIS Architecture & CLI Cookbook

## 1. Module Map (D3-P1 to D3-P7)

| Package | Modules | Key Capabilities |
|---|---|---|
| **D3-P1** | `primitives.py`, `io_lpf.py`, `io_geoparquet.py` | Four-tuple `FuzzyInterval` (PeriodO `xsd:gYear` & CIDOC-CRM `E52_Time-Span`), weighted `CompetingGeometry`, 3-state archival silence (`absent`/`unrecorded`/`contested`), 3-layer platial attributes (`location`/`locale`/`affect`), lossless LPF v1.1–v1.3 JSON-LD & GeoParquet v1.0.0 I/O. |
| **D3-P2** | `connectors.py`, `gazetteer.py`, `disambiguate.py` | External CHGIS GeoParquet (PyArrow CRS84-safe) & Shapefile zip loaders, WHG LPF, PeriodO JSON-LD, CBDB schema & dual-tier license guard, Cliopatria GeoJSON, SQLite FTS5 (+ optional DuckDB hook) index, and cross-dynasty temporal-hierarchy disambiguation. |
| **D3-P3** | `georef.py`, `annotations.py` | Allmaps IIIF Georeference Annotation & Maplat standard JSON parsers, non-distorting Thin-Plate Spline (TPS + Gauss-Newton bijective inverse) and Delaunay TIN piecewise affine bridges, LOOCV residual diagnostics, local viewport scale/rotation, and evidence-bound SVG region annotations. |
| **D3-P4** | `reasoning.py`, `cooccurrence.py`, `affect_field.py` | Probabilistic Allen interval algebra (7 disjoint relations summing to 1.0 + `contemporary`), uncertain-window spatiotemporal co-occurrence network mining, and kernel-smoothed spatial emotional valence & mood dispersion fields. |
| **D3-P5** | `narrative.py`, `narrative_html.py` | Evidence-bound YAML/JSON storyboard validator (hard-rejecting uncited scenes unless marked `speculative`) and zero-backend standalone interactive HTML compiler with map-view switcher, camera telemetry HUD, timeline scrubber, and evidence provenance cards. |
| **D3-P6** | `provenance.py`, `review_html.py` | Necessary Reunions-inspired dual-track (`AI` vs. `Human Verified`) SHA-256 hash-chained revision ledger, strict verified-layer export gate, and zero-backend static HTML human review workbench. |
| **D3-P7** | `cases.py`, `cli.py` | Three offline reproducible empirical case packs (`tang_song_poets`, `silk_road_contested`, `grand_canal_narrative`) and unified CLI (`python -m platial_hgis`). |

## 2. CLI Quick Reference

```bash
# Validate an LPF JSON-LD file
python3 -m platial_hgis validate-lpf fixtures/whg-place-sample.json --non-strict

# Evaluate non-distorting TPS or TIN residuals on Allmaps / Maplat GCPs
python3 -m platial_hgis georef-eval fixtures/allmaps-example-saigon-annotation.json --method tps
python3 -m platial_hgis georef-eval fixtures/allmaps-saigon-maplat-standard.json --format maplat --method tin

# Probabilistic Allen temporal relations
python3 -m platial_hgis allen-prob --a 740 745 750 755 --b 748 752 760 765

# Run all 3 offline empirical case packs (optionally pass external CHGIS GeoParquet)
python3 -m platial_hgis run-case all -o outputs/cases --chgis-path /path/to/chgis.geoparquet

# Human-verify an AI extraction and regenerate the review workbench HTML
python3 -m platial_hgis review-verify outputs/cases/grand_canal_narrative/dual_track_ledger.json \
  --id canal-vlm-02 --reviewer editor-name --html-out outputs/review.html
```
