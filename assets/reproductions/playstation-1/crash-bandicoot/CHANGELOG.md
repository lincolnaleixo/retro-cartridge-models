# Changelog — PlayStation 1 — Crash Bandicoot disc example

## 0.2.0 — 2026-10-16

- Replaced the nearly invisible clamping center and broad silver matrix band with a darker smoke-tinted center and dedicated dark transition; preserved the outer reflective rim.
- Removed only 512 hidden body-top triangles 5 micrometers beneath the printed face, eliminating radial depth-fighting artifacts in the actual WebGL viewer.
- Preserved 120 mm outer diameter, 15 mm true center hole, 1.2 mm thickness, original positions/normals/UVs, all other triangle indices, node transforms and embedded image bytes; retained the bottom-center meter-scale import contract.
- Reopened the original 0.1.0 editable source, updated its release identification, and included strict patch/source validation, matching actual-export previews and Godot import comparisons. Earlier releases are unchanged.
- Retained the exact previously restored Crash artwork and its original provenance; this release changes disc construction/materials, not the print restoration.

## Unreleased

- Moved this asset into `assets/reproductions/playstation-1/crash-bandicoot/` so the repository groups actual files by console and game. Published manifests, preview images, packages, identifiers and import contracts are unchanged.

## 0.1.0 — 2026-10-13

- First separately versioned Crash Bandicoot (1996), SCUS-94900 standalone disc example; neutral playstation-1 0.1.0 remains unchanged.
- Applied AI-assisted approximate color restoration to the flat scan, using a photographed physical disc to replace its pink cast with an orange field, blue-violet ink and neutral gray silver areas. Fine lettering may differ from the original scan.
- Used sRGB artwork, roughness 0.68 and reduced print specular reflection. Silver print areas use gray albedo rather than a per-pixel metallic mask; the center hole, clear hub and dark reading face are preserved.
- Packaged the initial public release with packed editable Blender source, self-contained GLB, previews and source attribution. The preceding local example passed GLB inspection, packed-source reopening and Godot 4.7.2 import and preview checks.
- Verified the versioned ZIP and the full catalog, inspected the actual exported hero/top/bottom/rear renders, and confirmed that publication changes only root metadata in the GLB; geometry, materials and embedded texture bytes are unchanged. Sanitized packed-image, file-browser and render-output paths in the editable source.
