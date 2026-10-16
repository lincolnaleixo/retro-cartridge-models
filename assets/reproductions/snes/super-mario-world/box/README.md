# Super Nintendo — Super Mario World box reproduction

**Version:** 0.2.0 · **Date:** 2026-10-16 · **Creator:** Lincoln Aleixo

A pristine Super Mario World retail carton with printed panels, two articulated end closures and a removable folded cartridge tray.

![Closed box](previews/0.2.0/hero.png)

![Open box](previews/0.2.0/open.png)

## Edition and contents

Selected edition: **US retail cardboard-box presentation**. This reproduction uses the independently released [snes neutral box template v0.1.0](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/snes-box-v0.1.0), with the same packaging geometry, hinge hierarchy, normalized print UVs and opening animation. Cartridge and CD models remain separate assets; no game media is enclosed. Printed booklet covers, where present, surround approximate blank interior leaves rather than a complete reproduced manual.

The shell and print aim for a pristine, newly unboxed appearance. Original full rear scan restored with a continuous dark-ink curve; three creased lower-right trademark/copyright lines re-typeset with their exact original wording. Four edges reconstructed from archived matching period illustrations, title lettering and front-scan Nintendo capsule, with clean flat ink fields. Original side legal line re-typeset and gray striped motif traced from specimen. No generative imagery. Edges are a documented reconstruction, not a claim of a new factory-flat scan. Original rear source is 1143 × 800 pixels; enlargement does not add fine print information. Original Dry Bones landing artwork is 429 × 438 pixels. Colors are visually normalized; no physical ink calibration is available. Gray striped motif and legal-line typeface are close reconstructions with approximately placed layout. Edges are a documented reconstruction, not a claim of a new factory-flat scan. Original rear source is 1143 × 800 pixels; enlargement does not add fine print information. Original Dry Bones landing artwork is 429 × 438 pixels. Colors are visually normalized; no physical ink calibration is available. Gray striped motif and legal-line typeface are close reconstructions with approximately placed layout. Restoration is a visual approximation rather than proof of original ink values, manufacturing tolerances or missing lettering. Upsampling does not add authentic detail. Paper texture, scan blur and small source imperfections may remain visible at close range.

## Prepared artwork

| Artwork slot | Approximate effective source pixels | Prepared image pixels | Release file |
| --- | --- | --- | --- |
| `Front` | See per-face provenance | 2048 × 1437 | `artwork/Front.png` in release ZIP |
| `Back` | See per-face provenance | 2048 × 1437 | `artwork/Back.png` in release ZIP |
| `Top` | See per-face provenance | 2048 × 403 | `artwork/Top.png` in release ZIP |
| `Bottom` | See per-face provenance | 2048 × 403 | `artwork/Bottom.png` in release ZIP |
| `SpineLeft` | See per-face provenance | 403 × 1437 | `artwork/SpineLeft.png` in release ZIP |
| `SpineRight` | See per-face provenance | 403 × 1437 | `artwork/SpineRight.png` in release ZIP |

Every listed PNG is embedded byte-for-byte in its GLB artwork slot and included separately in the release for reproducible application. The package contains the used prepared faces, their source citations and transformation provenance; it does not include unused research photographs or raw specimen images. Separate files do not grant additional rights to the artwork.

## Import and validation

| Property | Value |
| --- | --- |
| Units and axes | Meters; X width, Y up, +Z front |
| Pivot | Bottom center of the nominal closed envelope |
| Nominal closed size | 179 × 128 × 31 mm |
| Initial pose | Closed |
| Animation | `Open`, 0 to 2 seconds |

The self-contained GLB passed structural, image, UV, hierarchy and animation checks. Direct comparison with its neutral template verified identical positions, normals, artwork UVs, triangle indices, node transforms and animation keys. Godot 4.7.2-stable (official) imported and evaluated both animation endpoints; Blender 5.2.2 LTS reopened the packed editable source and checked both poses. Release reports bind these checks to exact binary hashes.

Protector-fit dimensions establish an approximate envelope. Paper gauge, tray aperture, flap lengths and folds are inferred from photographs, not measured factory die lines. Transparent materials and printed-paper highlights can vary between renderers. Godot does not honor the exported specular extension; apply a printed-material specular level of 0.18 when matching the Blender preview lighting.

The release includes editable `.blend`, portable `.glb`, six previews, construction and reference evidence, prepared PNGs, provenance and validation reports. Run the repository's `tools/create_game_boxes.py` from the unpacked release directory, passing `--console snes --asset-id snes-super-mario-world-box --source snes-super-mario-world-box.blend --artwork artwork-mapping.json --output regenerated`, to rebuild with the included artwork mapping while preserving the published source geometry.

See [credits](CREDITS.md) and [changelog](CHANGELOG.md). Original modeling contributions only: CC BY-NC-ND 4.0. Game artwork, marks, product designs, scans and source photography are excluded. Attribution and the maintainer's request do not grant rights to those elements.
