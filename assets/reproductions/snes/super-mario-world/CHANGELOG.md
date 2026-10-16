# Super Mario World example changelog

## Unreleased

- Moved this asset into `assets/reproductions/snes/super-mario-world/` so the repository groups actual files by console and game. Published manifests, preview images, packages, identifiers and import contracts are unchanged.

- Translated gallery descriptions, rights summaries and descriptive manifest notes into English at the owner's request. No geometry, artwork, release files, tags or checksums changed.

## 0.2.0 — 2026-10-16

- Synchronized the canonical `labels/front.png` with the packaged restored image for consumers using immutable tagged raw URLs; verified both canonical label hashes against the release payload.

- Repaired blue-field scan blemishes with localized original-print cloning and a thin scratch repair; retained the deliberate halftone, speed streaks, illustration, code and fold layout.
- Applied a restrained 4% saturation/contrast recovery only to the color panel; kept the subtle SNES emblem, rear label and other textures unchanged.
- Updated the standalone front PNG to exactly match the embedded GLB image; the standalone rear PNG remains byte-identical to 0.1.1. Geometry, UVs and materials remain unchanged.
- Validated packed-source reopening, unchanged non-image GLB buffers and UVs, actual-export render comparisons, and Godot 4.7.2 decoded textures with identical imported geometry, normals, UVs and transforms.
- Previous published packages, manifests and previews remain byte-identical. Restored title/warning typography and color are approximate; this is not a factory print master.

## 0.1.1 — 2026-09-17

- Added `labels/front.png` and `labels/rear.png`, extracted unchanged from the published GLB, so an application can paint the real label on the shared neutral `snes-ntsc-u` shell without loading the complete textured model.
- Recorded both label files with their sizes and SHA-256 in the version manifest, and packaged them with the source, GLB, renders and notices.
- Previews are unchanged from 0.1.0; no geometry, material or UV change.

Known limits: the label exports carry the same Nintendo artwork and trademark exclusion as the textured model; they add no license grant beyond what the asset already publishes.

## 0.1.0 — 2026-09-09

- Published the existing textured cartridge as a separate public example with its own version, source package and attribution.
- Preserved the restored front print, folded top title, rear warning label and Nintendo emblem.
- Retained the crowned roof, rounded grip details and blind lower latch recesses from the photo-reviewed geometry.
- Removed private paths, embedded scripts and internal metadata from the public editable source; no geometry or artwork redesign was introduced for this publication.
- Added hero, top, rear, side and underside inspection images to the public gallery. All previews are existing renders; no new visual-fidelity claim is made.
- Verified the public export in Godot 4.7.2 (23 meshes, 10 materials, 6 embedded textures) and in the gallery on desktop and mobile.

Known limits: approximate photo-derived geometry and reconstructed typography. Nintendo artwork and marks are excluded from the original-contributions license.
