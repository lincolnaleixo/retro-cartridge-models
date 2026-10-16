# Changelog — PlayStation 1 — clear-tray jewel case template

## 0.3.0 — 2026-10-16

- Replaced overlapping alpha-plus-transmission plastic with a reviewed glossy alpha approximation so the clear case and printed spines remain readable across Blender, Godot and WebGL.
- Assigned the existing retaining hub and twelve spring fingers their own translucent material, making the mechanism visible without clouding the whole removable tray.
- Corrected the left tray edge that previously crossed the folded paper and overlaid ribs on the printed spine: thirty-five ribs and their web now fit behind the inner paper, and the complete edge rail moves inward without losing its width.
- Applied positive X transforms to exactly thirty-seven molded parts using evaluated bounds; retained their native polygon topology and UVs. A 0.10 mm modeled paper clearance is an assembly constraint, not a factory tolerance claim.
- Removed sixteen hidden broad page-stack caps, equivalent to thirty-two exported triangles, that competed in depth with the separate printed covers. Kept the visible page edges, printed surfaces, artwork UVs, paper envelope and original double-sided material flags; matched WebGL trials verified that removing the hidden caps resolves the inward booklet bands.
- Preserved all other native parts, referenced packed images and hinge endpoints; recorded the material, thirty-seven-part placement and hidden-page-cap exceptions in a hash-linked source audit.
- Kept the booklet faces opaque and correctly opposed, with independent exterior-front and inward-booklet artwork targets; the neutral template remains empty.
- Recorded actual-export previews and exact-input engine/source audits. Earlier box versions and separate disc assets remain unchanged by this template release.

## 0.2.0 — 2026-10-16

- Restored visibility of the clear disc tray, circular recess, retaining hub, ribs and lid rims by increasing transparent-material coverage and refining surface roughness.
- Retained transmission shading plus an alpha fallback for engines that do not import KHR_materials_transmission; reviewed the actual clear-plastic appearance in Blender and Godot.
- Updated the previous released editable source while preserving positions, normals, triangle indices, artwork UVs, hinge transforms and opening animation.
- Included new actual-export previews, exact-input engine and source validation reports; preserved the 0.1.0 release and separate CD models unchanged.

## 0.1.0 — 2026-10-16

- Added the first independent neutral box release with pristine materials, real packaging parts and separately addressable artwork targets.
- A standard-compatible 142.35 × 124.75 × 10.4 mm envelope with a separate front-lid pivot.
- Clear molded lid and removable tray with a central retaining hub and approximate rib, clip and hinge detail.
- Independent front booklet, booklet reverse, rear wrap and inner wrap artwork targets; spine folds share the tray-card UV field.
- The Open clip rotates the lid to 110 degrees. The standalone CD remains a separate media asset.
- Preserved meter scale, +Y up, +Z front and a bottom-center closed-envelope pivot; included one two-second Open animation in the portable export.
- Verified the actual exported poses, self-contained resources, named parts and UVs; imported and evaluated the animation in Godot and reopened the editable Blender source.
- Recorded source-specific approximation limits and retained existing cartridge and disc releases unchanged.
