# Nintendo 64 — Super Mario 64 reproduction — changelog

## Unreleased

No pending changes.

## 0.3.0 — 2026-10-16

- Removed the front photograph's thin scratch and isolated green-field spots with localized retouch; preserved the K-A rating, NUS-006 (USA), NUS-NSME-USA and original illustration.
- Restored the 1996 NUS-USA/CAN rear label to an even charcoal field and clean ivory print, removing scratches, chips and faded spots.
- Registered the restored rear image into the existing UV footprint; geometry, normals, indices, node transforms, all UV bytes, plastic maps and print material settings remain unchanged.
- Validated packed-source reopening, unchanged non-image GLB buffers and UVs, actual-export render comparisons, and Godot 4.7.2 decoded textures with identical imported geometry, normals, UVs and transforms.
- Previous published packages, manifests and previews remain byte-identical. Restored title/warning typography and color are approximate; this is not a factory print master.

## 0.2.0 — 2026-10-15

- Removed broad faceted crown highlights and pinched cheek/channel transitions by refining curved geometry, recess rims and split/weighted normals. The same camera and studio setup make the difference comparable with 0.1.0.
- Replaced thin raised generic lettering with recessed official-source Nintendo letter contours, a shallow molded island and rounded surrounding channel. The mark remains excluded from the original-model license; relief and scale are photographic estimates.
- Rebuilt the security heads with a round dome, six external shoulder lobes and a deeper recessed seat. Their warm metal finish is less glossy at close range.
- Extended the black connector guide into continuous walls around the tongue. The insertion edge now shows tan bare substrate below green solder mask, retaining 25 gold contacts per face at 2.50 mm pitch.
- Increased fine plastic detail, with stronger rear grain and a softer satin front. The 116 × 76.6 × 18.5 mm nominal envelope, axes, pivot and named label surfaces remain compatible.
- Final source-solid checks pass for all 73 solids: manifold edges, no degenerate faces and positive volume. Actual-export review confirms clean crown shading, recessed lettering and connector structure; Blender 5.2.2 LTS packed-source reopening, GLB/UV inspection and Godot 4.7.2 import, named surfaces, world bounds and five-format application checks pass. Eight actual-export previews and manifest checksums accompany the release.
- Preserved the published 0.1.0 source package, manifest and preview bytes unchanged.
- Retained the same Super Mario 64 front/rear photographs byte-for-byte, UV rectangles and sRGB print material settings. No image recoloring or restoration is included in this shell refinement.

## 0.1.0 — 2026-10-15

- Released the first separately versioned Super Mario 64 (1996) reproduction on the original NTSC-U/C Nintendo 64 shell.
- Selected the original US K-A NUS-NSME-USA front and the 1996 NUS-USA/CAN rear label. Kept the unprinted template separately maintained.
- Mapped unmodified photograph regions with UV coordinates and sRGB print materials, roughness 0.68 and reduced dielectric specular reflection. No generated, recolored or retouched artwork is included.
- Recorded source hosts, photographer-attribution limitations and the maintainer's 2026-10-15 request without treating attribution or that request as a rights grant.
- Known limits: approximately 580 × 660 front-label source pixels, photographed lighting and perspective, estimated shell details and no exact physical color-match claim.
- Passed GLB integrity/UV inspection, Godot 4.7.2 import and named-surface checks. Reviewed seven actual-export views; reopened packed Blender sources after sanitizing private paths. Release manifests record the exact package checksums.
