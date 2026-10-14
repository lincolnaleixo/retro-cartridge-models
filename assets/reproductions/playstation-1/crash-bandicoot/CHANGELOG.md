# PlayStation 1 — Crash Bandicoot disc example — changelog

## Unreleased

- Moved this asset into `assets/reproductions/playstation-1/crash-bandicoot/` so the repository groups actual files by console and game. Published manifests, preview images, packages, identifiers and import contracts are unchanged.

## 0.1.0 — 2026-10-13

- First separately versioned Crash Bandicoot (1996), SCUS-94900 standalone disc example; neutral playstation-1 0.1.0 remains unchanged.
- Applied AI-assisted approximate color restoration to the flat scan, using a photographed physical disc to replace its pink cast with an orange field, blue-violet ink and neutral gray silver areas. Fine lettering may differ from the original scan.
- Used sRGB artwork, roughness 0.68 and reduced print specular reflection. Silver print areas use gray albedo rather than a per-pixel metallic mask; the center hole, clear hub and dark reading face are preserved.
- Packaged the initial public release with packed editable Blender source, self-contained GLB, previews and source attribution. The preceding local example passed GLB inspection, packed-source reopening and Godot 4.7.2 import and preview checks.
- Verified the versioned ZIP and the full catalog, inspected the actual exported hero/top/bottom/rear renders, and confirmed that publication changes only root metadata in the GLB; geometry, materials and embedded texture bytes are unchanged. Sanitized packed-image, file-browser and render-output paths in the editable source.
