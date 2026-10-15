# Owner artwork and published examples

Publish the model repository first; consumers pin its released GLBs and do not recreate geometry. The reusable `tools/apply_media_artwork.py` tool applies a supplied label locally and exports a self-contained GLB and packed Blender source. It does not download artwork or publish its output. Local generation remains the default; future publication is a separate maintainer decision subject to the repository's rights and attribution rules.

The [Sonic the Hedgehog Mega Drive example](../assets/reproductions/mega-drive/sonic-the-hedgehog/README.md), [Crash Bandicoot PlayStation disc example](../assets/reproductions/playstation-1/crash-bandicoot/README.md), [Super Mario 64 reproduction](../assets/reproductions/nintendo-64/super-mario-64/README.md) and [Super Mario Bros. reproduction](../assets/reproductions/nes/super-mario-bros/README.md) are separately versioned from their unprinted templates, with their own manifests and source credits. The collection license applies to original modeling contributions; included third-party artwork, marks and photography remain outside its scope.

## Supported models

| `--model` | Front artwork | Separate `--top` | Optional `--rear` |
| --- | --- | --- | --- |
| `mega-drive` | 74 × 67 mm unfolded label | Top 7 mm fold | 77.75 × 21.75 mm rear panel |
| `playstation-1` | Square image mapped to the disc's printable annulus | No top fold | No rear label surface |
| `nintendo-64` | 54.5 × 62.5 mm arched label | No top fold | Approximately 80.9 × 38.9 mm warning label |
| `nes` | Approximately 55 × 97 mm unfolded label | Top 7 mm fold | Approximately 78.5 × 31 mm warning label |

The Nintendo 64 model targets the North American NUS-006 shell. The NES model targets the early western five-screw shell. Label sizes and molding details have the source limitations recorded in each template's credits.

For supplied flat artwork covering each label's full domain:

```sh
blender --factory-startup -b --python tools/apply_media_artwork.py -- --model mega-drive --front /path/to/unfolded-label.png --title "Sonic the Hedgehog (1991)" --output dist/owner-examples/mega-drive
blender --factory-startup -b --python tools/apply_media_artwork.py -- --model playstation-1 --front /path/to/disc-label.png --title "Crash Bandicoot (1996)" --output dist/owner-examples/playstation-1
blender --factory-startup -b --python tools/apply_media_artwork.py -- --model nintendo-64 --front /path/to/front-label.png --rear /path/to/rear-label.png --title "Super Mario 64 (1996)" --output dist/owner-examples/nintendo-64
blender --factory-startup -b --python tools/apply_media_artwork.py -- --model nes --front /path/to/front-face.png --top /path/to/top-title.png --rear /path/to/rear-label.png --title "Super Mario Bros. (1985)" --output dist/owner-examples/nes
```

With no `--top`, the Mega Drive and NES front input covers the complete unfolded label. With `--top`, the front input covers the front face and the separate top image covers the fold; both remain on the continuous `FrontLabel` mesh with separate material regions. The disc's annular mesh excludes the outside and center from the printable surface. An optional rear image maps to `RearLabel`; omitting it leaves the template's unprinted rear surface.

## Map regions of a photograph

The source photograph can contain the whole cartridge. Select its printed region through UV coordinates without cropping, repainting or resampling the input image:

- `--front-rect`, `--top-rect` and `--rear-rect` accept four normalized values in **left, bottom, right, top** order. The default `0 0 1 1` uses the whole image. Reversed bounds flip the selected region.
- `--front-quad`, `--top-quad` and `--rear-quad` accept eight normalized values: the `(u, v)` pairs for **bottom-left, bottom-right, top-right, top-left**, in that order. A quadrilateral takes precedence over the corresponding rectangle.

UV coordinates start at the image's bottom-left corner. For a pixel position `(x, y)` measured from the image's top-left in an image of width `W` and height `H`, use `u = x / W` and `v = 1 - y / H`. Choose corner order according to the intended upright label, accounting for the photo's orientation.

Quadrilateral mapping uses bilinear interpolation and suits nearly frontal photographs with a small rotation or keystone distortion. It is not a full camera-perspective reconstruction and cannot remove glare, compensate for curved paper, or recover illegible lettering. Prefer neutral lighting and sufficiently detailed source regions. The source image remains unchanged; the model's UVs determine which region is sampled.

The tool writes `artwork-provenance.json` alongside the GLB and packed Blender source. It records source hashes, image byte counts, rectangle/quadrilateral coordinates and print material settings without private machine paths. Its `publicationRights: "not-established"` value describes a limitation, not a technical validation failure or a permission grant. The tool does not establish rights or publish output.

## Print materials and consumer import

Artwork uses an explicit sRGB input, white base-color tint, nonmetallic ink, roughness 0.68 and Blender Specular IOR Level 0.18 (exported as `KHR_materials_specular.specularFactor` 0.36). This reduces the broad white reflections that previously washed out dark ink. The provenance also records these material settings. Review color under neutral white lighting with exposure low enough to avoid clipping; a saturated or faded source scan still needs correction before applying it. Prefer original-resolution artwork over resized product thumbnails.

Godot 4.7.2 imports the texture and roughness but ignores the exported specular extension. An owner-artwork consumer should duplicate each printed material on `FrontLabel` and `RearLabel`, including any separate top-fold material, and set `metallic_specular` to 0.18 while preserving its texture and other properties. Apply this only to printed surfaces, leaving unprinted shell materials and optical hub, matrix and rim materials intact.

## Example sources and limitations

The Crash example uses a [photographed SCUS-94900 disc](https://www.ebay.com/itm/186116411851) to distinguish the orange printed field, blue-violet ink and exposed silver areas from the pink/yellow cast of the scan. The release includes an AI-assisted restoration of the flat scan; the reference photograph is not included. Photo-based color restoration is approximate, and fine lettering may differ from the original scan. Silver areas use gray albedo without a per-pixel metallic mask. Neutral releases contain none of this game artwork.

Game references: Sonic the Hedgehog (1991), western PAL cartridge; Crash Bandicoot (1996), SCUS-94900 disc. The Sonic example embeds original-resolution product photographs from [Grillo Games](https://www.grillogames.de/products/sega-mega-drive-spiel-sonic-the-hedgehog-modul-anleitung-ovp-sehr-guter-z), selecting the front and top labels through UV mapping without modifying image bytes. The Crash restoration is based on the [PSX Data Center disc scan](https://psxdatacenter.com/games/U/C/SCUS-94900.html), whose entry credits SPECIALT1212 for high-resolution covers. Each example's credits and provenance identify its sources. SEGA, Sony, Universal and Naughty Dog artwork/marks, scans and photography remain outside the model license; source attribution is not a rights grant.

Super Mario 64 (1996) uses the original US K-A NUS-NSME-USA front label from a [MobyGames-hosted photograph](https://www.mobygames.com/game/3533/super-mario-64/cover/group-5063/cover-28852/) and the original 1996 NUS-USA/CAN rear from a [photographed eBay specimen](https://www.ebay.com/itm/335375735854). The visible front region has approximately 580 × 660 source pixels, limiting fine-print detail. Player's Choice artwork and the later NUS-USA/CAN-1 rear are not substituted.

Super Mario Bros. (1985) uses the early five-screw label with the round gold seal. The main front comes from the 3,750 × 4,216 [Golden Apple Comics photograph](https://goldenapplecomics.com/products/nintendo-nes-super-mario-bros-video-game-cartridge); the top fold and rear warning label without REV-A come from the [Fenyx Games five-screw specimen](https://www.fenyxgames.com/product-page/super-mario-bros-nes-5-screw-1985-nintendo). The small oblique top region has lower detail than the main front, and differing source lighting or wear can remain visible.

Both Nintendo reproductions use unmodified source pixels, with no generated, restored or recolored artwork. The maintainer requested them as part of the publication workflow on 2026-10-15. That request does not establish rights in Nintendo artwork, marks or the source photographs, and no redistribution license for those elements is asserted. Their credits retain these limitations explicitly; packing the photographs inside a model does not change their rights. Technical package verification is separate from those rights questions.
