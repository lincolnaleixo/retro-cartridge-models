# Collection changelog

Model release histories also live in `assets/<asset-id>/CHANGELOG.md`.

## Unreleased

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
