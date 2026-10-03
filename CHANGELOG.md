# Collection changelog

Model release histories also live in `assets/<asset-id>/CHANGELOG.md`.

## Unreleased

- Published neutral Mega Drive cartridge and standalone PlayStation CD 0.1.0 packages. Replaced the default PlayStation case with a 120 mm CD and annular front-only artwork target. Added owner-supplied Sonic/Crash artwork mapping with provenance; no third-party scans are distributed.

- Refined the development media materials with embedded, original surface maps: physically scaled ABS grain on Mega Drive and restrained concentric optical roughness on the PlayStation disc. Polished the clear case, booklet edges and export efficiency while preserving the reconstructed envelopes and mechanical clearances. Doubled the export-review studio samples to 64 for fine surface detail.
- Reconstructed the western Mega Drive shell and NTSC-U/C standard PlayStation case/CD using identified photographs, manufacturer dimensions and measured reference geometry. Added separate parametric modules and source/confidence records in `docs/measurement-evidence-2026-10-02.json` and each asset's credits. Replaced the generic profiles, corrected artwork surfaces and added orthographic export review views plus a standalone CD export. This is unreleased development work; the earlier rejection below documents the superseded drafts.
- Rejected the Mega Drive and PlayStation development drafts for visual fidelity after comparison with photographed physical specimens. Recorded regional differences, invented cartridge details and case assembly defects in `docs/reference-audit-2026-10-02.md`. Previous export/import checks remain technical checks only; no corrected geometry or new release is included in this documentation review.
- Added reproducible, neutral Mega Drive cartridge and PlayStation jewel case/CD development models, with editable Blender sources, self-contained GLB exports and separate front/rear artwork surfaces. These drafts are not published releases and do not alter the release catalog.
- Added `tools/refine_snes.py` to refine a verified SNES 0.1.0 source: small molded-edge bevels and packed ABS roughness grain reduce sharp highlights, while matte labels retain the original folded geometry and UVs. The tool renders matched before/after hero, top and bottom views without changing the released snapshot.
- Added a dependency-free GLB inspection tool and malformed-asset checks for portable exports, finite bounds and usable front/rear label UVs.

- Published the [Super Mario World example 0.1.1](assets/snes-super-mario-world/CHANGELOG.md) with standalone front and rear label exports derived from the published GLB, so a consumer can map the artwork onto the shared neutral `snes-ntsc-u` shell.
- Translated all authored gallery text into English, including metadata, model descriptions, controls, accessibility labels, status/error messages and generated cards. Dimensions now use decimal points.
- Translated the Super Mario World manifest's descriptive change notes at the owner's request; existing release tags, packages, binaries and checksums remain unchanged.
- Added an English-only rule for future repository content, gallery copy and release notes.

- Added a public GitHub Pages gallery generated from the catalog, with black-background 3D orbit/zoom, six view presets, version selection, render galleries, downloads and credits for every model.
- Added the existing Super Mario World example as a separately versioned asset, preserving Nintendo artwork/mark exclusions and scan-source attribution.
- Added a verified-release site builder and automatic Pages publishing. Updated the README with the gallery and individual model links.
- Verified local desktop/mobile model loading, black backgrounds, six camera presets, variant switching and layout without overflow or browser errors. The SMW public export passed Godot 4.7.2 import (23 meshes, 10 materials, 6 embedded textures).
- Configured the Pages environment to accept `main` and version tags matching `*-v*`, so published model releases can deploy the gallery as well as main-branch updates.

- Added `rules.md` as the single source of repository instructions, with harness entrypoints for AGENTS-compatible tools, Claude Code, Gemini CLI, GitHub Copilot, Cursor, Windsurf and Cline.
- Required a changelog update in the same commit for every change, including documentation, rules and configuration. Model changes also require entries in each affected model's changelog.

## 2026-09-09 — Initial public collection

- Published the [SNES NTSC-U 0.1.0 baseline](assets/snes-ntsc-u/CHANGELOG.md), with neutral labels, editable Blender source, GLB and previews.
- Added independent model versions, release manifests, checksums, packaging tools and catalog validation in CI.
- Established CC BY-NC-ND 4.0 licensing for original contributions with explicit attribution and third-party rights notices.
