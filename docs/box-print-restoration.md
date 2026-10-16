# Pristine game-box print restoration

The five box reproductions at **0.3.0** separate photographed wear from the original printed design. The goal is clean, newly unboxed packaging with legible lettering when viewed close up. This is a documented reconstruction, not a recovered factory master or calibrated ink proof.

| Game | Main print treatment |
| --- | --- |
| Super Mario Bros. | Sharper Nintendo-attributed original front components, smooth original letter contours, clean black ink, angular flat-color Mario/block artwork and a reconstructed early round seal. The early no-REV-A layout is retained. |
| Super Mario World | Clean flat marks and side panels, original period illustrations and newly typeset exact rear wording, preserving the four original screenshots. |
| Super Mario 64 | Clean original K-A front, matching period character artwork for narrow duotone panels, restored rear copy and marks. |
| Sonic the Hedgehog | Restored title contours, measured grid, cream/pink fields, clean SEGA wordmark and reconstructed chrome Mega Drive plate. |
| Crash Bandicoot | Separate illustration and fine-copy cleanup, clean black fields, the matching 1994–2009 PlayStation vector wordmark and restored NTSC U/C copy. |

Sonic adopts the independently published **Mega Drive box template 0.3.0**, retaining the corrected `SpinePrint` U direction from 0.2.0 and adjusting six retention supports to accommodate the full-size cartridge. Every other printed surface retains its template mapping. The box subset preserves its selected template geometry, articulation and `Open` animation.

Each game reproduction includes its matching published cartridge or disc beneath a removable `Contents` parent. The four cartridges retain their original dimensions and artwork; Crash's disc fits the jewel-case hub. Neutral templates stay empty. Standalone media releases remain unchanged.

## Sources and reproducibility

[The source catalog](game-box-artwork-sources.json) identifies the actual references used by each face. Release ZIPs include lossless prepared PNGs, an artwork mapping, per-face transformation records and source citations. They also contain the packed editable Blender file, self-contained GLB, six standard previews, and exact-hash validation reports. The prepared PNGs are embedded byte-for-byte in the GLB.

The deterministic preparation scripts are `tools/refine_nes_box_print.py`, `tools/polish_nintendo_box_prints.py`, `tools/refine_sonic_box_print.py` and `tools/refine_ps1_box_print.py`. They use Pillow, NumPy and OpenCV; contour fitting also uses scikit-image and SciPy. Run their `--help` commands from the repository root for input paths and available overrides. Their default `dist/` paths describe the documented research workspace. Raw research references are not silently downloaded by these scripts and must be supplied separately. Use the recorded hashes to identify the exact inputs. Typeface substitutions and any local font dependencies are documented approximations, not original production fonts.

To rebuild without reconstructing the artwork research, unpack the selected neutral box template and the reproduction's prepared PNGs and mapping. Run `tools/create_game_boxes.py` with the neutral template `.blend` as `--source`, the reproduction asset ID, console and artwork mapping to make a print-only box. Then run `tools/compose_box_contents.py` through Blender with `--box-source` pointing to that new `.blend`, `--media-directory` pointing to the unpacked pinned media release, and a separate `--output` directory. The catalog must match the recorded source versions. The composer reads the neighboring `.glb` and `construction.json`, copies the source binary buffers exactly and appends the native media objects to the editable Blender source. An ordinary DCC re-export can change buffer precision.

The release's `content-composition.json` identifies the exact input hashes, rigid placement, parent, scale and byte-preservation checks. `content-source/` retains the pinned media manifest and its original attribution and provenance. Box geometry is compared with its independent template; the added media is compared separately with its exact published source. This separation rejects unintended box edits and prevents a composition from silently changing a cartridge or disc.

[Physical-fit evidence](box-content-fit.json) records specimen references, manual/cartridge orientation, inferred clearances and final mesh intersection checks in the closed and fully open poses. The release includes its corresponding selection as `content-fit-evidence.json`. `tools/audit_box_content_fit.py` reproduces the surface checks from the final exported GLBs through Blender. The Nintendo packages also include a documented extracted-insert view; their normal `Open` animation keeps the cartridge seated inside the carton.

## Review and limits

Review covers front, rear, both sides, top, bottom and the open pose using renders of the exported GLB. Matching before/after close-ups use the same camera, output resolution and lighting. Flat-face comparisons isolate the print from the shell's lighting and transparency. Blender source reopening and Godot import check the same binary hashes used in the packages.

Original screenshots and shaded illustrations retain finite source detail. Traced contours, reconstructed seals, chrome reflections, duotone placement, visual color restoration and approximate typesetting are identified in provenance. Enlarging the output improves antialiased edges but does not recover unseen artwork. Third-party game artwork, trademarks and source images retain the exclusions documented in each release.
