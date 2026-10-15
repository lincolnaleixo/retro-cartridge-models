# Nintendo 64 cartridge template — credits and scope

- Model reconstruction and original procedural surface maps: **Lincoln Aleixo**, https://github.com/lincolnaleixo/retro-cartridge-models
- Original contributions: **CC BY-NC-ND 4.0**, https://creativecommons.org/licenses/by-nc-nd/4.0/
- Geometry source: `tools/media_nintendo_64.py`. The shell is authored parametrically; no third-party mesh or factory CAD is included.
- Nintendo product design and marks, including the approximate molded rear wordmark, are excluded from the collection license. This independent reconstruction is not an official Nintendo asset.

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

The packed normal and roughness maps are original deterministic procedural images, not sampled photographs. The unprinted labels contain no game artwork. The [evidence record](../../../docs/nintendo-64-reference-evidence.json) distinguishes sourced dimensions from estimated molding details. No physical fit, exact reflectance or manufacturing accuracy is claimed. See the root [NOTICE.md](../../../NOTICE.md) for license scope.
