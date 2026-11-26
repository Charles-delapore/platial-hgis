# Data Licensing & Redistribution Policy

This repository (`platial-hgis`) is licensed under the **MIT License** for all original source code, tests, schemas, and open historical demonstration scripts. Third-party historical GIS datasets carry distinct upstream licenses that are strictly enforced here:

| Dataset / Standard | Upstream License | Handling in `platial-hgis` |
|---|---|---|
| **CHGIS V6** (Harvard Fairbank Center & Fudan Univ.) | **CHGIS V6 EULA**: Non-commercial academic/educational use only; redistribution prohibited without written permission. Mandatory citation: `"CHGIS Version 6." (c) Fairbank Center for Chinese Studies and the Institute for Chinese Historical Geography at Fudan University, Dec 2016.` | **NOT embedded in this repository.** Loaded at runtime via external local path (`--chgis-path` / `load_chgis_geoparquet()` / `load_chgis_shapefile_zip()`). |
| **CBDB** (China Biographical Database) | **Dual-tier (effective 2026-08-20)**: §1 in-release standalone scope under CC BY-NC-SA 4.0; §2 out-of-release under CBDB proprietary terms (no derivatives, no redistribution, no public API). | **Zero CBDB person records embedded or fabricated.** Only schema validation (`cbdb-sample-schema-template.md`) and public sources inventory metadata are supported. |
| **PeriodO** | **Public Domain** | Small reference samples vendored in `fixtures/` (`periodo-sample-darkage.json`, `periodo-sample-cultural-revolution.json`). |
| **Allmaps Georeference Annotations** | **CC0** (annotations); original IIIF images follow holding institution terms (BnF Gallica). | Reference annotation (`allmaps-example-saigon-annotation.json`) and Maplat worked example (`allmaps-saigon-maplat-standard.json`) vendored in `fixtures/`. |
| **World Historical Gazetteer (WHG) / GeoNames sample** | **CC BY 4.0** (GeoNames, Unxos GmbH) | Single place sample (`whg-place-sample.json`) vendored in `fixtures/` with full attribution. |
| **Linked Places Format (LPF)** | Upstream repo has no LICENSE file; sample records use CC BY-SA 3.0. | Referenced by specification (v1.1 / v1.2.2 / v1.3); context/schema implemented cleanly from spec. |
| **CIDOC-CRM v7.1.3** | **CC BY 4.0** | Core class/property URIs (`E52`, `E53`, `E92`, `P81a/b`, `P82a/b`) referenced in serialization. |
| **Cliopatria (Seshat)** | **CC BY 4.0** | Loader supports external `cliopatria.geojson` (full 49.2 MB file not embedded). |
| **Maplat** | **Apache License 2.0** | Standard JSON GCP format & non-distorting transform concepts implemented cleanly from spec. |
| **Necessary Reunions** | **EUPL v1.2** (code); GAVOC/Manifest research use. | Dual-track AI vs. Human Verified workflow & provenance schema inspired by public documentation; no EUPL code copied. |
| **IJDE 2026 (Yang et al.) & Mapping Place 2025 (Giordano et al.)** | **CC BY 4.0** (abstract-level reconstruction only; full text unavailable due to publisher HTTP 403). | Narrative storyboard schema and provisional 3-layer platial affect taxonomy explicitly marked as summary-level / provisional. |
