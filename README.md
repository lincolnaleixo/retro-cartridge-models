# Retro Cartridge Models

Versioned 3D cartridge reconstructions by **Lincoln Aleixo**. Each model has editable Blender sources, a portable GLB, preview images, a changelog and checksums tied to a release.

![SNES cartridge — neutral labels](assets/snes-ntsc-u/previews/0.1.0/hero.png)

## Models

| Model | Current version | Files | Changes |
| --- | --- | --- | --- |
| [SNES — early North American shell](assets/snes-ntsc-u/README.md) | 0.1.0 | [Download release](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/snes-ntsc-u-v0.1.0) | [Changelog](assets/snes-ntsc-u/CHANGELOG.md) |

The initial public model uses neutral, unprinted labels. It includes the curved top, the label folded around that curve, rounded side details, and blind lower latch recesses with solid backing. Dimensions are estimates from physical references, not official manufacturing drawings.

## Download and use

Download the model package from its release. It contains the `.blend`, self-contained `.glb`, previews, license, credits and a file manifest. The GLB uses meters: **X = width, Y = up, +Z = front**, with its origin near the bottom connector center. Import it into Godot or another glTF-compatible tool at scale 1.

Large source/export files live in versioned release packages; Git tracks the catalog, manifests, documentation, tools and previews. The download address and SHA-256 of each package are recorded in Git. You can retrieve a specific version and compare it with the next one without guessing which file is current.

```sh
python3 tools/verify.py
python3 tools/verify.py --download snes-ntsc-u 0.1.0
```

See [VERSIONING.md](VERSIONING.md) for the release workflow and comparison rules.

Before contributing changes, read [rules.md](rules.md). Every change requires a [collection changelog](CHANGELOG.md) update; model changes also belong in that model's changelog.

## License and attribution

Original contributions are licensed under **[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)**: attribution is required, commercial use is not licensed, and adapted material may not be redistributed under this license. The full terms are in [LICENSE](LICENSE). This is a public, source-available collection, not an OSI open-source software project.

Suggested credit:

> SNES NTSC-U cartridge reconstruction v0.1.0 by Lincoln Aleixo — Retro Cartridge Models — CC BY-NC-ND 4.0. https://github.com/lincolnaleixo/retro-cartridge-models

Existing hardware designs, product names, trademarks and any separately identified third-party content are outside this license grant. See [NOTICE.md](NOTICE.md) and [CREDITS.md](CREDITS.md). This collection is independent and is not affiliated with Nintendo.
