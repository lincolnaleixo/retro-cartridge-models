# Development model reference audit — 2026-10-02

**Historical audit of the first drafts.** The rejected geometry described below has since been replaced by `tools/media_mega_drive.py` and `tools/media_playstation.py`. The current reconstruction uses [new dimensional evidence](measurement-evidence-2026-10-02.json); see each asset's README and changelog for its current contract. This audit is retained to explain which errors were corrected, not as a description of the replacement files.

**Result: Mega Drive and PlayStation drafts rejected for visual fidelity.** This review compares their exported previews and `tools/create_media_models.py` with photographed specimens. It does not include corrected geometry. File integrity, UV, catalog and engine import checks do not establish physical resemblance.

## Reference scope

Use an identified specimen, not a mixture of regional details. The Sega western shell and Japanese shell below differ. PlayStation PAL branded cases, NTSC slim cases, longboxes and multidisc packages are distinct assets. A thin jewel case is not inherently wrong for PlayStation; its construction must match the selected variant.

The sources are photographs of actual objects published by retailers and collectors, not manufacturing drawings. A used-game listing does not establish that its case has never been replaced. External photographs are linked for comparison only and have not been copied into this repository or used as textures.

### Mega Drive references

- [Sonic PAL specimen: front, rear and top photographs](https://www.grillogames.de/products/sega-mega-drive-spiel-sonic-the-hedgehog-modul-anleitung-ovp-sehr-guter-z).
- [Genesis rear close-up](https://www.ebay.com/itm/296933836167), with [direct photograph](https://i.ebayimg.com/images/g/w9QAAOSw11Vnf9Vn/s-l1200.jpg).
- [Genesis lower connector opening](https://www.ebay.com/itm/205354222286), with [direct photograph](https://i.ebayimg.com/images/g/hL0AAeSwlYZn1PIC/s-l500.jpg).
- [Japanese Sonic G-4049 specimen](https://www.jnlgame.com/products/sonic-the-hedgehog-sega-mega-drive-japanese-import-pre-owned), including front, rear and top views.

### PlayStation references

- [PAL case photographs](https://www.psxpaldb.com/case-types/full-jewel-pal/) and [case-family overview](https://www.psxpaldb.com/case-types/).
- [Silent Hill NTSC-U/C specimen](https://www.grillogames.de/en/products/sony-playstation-1-spiel-silent-hill-ovp-anleitung-ntsc-u-c-usa-konami), including front, rear, spine and open case.
- [Tekken disc underside photograph](https://www.ebay.com/itm/335443828959), with [direct photograph](https://i.ebayimg.com/images/g/KCIAAOSwNb1mbyn1/s-l400.jpg).

## Mega Drive findings

| Feature | Rejected draft | Photographic evidence / required correction |
| --- | --- | --- |
| Silhouette | Large rounded shoulders, lower feet and rectangular U-shaped opening; matching front/rear extrusions | The PAL/Genesis specimen has a more rectangular face, small corner radii and smooth side cheeks. The Japanese specimen has separate lateral forms and an asymmetric notch. Select one family before rebuilding. |
| Front label | Isolated 79 × 44 mm rounded rectangle, aspect ratio 1.795 | The PAL label is taller relative to width and folds over the top. Rebuild its continuous surface and UVs. |
| Grips | Five raised vertical bars per side on each face | Western front sides are smooth; the rear has a long horizontal concave grip. Japanese fine peripheral ribs are also different from these invented bars. |
| Fasteners | Four protruding, slotted heads near the rear corners | The western rear photographs show two inset metallic fasteners. A sharper macro is needed to specify their head profile. |
| Rear | Broad pale label | The western specimen has molded logo/warning regions below the horizontal grip. The Japanese specimen has a different rear warning-label arrangement. |
| Connector | Gold contacts exposed across a tall frontal cutout | Contacts sit inside the bottom slot; the front wall conceals them in the normal front view. |
| Surface hierarchy | Dark overlays named as wells or screw recesses | These are not cavities. Front shell reaches Z=9.8 mm, label border reaches 10.02 mm and label is at 10.07 mm; rear screw heads extend beyond the shell surface. Rebuild actual depressions. |

The current export envelope, approximately 110 × 70 × 20.66 mm, describes the file only. It has not been validated against a measured physical cartridge. Do not derive exact thicknesses, corner radii or hole spacing from uncalibrated perspective photos.

## PlayStation findings

| Feature | Rejected draft | Photographic evidence / required correction |
| --- | --- | --- |
| Regional target | Generic thin case, approximately 142.025 × 125 × 10.325 mm | Select a specific PAL or NTSC case. Do not claim one geometry represents every PlayStation package. |
| Hinge-side strip | Opaque black block with 54 horizontal bars | The photographed PAL strip is smooth with molded PlayStation relief. The Silent Hill specimen uses a translucent molded component. Neither matches the draft. |
| Rear paper and spine | Flat rear label, no folded spine paper | `RearLabel` at Z=-5.025 mm lies outside `RearPanel`, whose outside is Z=-5.000 mm. Move paper inside and model the observed spine folds. |
| Booklet and clips | Two planes separated by 0.1 mm; one central rectangular clip at each edge | The NTSC specimen has a booklet with volume and two separated rounded clips along each of its top/bottom edges. |
| Tray | Black slab, ring and four raised rectangular pads | The NTSC specimen has a transparent molded tray with finer curved structures. The photographed PAL case has a black tray. Follow the chosen specimen's geometry and material. |
| Retaining hub | Capped cylinder and twelve rectangular fingers | Replace with a connected, slotted radial structure. The cylinder is 0.65 mm above the tray, leaving a gap. |
| Disc retention | Finger geometry reaches at most approximately 7.28 mm radius before bevel | The disc hole radius is 7.5 mm; the fingers do not reach its inner edge. These values describe the generated model, not measured hardware. |
| Hinge | Lid pivot at Z=3.8 mm; hinge pins at Z=2.6 mm | Align the rotation axis with the physical pin axis; current offset is 1.2 mm. Model mating ears/recesses. |
| Closure | Overlapping solid edge blocks | The lid edges and rails overlap by 1.3 mm in depth with overlapping XY footprints. Rebuild the nesting cross-sections instead of intersecting boxes. |
| Clear disc center | Transparent ring over a continuous silver annulus | Remove reflective geometry from the clear center region. A transparent material above opaque metal does not produce a transparent hub. |
| Disc underside | Dark material already exists | The Tekken photograph supports a dark, reflective underside. A silver top face alone is not evidence that the underside is wrong; validate it in a dedicated underside render. |

The 120 mm disc diameter, 15 mm hole and 1.2 mm thickness are authored values in the current generator; this review does not certify fit tolerances. The PAL database's own dimensions are inconsistent: its detail header reports 142 × 129 × 17 mm, body text reports 142 × 125 × 10 mm, and overview reports approximately 142 × 130 × 18 mm. None has been adopted as an exact reconstruction specification.

## Reconstruction acceptance criteria

1. Record game, region, edition and photographed shell/case family. Keep conflicting variants separate.
2. Compare front, back, both sides, top and bottom before adding surface grain, wear or lighting polish. Use measured or scale-bearing references for exact dimensions.
3. Reconstruct observed recesses, fasteners, clips, label folds and connector openings. Neutral labels must retain correct physical surfaces.
4. Verify assembly: paper inside plastic, hub connected to tray, lid pivot aligned with pins, no intersecting closure blocks, and no metal underneath the clear disc center.
5. Inspect the actual exported GLB in Godot, including the open case and disc underside. Use a UV test texture to reveal wrapping errors.
6. Record visual review separately from technical validation. Do not publish these drafts as faithful reconstructions merely because the catalog and import checks pass.
