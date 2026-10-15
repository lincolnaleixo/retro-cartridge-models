# Nintendo 64 — Super Mario 64 reproduction

**Version:** 0.2.0 · **Date:** 2026-10-15 · **Reconstruction:** Lincoln Aleixo

[Previous 0.1.0 release](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/nintendo-64-super-mario-64-v0.1.0) · [Changelog](CHANGELOG.md)

Super Mario 64 (1996) on the original North American gray NUS-006 cartridge. The front reproduces the original K-A label, identified as NUS-NSME-USA, without Player's Choice branding. The rear uses the original NUS-USA/CAN warning label dated 1996, rather than the later NUS-USA/CAN-1 revision.

Original photographed label regions are mapped onto the model through UV coordinates. Source pixels are not generated, repainted, recolored or retouched. The front comes from a near-frontal photograph hosted by MobyGames; the rear comes from a photographed original cartridge offered on eBay. Source provenance and rights limitations are listed in [credits](CREDITS.md).

Geometry and original ABS surface detail follow the [Nintendo 64 template](../../../templates/nintendo-64/README.md) 0.2.0 refinement: smoother crown and cheek shading, recessed official-source rear lettering on an approximate molded island, domed gold-toned Gamebit heads, a continuous black connector guide, tan exposed PCB tongue and more visible fine rear grain. The official website's 2D logo contours are identified separately in [credits](CREDITS.md); the modeled relief and dimensions remain approximate.

The nominal envelope remains 116 × 76.6 × 18.5 mm; units are meters, X is width, Y is up and +Z is front, with a bottom-center origin. Front and rear label dimensions, source photographs, UV mapping and print material settings are unchanged from 0.1.0. The original 1996 K-A edition is retained. This is a reconstruction for visualization, not Nintendo manufacturing CAD.

Printed artwork uses sRGB input, a white base-color tint, roughness 0.68 and reduced dielectric specular reflection. The front label region contains approximately 580 × 660 source pixels; its photographic perspective, lighting and fine-print resolution remain visible limitations. UV mapping does not recover missing detail or establish an exact printed color match. See the [owner-artwork workflow](../../../../docs/owner-artwork.md) for mapping and consumer material settings.

Version 0.2.0 contains 48,341 triangles in ten meshes, nine materials and four embedded images. The actual GLB passed integrity/UV inspection, comparable render review and Godot 4.7.2 import, surface/UV checks and five-format application smoke checks. Both saved Blender sources reopen with packed images and relative resource paths. The eight release previews include a native rear-detail render; the manifest records package checksums. The published 0.1.0 baseline includes editable Blender source, a self-contained GLB, seven actual-export preview views and checksummed release files; that package remains unchanged. This reproduction is maintained separately from the unprinted template. Publish and verify the revised model package before updating the consumer application.

Original modeling contributions are CC BY-NC-ND 4.0. Nintendo artwork, marks, underlying product design and source photography are excluded from that grant. Neither the maintainer's request nor these credits grant rights to the third-party elements. See [credits](CREDITS.md), [changes](CHANGELOG.md) and the root [NOTICE.md](../../../../NOTICE.md).
