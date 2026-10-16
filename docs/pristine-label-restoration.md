# Pristine label restoration

The October 16, 2026 releases target the appearance of clean, newly unboxed print. They retain the existing game editions and cartridge geometry.

| Reproduction | Version | Restored surfaces |
| --- | --- | --- |
| Super Mario 64 | 0.3.0 | Locally retouched original front; clean 1996 rear warning print |
| Super Mario Bros. | 0.2.0 | Clean original black front ink; restored top title and early rear warning |
| Super Mario World | 0.2.0 | Repaired blue-field scan blemishes and restrained color recovery |
| Sonic the Hedgehog | 0.2.0 | Clear folded top title; original cream front bytes retained |
| Crash Bandicoot | 0.1.0, unchanged | Existing print was already clean; intentional graphic textures retained |

## Artwork methods

Local retouch preserves the original front illustrations, lettering, seals and edition codes. Small masks repair observed damage. The NES front suppresses neutral low-value abrasion in black ink while retaining bright printed stars and colored pixels. The SNES repair clones clean blue halftone from the same original print; broad smoothing was rejected because it created visible patches.

The N64/NES rear warnings and NES/Sonic top titles use the built-in image-generation tool, then local registration into the existing photographed UV footprints. Text and edition marks were checked against the original images. The N64 rear retains its original `MANUAL` spelling and 1996 `NUS-USA/CAN` edition. The NES rear has no REV-A marking. A generated Sonic front was rejected because it reduced effective source resolution.

Restoration is approximate. It does not recover an archival master or prove a color-calibrated match to factory ink. Reconstructed warning/title typography can differ subtly from the physical label. Third-party artwork, marks and source photography retain their existing rights exclusions.

Each release includes `artwork-provenance.json`, selected prompts, input/output hashes, local-processing records and `artwork-update-report.json`. The previous releases remain available unchanged.

## Geometry-preserving image replacement

Use the previous published Blender source and GLB, plus a JSON mapping from exact Blender image names to reviewed replacement files:

```json
{
  "images": {
    "Super Mario 64 (1996) rear artwork": "restored-rear.png"
  }
}
```

```sh
blender --factory-startup --background --python-exit-code 1 \
  --python tools/update_packed_artwork.py -- \
  --blend previous.blend --glb previous.glb \
  --mapping replacements.json --output dist/restored
```

The updater patches only embedded GLB image buffers and the corresponding packed Blender image datablocks. It saves and reopens the source, checks geometry/normals/transforms/UVs, and verifies untouched packed images. Output paths cannot alias inputs. Existing output files require an explicit overwrite option.

These four releases use no mesh UV remaps. The optional helper remap facility requires a named object/material/layer, explicit old/new rectangles and framing evidence; unrelated UV accessors are protected.

## Validation

All four updated exports pass structural GLB inspection, saved-source reopening and Godot 4.7.2 import. Godot compares surface geometry, normals, UVs and transforms against the previous model and confirms that the new albedo images decode. The helper's eight focused tests join the eighteen existing tooling tests.

Previous and current GLBs were rendered with identical neutral lighting, camera presets, Standard view transform, exposure -1.0, 32 Cycles samples and 1200 × 1000 output. The new release previews use that setup; historical previews remain immutable. Some older SNES/Sonic previews used different lighting, so matched rerenders are the basis for judging artwork changes.

All five unprinted templates and the Crash reproduction remain unchanged. RetroLife's neutral model pins remain unchanged; only its Super Mario World label dependency needs a new version after the source release is published and verified.
