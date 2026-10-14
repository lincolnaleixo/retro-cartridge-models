# Model assets

The actual model records are organized into two collections:

- [Templates](templates/README.md): neutral media, grouped by console.
- [Reproductions](reproductions/README.md): game-specific media, grouped by console and game.

```text
assets/
├── templates/
│   ├── snes/
│   ├── mega-drive/
│   └── playstation-1/
└── reproductions/
    ├── snes/super-mario-world/
    ├── mega-drive/sonic-the-hedgehog/
    └── playstation-1/crash-bandicoot/
```

Each model folder contains its documentation, credits, changelog, published version manifests and preview images. The [catalog](../catalog.json) locates current records. Stable asset IDs, version tags and verified release downloads remain unchanged.

Use the [offline library builder](../README.md#organized-library) to collect the released Blender sources, GLBs and ZIPs in this console/game layout.
