# PlayStation 1 — standalone CD

Version 0.1.0 is a standalone optical disc, with no jewel case, booklet, tray or retention hub. The previous case reconstruction remains historical generator source in `tools/media_playstation.py`; the default builder uses `tools/media_playstation_disc.py`.

The model follows the nominal ECMA-130 envelope: 120 mm diameter, 15 mm center hole and 1.2 mm thickness. It uses meters, X width, Y up and +Z printed face, with the bottom at Y=0. Physical fine finishes are visual approximations, not manufacturing tooling.

Five independently addressable meshes form the disc: `Disc`, `DiscClearHub`, `DiscInnerMatrix`, `DiscOuterRim`, and `FrontLabel`. The clear center is a real annulus and the hole is empty. `FrontLabel` contains only the printable annulus (21–59.55 mm radius), with a 120 mm square UV0 layout. There is deliberately no `RearLabel`: the dark reading face must never receive cover artwork. The original optical-zone roughness texture is embedded in the GLB.

Generate with Blender 5.2.2:

```sh
blender --factory-startup -b --python tools/create_media_models.py -- --only playstation-1
```

Outputs are `dist/development/playstation-1/playstation-1.blend`, `.glb`, actual-export renders and `development.json`. Released packages include editable source, GLB, views, attribution and checksums. Git stores the version manifest and previews.

The neutral release contains no Sony or game artwork. For locally supplied Crash Bandicoot disc artwork, see [owner artwork workflow](../../docs/owner-artwork.md). That example is not bundled in the neutral release.

Validation: 5 meshes, 8,704 triangles, 4 materials, one embedded original image; GLB integrity/UV inspection and Godot 4.7.2 import. Transmission differs by engine; Compatibility uses alpha for the clear hub. Read [credits](CREDITS.md) and [changelog](CHANGELOG.md).
