# PlayStation 1 — Crash Bandicoot box reproduction

**Version:** 0.1.0 · **Date:** 2026-10-16 · **Creator:** Lincoln Aleixo

A clean Crash Bandicoot clear-tray jewel case with original-edition booklet covers, both sides of the folded tray card and an articulated lid.

![Closed box](previews/0.1.0/hero.png)

![Open box](previews/0.1.0/open.png)

## Edition and contents

Selected edition: **Original US black-label SCUS-94900 presentation**. This reproduction uses the independently released [playstation-1 neutral box template](https://github.com/lincolnaleixo/retro-cartridge-models/tree/main/assets/templates/playstation-1/box), with the same packaging geometry, hinge hierarchy, normalized print UVs and opening animation. Cartridge and CD models remain separate assets; no game media is enclosed. Printed booklet covers, where present, surround approximate blank interior leaves rather than a complete reproduced manual.

The shell and print aim for a pristine, newly unboxed appearance. Local scan cleanup; no generated illustration or replacement lettering. Source printing and scan resolution are preserved. Fine paper texture and residual minor scan variation remain approximate. Complete four-part paper print set, including both rear spines. Mild edge wear. Clear tray verified by a physical US specimen with matching disc code. Case envelope uses midpoints of CMC assembly inspection ranges (142.35 × 124.75 × 10.4 mm); fine molding is approximate, and CMC is not established as the original Sony case supplier. See docs/playstation-box-reference-evidence.json. Restoration is a visual approximation rather than proof of original ink values, manufacturing tolerances or missing lettering. Upsampling does not add authentic detail. Paper texture, scan blur and small source imperfections may remain visible at close range.

## Prepared artwork

| Artwork slot | Approximate effective source pixels | Prepared image pixels | Release file |
| --- | --- | --- | --- |
| `Front` | 1425 × 1401 | 1425 × 1401 | `artwork/Front.png` in release ZIP |
| `WrapBack` | 1768 × 1368 | 1768 × 1368 | `artwork/WrapBack.png` in release ZIP |
| `BookletBack` | 1417 × 1404 | 1417 × 1404 | `artwork/BookletBack.png` in release ZIP |
| `WrapInside` | 1755 × 1380 | 1755 × 1380 | `artwork/WrapInside.png` in release ZIP |

Every listed PNG is embedded byte-for-byte in its GLB artwork slot and included separately in the release for reproducible application. The package contains the used prepared faces, their source citations and transformation provenance; it does not include unused research photographs or raw specimen images. Separate files do not grant additional rights to the artwork.

## Import and validation

| Property | Value |
| --- | --- |
| Units and axes | Meters; X width, Y up, +Z front |
| Pivot | Bottom center of the nominal closed envelope |
| Nominal closed size | 142.35 × 124.75 × 10.4 mm |
| Initial pose | Closed |
| Animation | `Open`, 0 to 2 seconds |

The self-contained GLB passed structural, image, UV, hierarchy and animation checks. Direct comparison with its neutral template verified identical positions, normals, artwork UVs, triangle indices, node transforms and animation keys. The exporter rounded 28 non-artwork UV scalars by at most 5.96e-08; this is recorded separately and does not change any printed-face UV coordinates. Godot 4.7.2-stable (official) imported and evaluated both animation endpoints; Blender 5.2.2 LTS reopened the packed editable source and checked both poses. Release reports bind these checks to exact binary hashes.

The envelope uses midpoint values from CMC assembly inspection ranges, not proof of the original Sony supplier. Fine molded features, booklet leaves and paper-fit dimensions are approximate. Clear plastic rendering depends on the importing engine. Transparent materials and printed-paper highlights can vary between renderers. Godot does not honor the exported specular extension; apply a printed-material specular level of 0.18 when matching the Blender preview lighting.

The release includes editable `.blend`, portable `.glb`, six previews, construction and reference evidence, prepared PNGs, provenance and validation reports. Run the repository's `tools/create_game_boxes.py` from the unpacked release directory, passing `--console playstation-1 --asset-id playstation-1-crash-bandicoot-box --artwork artwork-mapping.json --output regenerated`, to rebuild with the included artwork mapping.

See [credits](CREDITS.md) and [changelog](CHANGELOG.md). Original modeling contributions only: CC BY-NC-ND 4.0. Game artwork, marks, product designs, scans and source photography are excluded. Attribution and the maintainer's request do not grant rights to those elements.
