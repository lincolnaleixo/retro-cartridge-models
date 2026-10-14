# Mega Drive — Sonic the Hedgehog example — changelog

## Unreleased

- Moved this asset into `assets/reproductions/mega-drive/sonic-the-hedgehog/` so the repository groups actual files by console and game. Published manifests, preview images, packages, identifiers and import contracts are unchanged.

## 0.1.0 — 2026-10-13

- First separately versioned Sonic the Hedgehog (1991) example on the existing western Mega Drive shell; neutral mega-drive 0.1.0 remains unchanged.
- Mapped original 2992 × 2992 front and top product photographs without modifying their image bytes; the front artwork region has approximately 954 × 748 source pixels.
- Used sRGB artwork, roughness 0.68 and reduced print specular reflection; kept original ABS surface maps, axes, dimensions and label UVs.
- Packaged the initial public release with packed editable Blender source, self-contained GLB, previews and source attribution. The preceding local example passed GLB inspection, packed-source reopening and Godot 4.7.2 import and preview checks.
- Verified the versioned ZIP and the full catalog, inspected the actual exported hero/top/bottom/rear renders, and confirmed that publication changes only root metadata in the GLB; geometry, materials and embedded texture bytes are unchanged. Sanitized packed-image, file-browser and render-output paths in the editable source.
