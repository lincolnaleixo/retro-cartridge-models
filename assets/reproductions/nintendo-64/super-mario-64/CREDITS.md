# Super Mario 64 reproduction — credits and scope

- Model reconstruction, UV mapping and material work: **Lincoln Aleixo**, https://github.com/lincolnaleixo/retro-cartridge-models
- Original modeling contributions: **CC BY-NC-ND 4.0**, https://creativecommons.org/licenses/by-nc-nd/4.0/
- Super Mario 64 artwork, Nintendo marks and underlying product design: **Nintendo**, excluded from the collection license. This independent visualization is not an official Nintendo asset.
- Shell geometry and original procedural ABS maps follow the [Nintendo 64 template](../../../templates/nintendo-64/README.md), refined for 0.2.0. Its [credits](../../../templates/nintendo-64/CREDITS.md) identify dimensional references, the newer close-up construction photographs and the official 2D logo source.
- Rear lettering and racetrack contours: **Nintendo**, from the inline `NintendoRacetrackLogoIcon` SVG on [Nintendo's official US website](https://www.nintendo.com/us/), retrieved on 2026-10-15. Version 0.2.0 replaces the earlier generic-font mark with these official 2D contours, scaled and adapted into an approximate molded island, recessed lettering and surrounding channel. Neither the contours nor Nintendo's product design and trademark are original modeling contributions licensed by this collection. Public website availability is not a permission grant.

## Artwork and photography sources

- Front: [MobyGames, Super Mario 64 Nintendo 64 media](https://www.mobygames.com/game/3533/super-mario-64/cover/group-5063/cover-28852/), [source image](https://cdn.mobygames.com/covers/4468624-super-mario-64-nintendo-64-media.jpg). The 1,200 × 799 photograph shows the original US K-A label, NUS-006 (USA) / NUS-NSME-USA, without Player's Choice marks. MobyGames is identified as the source host; individual photographer attribution and a redistribution license have not been established.
- Rear: [eBay original 1996 cartridge listing](https://www.ebay.com/itm/335375735854), [source image](https://i.ebayimg.com/images/g/YRgAAOSwQTVmLDDN/s-l1200.jpg). The 1,200 × 834 seller photograph shows the NUS-USA/CAN warning label with the 1996 Nintendo copyright line. Photographer identity and redistribution permission have not been established.

In versions 0.1.0 and 0.2.0, the original image files were used without pixel modification. The same two artwork source photographs, UV regions and print material settings are retained from 0.1.0 in the 0.2.0 refinement; no AI-generated, restored or recolored artwork is included. Source hashes and the applied UV coordinates belong in the generated artwork provenance. The newer iFixit, Not for Resale specimen and Video Game Gem Vault photographs inform shell construction only and do not replace the label edition or become additional embedded artwork. Photography and artwork remain third-party material even when packed inside a model instead of supplied as standalone files.

The maintainer requested this specific reproduction as part of the publication workflow on **2026-10-15**. That request and the attribution above do not transfer or establish publication rights in Nintendo artwork, marks or source photography. No redistribution license for those elements is asserted, and they remain outside the collection's CC BY-NC-ND grant. The repository's publication-rights requirement applies separately from technical package validation.

Dimensions, molding, photographic perspective and color are approximations. Official 2D contours do not establish the physical mark's depth, edge radii or exact molded proportions. Plastic grain, substrate color and screw finish remain visual estimates. The limited front source resolution restricts fine-print fidelity. Read the root [NOTICE.md](../../../../NOTICE.md) and [LICENSE](../../../../LICENSE).

## Pristine print restoration — 0.3.0

The front uses localized inpainting and a 2.5% saturation/contrast adjustment. The rear uses built-in image generation followed by measured image registration. Warning wording, MANUAL spelling, 1996 copyright and edition codes were visually checked.

Restoration was requested by the maintainer on October 16, 2026. It does not establish rights to the original artwork or source photography. The release includes exact input/output hashes, generation prompts where used, local-processing records and geometry-preservation evidence in `artwork-provenance.json` and `artwork-update-report.json`. Colors and reconstructed fine lettering remain visual approximations.
