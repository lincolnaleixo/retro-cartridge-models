# Retro Cartridge Models

Versioned 3D cartridge reconstructions by **Lincoln Aleixo**. Each model has editable Blender sources, a portable GLB, preview images, a changelog and checksums tied to a release.

**[Explore the public 3D gallery →](https://lincolnaleixo.github.io/retro-cartridge-models/)**

Rotate each model on a black background, inspect six camera angles, browse renders and select published versions on desktop or mobile.

![SNES cartridge — neutral labels](assets/snes-ntsc-u/previews/0.1.0/hero.png)

## Models

| Model | Current version | Files | Changes |
| --- | --- | --- | --- |
| [SNES — early North American shell](assets/snes-ntsc-u/README.md) | 0.1.0 | [Download release](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/snes-ntsc-u-v0.1.0) | [Changelog](assets/snes-ntsc-u/CHANGELOG.md) |
| [SNES — Super Mario World example](assets/snes-super-mario-world/README.md) | 0.1.1 | [Download release](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/snes-super-mario-world-v0.1.1) | [Changelog](assets/snes-super-mario-world/CHANGELOG.md) |
| [Mega Drive — western cartridge](assets/mega-drive/README.md) | 0.1.0 | [Download release](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/mega-drive-v0.1.0) | [Changelog](assets/mega-drive/CHANGELOG.md) |
| [PlayStation 1 — standalone CD](assets/playstation-1/README.md) | 0.1.0 | [Download release](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/playstation-1-v0.1.0) | [Changelog](assets/playstation-1/CHANGELOG.md) |

### Super Mario World example

[![Super Mario World example](assets/snes-super-mario-world/previews/0.1.0/hero.png)](https://lincolnaleixo.github.io/retro-cartridge-models/#snes-super-mario-world)

The existing textured demonstration is also available in the gallery and as its own versioned package. Nintendo artwork and marks are excluded from the original-contributions license; [source credits and rights scope](assets/snes-super-mario-world/CREDITS.md) remain explicit.

The initial public model uses neutral, unprinted labels. It includes the curved top, the label folded around that curve, rounded side details, and blind lower latch recesses with solid backing. Dimensions are estimates from physical references, not official manufacturing drawings.

## Download and use

### Mega Drive and PlayStation

The [Mega Drive cartridge](assets/mega-drive/README.md) and [standalone PlayStation CD](assets/playstation-1/README.md) now have neutral 0.1.0 packages in the catalog. PlayStation uses only the CD; the earlier case study remains historical source. [Owner-supplied Sonic and Crash artwork](docs/owner-artwork.md) can be applied locally without changing the released neutral models.

The geometry follows [documented dimensional evidence](docs/measurement-evidence-2026-10-02.json). These are visualization reconstructions, not certified replacement parts. The SNES surface refinement remains development work; its published baseline is unchanged.

Generate the two new models with Blender 5.2.2:

```sh
blender --factory-startup -b --python tools/create_media_models.py -- --output dist/development
```

For the SNES refinement, download and verify the 0.1.0 package above, extract it locally, then run:

```sh
blender --factory-startup -b path/to/snes-ntsc-u.blend --python tools/refine_snes.py -- dist/development/snes-ntsc-u
python3 tools/inspect_glb.py dist/development/snes-ntsc-u/snes-ntsc-u.glb
python3 tools/verify.py
```

Generated sources, GLBs and renders remain in the ignored `dist/` directory. Review actual exports and engine import before preparing a versioned release; existing packages and checksums stay unchanged.

Download the model package from its release. It contains the `.blend`, self-contained `.glb`, previews, license, credits and a file manifest. The GLB uses meters: **X = width, Y = up, +Z = front**, with its origin near the bottom connector center. Import it into Godot or another glTF-compatible tool at scale 1.

Large source/export files live in versioned release packages; Git tracks the catalog, manifests, documentation, tools and previews. The download address and SHA-256 of each package are recorded in Git. You can retrieve a specific version and compare it with the next one without guessing which file is current.

```sh
python3 tools/verify.py
python3 tools/verify.py --download snes-ntsc-u 0.1.0
```

See [VERSIONING.md](VERSIONING.md) for the release workflow and comparison rules.

Before contributing changes, read [rules.md](rules.md). Every change requires a [collection changelog](CHANGELOG.md) update; model changes also belong in that model's changelog.

## Gallery publishing

The GitHub Pages gallery is generated from `catalog.json` and the version manifests. Add a model's display title, description, credits and rights summary to the catalog; publish its verified release package. The Pages workflow builds and deploys on main-branch changes and published releases.

To preview locally, run `python3 tools/build_site.py`, then `python3 -m http.server 8080 --directory _site`. The builder downloads and verifies release archives and copies only the site, GLBs, previews and public notices into `_site`. Model binaries stay outside Git; the browser loads them from the same Pages origin. `site/vendor/` contains the pinned viewer and its software license.

## License and attribution

Original contributions are licensed under **[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)**: attribution is required, commercial use is not licensed, and adapted material may not be redistributed under this license. The full terms are in [LICENSE](LICENSE). This is a public, source-available collection, not an OSI open-source software project.

Suggested credit:

> SNES NTSC-U cartridge reconstruction v0.1.0 by Lincoln Aleixo — Retro Cartridge Models — CC BY-NC-ND 4.0. https://github.com/lincolnaleixo/retro-cartridge-models

Existing hardware designs, product names, trademarks and any separately identified third-party content are outside this license grant. See [NOTICE.md](NOTICE.md) and [CREDITS.md](CREDITS.md). This collection is independent and is not affiliated with Nintendo.
