# Changelog — Mega Drive — western clamshell box template

## 0.3.0 — 2026-10-16

- Cleared the published full-size Mega Drive cartridge by moving four internal corner supports outward by 0.4 mm and lifting the upper profiles of the two spring clips by 1.8 mm while retaining their anchored feet.
- Reopened the 0.2.0 editable source and confined the geometry change to those six internal parts; preserved exterior dimensions, artwork UVs, materials, insertion anchor, hinges and opening animation.
- Recorded exporter reindexing in the two affected static material groups, compensated group-origin movement and tiny rounding on unprinted UVs; the native polygon topology and UV arrays remain unchanged.
- Retained an empty neutral template. Matching published game media is composed separately into game reproductions at its original scale.
- Verified the final exported scene and both opening endpoints in Godot, reopened the editable source, and recorded scoped migration and approximate fit evidence. Published earlier versions remain unchanged.

## 0.2.0 — 2026-10-16

- Corrected the spine artwork U direction so lettering reads normally from outside the left edge rather than appearing mirrored.
- Applied the same idempotent correction when reopening a previous editable source; only SpinePrint U coordinates change, with V, vertices, normals, indices, hinges and animation retained.
- Added a printed-face handedness regression check, actual-export spine proofs and hash-bound Blender/Godot validation.
- Preserved the 0.1.0 release and every separate cartridge, disc and other box release unchanged.

## 0.1.0 — 2026-10-16

- Added the first independent neutral box release with pristine materials, real packaging parts and separately addressable artwork targets.
- Hollow black molded front and rear shells with two separate spine pivots and a 180-degree open spread.
- Independent clear cover sleeve above the unprinted front, spine and rear paper surfaces.
- Opposing sideways cartridge guides with spring tongues, booklet retainers, snap details and tooling witness marks.
- The intact retail hanger is a named separate part. A neutral booklet placeholder and cartridge placement anchor remain editable.
- Preserved meter scale, +Y up, +Z front and a bottom-center closed-envelope pivot; included one two-second Open animation in the portable export.
- Verified the actual exported poses, self-contained resources, named parts and UVs; imported and evaluated the animation in Godot and reopened the editable Blender source.
- Recorded source-specific approximation limits and retained existing cartridge and disc releases unchanged.
