# Nintendo 64 cartridge template — changelog

## Unreleased

No pending changes.

## 0.1.0 — 2026-10-15

- Added an original gray NTSC-U/C NUS-006 cartridge reconstruction with a nominal 116 × 76.6 × 18.5 mm envelope, bowed crown, curved cheeks, recessed label lands, two rear screw wells and a recessed 50-contact connector.
- Kept front and rear artwork surfaces separately named and unprinted, with face-correct 0–1 UVs. Added original packed ABS micrograin maps with a separate repeating surface UV domain.
- Documented community dimensions, photographic construction references and the distinction between the North American and PAL/AUS regional keys. The approximate molded Nintendo wordmark remains outside the model license.
- Development export checks: the neutral GLB passed the integrity/UV inspector with 18,861 triangles, ten meshes, nine materials and two embedded images. Source solid meshes were checked for manifold edges and positive volume.
- Passed Godot 4.7.2 import and label/UV checks. Reviewed seven views rendered from the exported GLB; packed Blender textures were reopened and private paths sanitized. Versioned packages include exact payload and archive checksums.
- Known limits: inferred radii, recess depths, rear label size and internal clearances; approximate rear wordmark; omitted hidden chips and complete shielding. No manufacturing or physical-fit claim is made.
