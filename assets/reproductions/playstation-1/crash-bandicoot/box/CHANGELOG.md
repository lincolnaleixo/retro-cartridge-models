# Changelog — PlayStation 1 — Crash Bandicoot box reproduction

## 0.4.0 — 2026-10-16

- Adopted the independently released PlayStation box template v0.3.0, with lighter non-refractive clear plastic and a separately visible retaining hub so both spines remain readable in Blender, Godot and the web viewer.
- Kept the left tray ribbing behind the folded spine paper using the corrected template, removing the physical overlay across the lettering while preserving positive rail thickness.
- Removed the template's hidden page-stack cap faces beneath the booklet print, eliminating striped depth interference in WebGL while preserving the visible page edges and both original printed faces.
- Included the matching Crash Bandicoot disc v0.2.0 with its darker center annulus and hidden overlapping top faces removed, eliminating radial depth-fighting artifacts in the web viewer.
- Preserved the original SCUS-94900 artwork and printed UVs, with geometry and Open articulation matching the corrected neutral template; verified that the inward booklet image matches page 28 of the original manual.
- Included left and right side inspection views and a mounted-disc hub close-up, in addition to the six standard previews and exact-hash source, fit and engine validation.
- Clear-plastic materials use a portable alpha approximation; photographic references do not establish factory tooling dimensions.
- Preserved the box subset template positions, normals, artwork UVs, indices, hinge transforms and the two-second Open clip, verified through a complete decoded-data comparison. The exporter rounded 40 non-artwork UV scalars by at most 5.96e-08; this is recorded separately and does not change any printed-face UV coordinates.
- Validated the self-contained export, exact embedded artwork, Godot import and both animation endpoints, then reopened the editable Blender source.
- Kept all previously published template, box, cartridge and disc releases unchanged.

## 0.3.0 — 2026-10-16

- Refined all four original SCUS-94900 inserts for cleaner close-up print, treating illustrations, small type and solid fields separately.
- Preserved the original booklet/rear composition and the previously validated transparent case materials and articulation.
- Restored the matching 1994–2009 PlayStation vector wordmark and exact-wording NTSC U/C print; documented per-face changes and reconstruction limits.
- Preserved the box subset geometry and Open animation from the independently released playstation-1 template v0.2.0; artwork UVs match that selected template.
- Included the matching published cartridge or disc at its original scale beneath a removable Contents parent, preserving its geometry, materials and embedded images exactly.
- Included lossless prepared PNGs, source/edit provenance, six standard previews and exact-hash Blender/Godot validation; separately reviewed close-up renders of every exported face.
- Preserved the box subset template positions, normals, artwork UVs, indices, hinge transforms and the two-second Open clip, verified through a complete decoded-data comparison. The exporter rounded 64 non-artwork UV scalars by at most 5.96e-08; this is recorded separately and does not change any printed-face UV coordinates.
- Validated the self-contained export, exact embedded artwork, Godot import and both animation endpoints, then reopened the editable Blender source.
- Kept all previously published template, box, cartridge and disc releases unchanged.

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
