# NES — early five-screw cartridge template

**Version:** 0.1.0 · **Date:** 2026-10-15 · **Reconstruction:** Lincoln Aleixo

An original parametric reconstruction of the western gray NES Game Pak in its early five-screw form. The nominal envelope is 119.7 × 134 × 16.75 mm. It follows the photographed flat-top shell with a left rib channel, upper finger recesses, five rear screw seats, stepped lower shoulders and an engraved insertion triangle. It does not represent the later three-screw REV-A shell. See [credits](CREDITS.md) and [measurement evidence](../../../docs/nes-reference-evidence.json).

The tall front label continues over the top edge. The front and rear artwork surfaces are unprinted, and the rear molded mark land omits Nintendo lettering. No game artwork, reference photograph or third-party geometry is included. Original procedural normal and roughness maps approximate clean molded ABS without adding artificial wear.

Generate editable Blender source, a self-contained GLB and development views from the repository root:

```sh
blender -b --python tools/create_media_models.py -- --only nes
```

Outputs go to `dist/development/nes/`. The source keeps shell details and contacts separately editable; `tools/media_nes.py` regenerates the geometry. Static export parts are grouped while named artwork surfaces remain separate. Both original surface maps are packed in the Blender source and embedded in the GLB.

## Import contract

| Property | Value |
| --- | --- |
| Root | `NES` |
| Units and axes | Meters; X width, Y up, +Z front |
| Origin | Bottom center, Y = 0 |
| Nominal envelope | 119.7 × 134 × 16.75 mm |
| Front artwork mesh | `FrontLabel`; 55 × 97 mm unfolded; approximately 90 mm front face and 7 mm top fold |
| Rear artwork mesh | `RearLabel`; 78.5 × 31 mm |
| Artwork UVs | UV0, full 0–1 unfolded domain; upright and unmirrored when viewing each face |
| Connector | 72 contacts, 36 per face, at 2.5 mm pitch |

Development validation recorded nine exported meshes, 22,480 triangles, seven materials and two embedded images, with the GLB integrity/UV inspector passing. Actual-export views were generated for the front, rear, top, underside and connector. Final validation also passed Godot 4.7.2 import, named-label/UV surface checks, world-bound checks and actual-export render review. The release manifest records exact package checksums.

Shell dimensions are approximate published measurements. Rib placement, recess depths, fillets, screw details and internal supports are inferred from photographs. Hidden ROM electronics are omitted. This is a visualization asset, not a tested printable replacement shell. See [changes](CHANGELOG.md) and the separately documented [Super Mario Bros. reproduction](../../reproductions/nes/super-mario-bros/README.md).
