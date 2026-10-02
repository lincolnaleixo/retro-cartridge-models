# Mega Drive / Genesis western cartridge — reconstruction

The original generic draft was rejected and replaced. This reconstruction follows the standard western Sega shell photographed with Sonic PAL, using a nominal 109 × 70 × 17 mm envelope supported by independent dimensional references. It does not represent Japanese Sega or Electronic Arts shells. Read the [credits and references](CREDITS.md) and [measurement evidence](../../docs/measurement-evidence-2026-10-02.json).

The shell has smooth curved cheeks, a straight front outline, stepped rear molding, a concave horizontal grip and two recessed security-shaped fasteners. A real recessed label land continues over the top. The connector and PCB sit inside the underside slot; the front wall conceals the contacts. The rear warning and mark areas are neutral molded panels. No game artwork, logo mesh, copied texture or third-party geometry is included.

Version **0.1.0** publishes the neutral model with editable source, previews and checksums. Generate the editable source and self-contained export locally:

```sh
blender -b --python tools/create_media_models.py -- --only mega-drive
```

Outputs go to the ignored `dist/development/mega-drive/` directory: `mega-drive.blend`, `mega-drive.glb`, actual-export renders (`hero.png`, `rear.png`, `top.png` plus front/back/left/right/top-ortho/bottom-ortho), and `development.json`. The Blender file keeps the parts separately editable; `tools/media_mega_drive.py` regenerates the geometry. The GLB contains only the model.

The GLB merges static pieces by material while preserving named artwork surfaces. The Blender source keeps contacts, fasteners, inner bosses and shell pieces individually editable.

The ABS uses original deterministic micrograin normal and roughness maps that survive glTF export. Three 512 × 512 PNG images are packed into the Blender file and embedded in the GLB: one shared tangent normal map, a satin front roughness map and a subtly more matte rear roughness map. `SurfaceUV` repeats at an 8 mm physical scale independently of the artwork UVs. The restrained grain is a visual approximation of molded plastic, not a factory texture measurement. No downloaded texture or artificial wear is added.

`FrontLabel` and `RearLabel` retain untextured replacement materials and their original 0–1 UV0. This prevents Godot's texture-coordinate remapping from replacing the artwork UV domain with repeating material coordinates.

Closed shell, PCB, contact and fastener surfaces use backface culling. The contact pads retain their position and 0.028 mm thickness with simple planar faces; removing their microscopic bevels reduces the model from 23,416 to 12,152 triangles without changing its envelope or external silhouette.

## Import contract

| Property | Value |
| --- | --- |
| Root | `MEGA_DRIVE` |
| Units and axes | Meters; X width, Y up, +Z front |
| Origin | Bottom center, Y = 0 |
| Export envelope | Approximately 108.972 × 70 × 17 mm; nominal 109 × 70 × 17 mm |
| Front artwork mesh | `FrontLabel`; 74 × 67 mm unfolded; aspect ratio 1.10448; top 7 mm wraps over the shell |
| Rear artwork mesh | `RearLabel`; 77.75 × 21.75 mm neutral molded information panel; aspect ratio 3.57471 |
| Artwork UVs | Full 0–1 artwork domain, upright and unmirrored when looking at each face |
| Surface detail UVs | `SurfaceUV`; repeating 8 mm tile; separate from the artwork domain |

The rear grip is approximately 79 × 9.5 mm with 1.7 mm depth; screw centers are 69.6 mm apart and approximately 36.1 mm above the base. The front label land is recessed 0.4572 mm, with the paper surface 0.035 mm above its floor. These are reconstruction dimensions corroborated against the documented sources, not Sega manufacturing tolerances. Hidden details, fillets and security-head profiles remain approximations. This is not a print-ready replacement shell. The standard repository license and notices apply.

See [changes](CHANGELOG.md) for validation and known limits.

Owner-supplied Sonic the Hedgehog label mapping is supported by the [local artwork workflow](../../docs/owner-artwork.md). Game artwork is not bundled in the neutral release.
