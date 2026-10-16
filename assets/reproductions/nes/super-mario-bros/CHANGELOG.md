# NES — Super Mario Bros. reproduction — changelog

## Unreleased

No pending changes.

## 0.2.0 — 2026-10-16

- Removed neutral abrasion and cloudy wear from the black front label while retaining the original pixel illustration, motion streaks, star points, round seal and Made in Japan text.
- Replaced the blurred folded title and worn rear warning print with clean restored textures; preserved the early rear layout without REV-A.
- Registered the restored rear/top images into their existing photographed UV footprints; all model geometry, normals, transforms, UV bytes and non-artwork textures remain unchanged.
- Validated packed-source reopening, unchanged non-image GLB buffers and UVs, actual-export render comparisons, and Godot 4.7.2 decoded textures with identical imported geometry, normals, UVs and transforms.
- Previous published packages, manifests and previews remain byte-identical. Restored title/warning typography and color are approximate; this is not a factory print master.

## 0.1.0 — 2026-10-15

- Released the first separately versioned Super Mario Bros. (1985) reproduction on the early five-screw western NES shell.
- Selected the original early front layout with its round gold seal, the folded top title and a matching rear warning label without REV-A. Kept the unprinted template separately maintained.
- Mapped the original Golden Apple Comics front photograph and Fenyx Games top/rear regions through UV coordinates without modifying source pixels. Used sRGB print materials, roughness 0.68 and reduced dielectric specular reflection.
- Recorded the photography sources, lower-resolution top-fold limitation and maintainer's 2026-10-15 request without asserting a third-party rights grant. No generated, recolored or restored artwork is included.
- Known limits: oblique, low-resolution top-title photography; differing source lighting and wear; inferred shell details.
- Passed GLB integrity/UV inspection, Godot 4.7.2 import and named-surface checks. Reviewed seven actual-export views; reopened packed Blender sources after sanitizing private paths. Release manifests record the exact package checksums.
