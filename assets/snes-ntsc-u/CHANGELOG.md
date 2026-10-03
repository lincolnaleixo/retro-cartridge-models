# SNES NTSC-U changelog

## Unreleased

- Added a reproducible development refinement from the verified 0.1.0 Blender source. Front and back shell edges receive a clamped 0.12 mm bevel; a packed 512 px roughness map gives ABS a subtle grain and softens its previously glossy response. The unprinted label now has a matte paper finish.
- Retained the continuous folded front label, label UVs, model axes, units and pivot. Before/after hero, top and underside views use the same camera framing, studio lights and Cycles settings. This is a visualization refinement with approximate dimensions, not a manufacturing model or a new published version.
- Reviewed the actual matched renders and validated the self-contained GLB: 22 meshes, 9 materials, 5 embedded images and 85,772 triangles, versus 66,028 triangles in the baseline. The small bevel uses one segment to limit added geometry; the Blender source keeps it editable. Engine render verification is recorded with the consumer preview.

- Translated the gallery title, description, rights summary and interface to English; the model and release package are unchanged.

- Added the unchanged 0.1.0 model to the public gallery with orbit/zoom, six camera presets, version selection and release links. The existing model package and preview hashes are preserved.

## 0.1.0 — 2026-09-09

Initial public baseline, derived from the latest photo-reviewed reconstruction.

- Crowned the top across the front/back depth; the folded label follows the curve.
- Replaced the earlier through-hole interpretation of the lower latch recesses with blind pockets and solid backing webs, based on new underside photographs.
- Softened wing-roof edges and side grip-mouth edges.
- Used gray molded ABS for connector supports and small plastic details.
- Regenerated shell surface maps after geometry changes.
- Prepared a public neutral-label edition; removed the game print and logo mesh, then rebaked rear occlusion to remove the logo's residual shadow.
- Included editable Blender source, portable GLB, three comparable views, file checksums and version-specific release metadata.

Known limits: approximate reference-based measurements; no official CAD, caliper-certified fit or injection-mold specification. This version is the first public baseline, not a claim of photogrammetric equivalence.
