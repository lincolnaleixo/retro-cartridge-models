# Changelog — PlayStation 1 — Crash Bandicoot box reproduction

## 0.2.0 — 2026-10-16

- Reduced coarse scanned halftone and color noise across the four paper inserts, using a gentler filter for fine rear legal type.
- Restored the plain black spine fields and narrow booklet trim, retaining the original SCUS-94900 lettering and complete rear layout.
- Adopted the neutral template clear-plastic revision: shell, rim and tray alpha of 0.16, 0.35 and 0.25 make molded details visible while retaining the Godot Compatibility transparency fallback.
- Used the independently released playstation-1 box template v0.2.0; retained its decoded geometry, artwork UVs and Open animation.
- Included the revised prepared PNGs, transformation provenance and hash-bound Blender/Godot validation.
- Preserved template positions, normals, artwork UVs, indices, hinge transforms and the two-second Open clip, verified through a complete decoded-data comparison. The exporter rounded 32 non-artwork UV scalars by at most 5.96e-08; this is recorded separately and does not change any printed-face UV coordinates.
- Validated the self-contained export, exact embedded artwork, Godot import and both animation endpoints, then reopened the editable Blender source.
- Kept all previously published template, box, cartridge and disc releases unchanged.

## 0.1.0 — 2026-10-16

- Added the first independently versioned Crash Bandicoot box reproduction using the neutral playstation-1 box template.
- Applied edition-specific prepared print to each artwork slot, retaining unprinted interior stock and pristine packaging materials.
- Included the actual prepared PNG faces and per-slot source, edit and image-hash provenance; recorded restoration and resolution limits.
- Preserved template positions, normals, artwork UVs, indices, hinge transforms and the two-second Open clip, verified through a complete decoded-data comparison. The exporter rounded 28 non-artwork UV scalars by at most 5.96e-08; this is recorded separately and does not change any printed-face UV coordinates.
- Validated the self-contained export, exact embedded artwork, Godot import and both animation endpoints, then reopened the editable Blender source.
- Kept existing neutral templates, cartridge and disc releases unchanged.
