# Platial-HGIS (`platial-hgis`)

Evidence-bound **platial** ("sense of place") and **fuzzy spatiotemporal historical GIS** graph engine built from first principles for offline reproducible historical humanities workflows.

## Architecture (D3-P1 to D3-P7)

1. **D3-P1 Fuzzy Spatiotemporal Primitives & Archival Silence (`primitives`, `io_lpf`, `io_geoparquet`)**: Four-tuple fuzzy intervals (`earliest_start`, `latest_start`, `earliest_end`, `latest_end`) with PeriodO alignment, weighted competing geometries with citations, three-state archival absence (`absent` / `unrecorded` / `contested`), 3-layer platial attributes (`location` / `locale` / `affect`), and lossless LPF JSON-LD ↔ GeoParquet/JSON I/O.
2. **D3-P2 Historical Gazetteer & Cross-Dynasty Disambiguation (`connectors`, `gazetteer`, `disambiguate`)**: Local SQLite FTS5 (+ optional DuckDB hook) indexing for external CHGIS GeoParquet/Shapefile, WHG LPF, PeriodO, CBDB schema validation, and Cliopatria metadata, with temporal-administrative disambiguation and automatic uncertainty radii.
3. **D3-P3 Non-Distorting Historical Map Coordinate Bridge (`georef`, `annotations`)**: Allmaps Web Annotation & Maplat GCP parsers, Thin-Plate Spline (TPS) and Delaunay TIN piecewise affine bidirectional transforms (pixel ↔ WGS84) without warping the original scan, LOOCV residual diagnostics, and SVG evidence annotations.
4. **D3-P4 Fuzzy Spatiotemporal Reasoning & Affective Fields (`reasoning`, `cooccurrence`, `affect_field`)**: Probabilistic Allen interval algebra, uncertain-window spatiotemporal co-occurrence network mining, and spatial emotional valence/mood field modeling.
5. **D3-P5 Evidence-Bound Narrative Script Compiler (`narrative`, `narrative_html`)**: YAML/JSON storyboard compiler enforcing citation binding (`verified` / `indirect` / `speculative`) and compiling zero-backend interactive HTML narrative packages.
6. **D3-P6 Dual-Track AI vs. Human Verified Provenance (`provenance`, `review_html`)**: SHA-256 stamped dual-track review ledger inspired by Necessary Reunions with strict verified-layer gating and static HTML review workbench generation.
7. **D3-P7 Reproducible Empirical Case Packs (`cases`, `cli`)**: Three offline one-click cases (Tang–Song Poets, Silk Road Contested Toponyms & Archival Silence, Grand Canal Cinematic Narrative HTML).

## Licensing

Code is MIT-licensed (`LICENSE`). Third-party dataset boundaries (including CHGIS V6 EULA non-redistribution and CBDB dual-tier terms) are documented in `DATA_LICENSES.md`.
