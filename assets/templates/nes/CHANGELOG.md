# NES cartridge template — changelog

## Unreleased

No pending changes.

## 0.1.0 — 2026-10-15

- Added an original early western five-screw Game Pak reconstruction at a nominal 119.7 × 134 × 16.75 mm, with a left rib channel, recessed upper grips, five rear screw seats, stepped lower shoulders and an insertion triangle.
- Added a continuous 55 × 97 mm front/top label and a separate 78.5 × 31 mm rear label, both unprinted with face-correct UVs. Kept the rear molded mark land without Nintendo lettering.
- Added a recessed 72-contact connector at 2.5 mm pitch and original packed ABS normal/roughness maps. Corrected the interior cavity to follow the narrower lower shoulders, removing spurious side windows while keeping rib and foot relief inside the nominal envelope.
- Development validation in Blender 5.2.2 LTS: the neutral GLB passed the integrity/UV inspector with nine meshes, 22,480 triangles, seven materials and two embedded images. Generated views from the actual export include front, rear, top, underside and connector detail.
- Passed Godot 4.7.2 import and label/UV checks. Reviewed seven views rendered from the exported GLB; packed Blender textures were reopened and private paths sanitized. Versioned packages include exact payload and archive checksums.
