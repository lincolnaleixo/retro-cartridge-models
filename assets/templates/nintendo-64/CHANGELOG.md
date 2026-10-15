# Nintendo 64 cartridge template — changelog

## Unreleased

No pending changes.

## 0.2.0 — 2026-10-15

- Removed broad faceted crown highlights and pinched cheek/channel transitions by refining curved geometry, recess rims and split/weighted normals. The same camera and studio setup make the difference comparable with 0.1.0.
- Replaced thin raised generic lettering with recessed official-source Nintendo letter contours, a shallow molded island and rounded surrounding channel. The mark remains excluded from the original-model license; relief and scale are photographic estimates.
- Rebuilt the security heads with a round dome, six external shoulder lobes and a deeper recessed seat. Their warm metal finish is less glossy at close range.
- Extended the black connector guide into continuous walls around the tongue. The insertion edge now shows tan bare substrate below green solder mask, retaining 25 gold contacts per face at 2.50 mm pitch.
- Increased fine plastic detail, with stronger rear grain and a softer satin front. The 116 × 76.6 × 18.5 mm nominal envelope, axes, pivot and named label surfaces remain compatible.
- Final source-solid checks pass for all 73 solids: manifold edges, no degenerate faces and positive volume. Actual-export review confirms clean crown shading, recessed lettering and connector structure; Blender 5.2.2 LTS packed-source reopening, GLB/UV inspection and Godot 4.7.2 import, named surfaces, world bounds and five-format application checks pass. Eight actual-export previews and manifest checksums accompany the release.
- Preserved the published 0.1.0 source package, manifest and preview bytes unchanged.

## 0.1.0 — 2026-10-15

- Added an original gray NTSC-U/C NUS-006 cartridge reconstruction with a nominal 116 × 76.6 × 18.5 mm envelope, bowed crown, curved cheeks, recessed label lands, two rear screw wells and a recessed 50-contact connector.
- Kept front and rear artwork surfaces separately named and unprinted, with face-correct 0–1 UVs. Added original packed ABS micrograin maps with a separate repeating surface UV domain.
- Documented community dimensions, photographic construction references and the distinction between the North American and PAL/AUS regional keys. The approximate molded Nintendo wordmark remains outside the model license.
- Development export checks: the neutral GLB passed the integrity/UV inspector with 18,861 triangles, ten meshes, nine materials and two embedded images. Source solid meshes were checked for manifold edges and positive volume.
- Passed Godot 4.7.2 import and label/UV checks. Reviewed seven views rendered from the exported GLB; packed Blender textures were reopened and private paths sanitized. Versioned packages include exact payload and archive checksums.
- Known limits: inferred radii, recess depths, rear label size and internal clearances; approximate rear wordmark; omitted hidden chips and complete shielding. No manufacturing or physical-fit claim is made.
