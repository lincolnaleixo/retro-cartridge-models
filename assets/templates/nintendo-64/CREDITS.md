# Nintendo 64 cartridge template — credits and scope

- Model reconstruction and original procedural surface maps: **Lincoln Aleixo**, https://github.com/lincolnaleixo/retro-cartridge-models
- Original contributions: **CC BY-NC-ND 4.0**, https://creativecommons.org/licenses/by-nc-nd/4.0/
- Geometry source: `tools/media_nintendo_64.py`. The shell is authored parametrically; no external 3D mesh or factory CAD is imported. Version 0.2.0 uses third-party official 2D logo contours for the rear mark, as identified below.
- Nintendo product design and marks, including the official 2D logo contours and the reconstructed rear relief, are excluded from the collection license. This independent reconstruction is not an official Nintendo asset.

## Rear wordmark source and reconstruction

Version 0.2.0 takes the Nintendo lettering and racetrack contours from the inline **`NintendoRacetrackLogoIcon`** SVG on [Nintendo's official US website](https://www.nintendo.com/us/), retrieved on **2026-10-15**. The source uses a `0 0 97 24` SVG viewBox. These are Nintendo's 2D trademark contours, not newly designed lettering and not an original logo contribution by the model author.

The contours are scaled and adapted into recessed geometry using close-up cartridge photographs to approximate the molded letter relief, central island and rounded surrounding channel. This replaces the generic font-based wordmark in 0.1.0. Official website artwork does not supply Nintendo 64 mold dimensions: scale, placement, depths, edge radii and the relationship between the island and channel remain estimates. No exact OEM mold, factory CAD or trademark license is claimed. Public availability of the SVG is not a permission grant, and the source mark remains outside CC BY-NC-ND 4.0.

## Dimensional and construction references

- [ConsoleMods cartridge dimensions](https://consolemods.org/wiki/Dimensions_for_Game_Cartridges): community-reported 116 × 76.6 × 18.5 mm envelope, credited there to gsx115.
- [ConsoleMods label templates](https://consolemods.org/wiki/Cart_Labels): 54.5 × 62.5 mm front label with a curved top and rounded corners. The Nintendo 64 row has no fit-confirmation mark; it is not a validated manufacturing dieline.
- [BWest's iFixit cartridge teardown](https://www.ifixit.com/Guide/Disassembling+Nintendo+64+Cartridge/3583): two rear security screws, bottom retaining tabs, board support and internal construction. The 3.8 mm specification describes the Gamebit driver, not a measured screw-head diameter.
- [ConsoleMods connector pinout](https://consolemods.org/wiki/N64:Connector_Pinouts): 50 contacts, arranged as 25 on each face.
- [bigbass1997's connector adapter documentation](https://github.com/bigbass1997/n64-ext-adapter): 2.5 mm pitch for the standard cartridge connector. Its separate EXT adapter dimensions are not used as cartridge PCB measurements.

## Photographic references

- [Evan-Amos, N64 Game Cartridge](https://commons.wikimedia.org/wiki/File:N64-Game-Cartridge.jpg): original public-domain photograph of an unlabeled shell and opened cartridge. Used to study the front molding and recessed connector; its pixels are not included in the template.
- [Original Super Mario 64 rear specimen](https://www.ebay.com/itm/335375735854) and [alternate rear specimen](https://www.ebay.com/itm/396287632714): seller photographs of the North American rear shell, warning-label land and regional keys. Photo reuse permission is not asserted; the photographs are references only for this template.
- [Natsukashii Retro PAL/AUS underside](https://natsukashiiretro.com/products/super-mario-64-untested): recessed connector and front lip. PAL/AUS regional key placement is deliberately not copied into the NTSC-U/C reconstruction.
- [BWest's iFixit teardown](https://www.ifixit.com/Guide/Disassembling+Nintendo+64+Cartridge/3583): closer rear, guide and exposed-PCB photographs support the 0.2.0 screw, black-guide and tan-substrate refinements. They are visual references rather than calibrated measurements.
- [US Not for Resale Super Mario 64 specimen](https://www.ebay.com/itm/277049491347): seller photographs of the crown, rear wordmark, domed screws and connector. This later specimen is used only for shell construction; its game-label edition is not substituted into the 1996 K-A reproduction.
- [Video Game Gem Vault original cartridge photograph](https://www.videogamegemvault.com/cdn/shop/files/N64-NINTENDO-64-VIDEO-GAME-CARTRIDGE-AUTHENTIC-SUPER-MARIO-64-FRONT-GAME-LABEL-PINS-TEETH.jpg?v=1742306460): near-frontal/underside view used to compare the recessed tongue, guide and cheek transitions. The associated product page returned 404 during the reference audit; the original image URL remained available. No redistribution permission is asserted.

The new close-up photographs are construction references only and are not embedded in the template. Their availability does not establish publication rights. The packed normal and roughness maps are original deterministic procedural images, not sampled photographs; the stronger rear grain is an artistic approximation, not measured surface reflectance. The unprinted labels contain no game artwork. The [evidence record](../../../docs/nintendo-64-reference-evidence.json) distinguishes sourced dimensions from estimated molding details. No physical fit, exact reflectance or manufacturing accuracy is claimed. See the root [NOTICE.md](../../../NOTICE.md) for license scope.
