# Local owner artwork

Publish the model repository first; consumers pin its released neutral GLBs and do not recreate geometry. The reusable `tools/apply_media_artwork.py` tool applies a supplied label locally and exports a self-contained GLB and packed Blender source. It does not download or ship proprietary artwork. Publication rights must be established separately before distributing a textured example.

```sh
blender --factory-startup -b --python tools/apply_media_artwork.py -- --model mega-drive --front /path/to/unfolded-label.png --title "Sonic the Hedgehog (1991)" --output dist/owner-examples/mega-drive
blender --factory-startup -b --python tools/apply_media_artwork.py -- --model playstation-1 --front /path/to/disc-label.png --title "Crash Bandicoot (1996)" --output dist/owner-examples/playstation-1
```

An unfolded Mega Drive label is 74 × 67 mm, with its top 7 mm covering the fold. Optional `--top` supplies the fold separately. `--front-rect` and `--top-rect` accept normalized left/bottom/right/top UV bounds to select a region of a scan; reversed bounds flip that region. The input pixels remain unchanged. Disc artwork is square; the annular mesh masks the outside and center without transparency tricks. A provenance JSON records input hashes and UV mapping without private machine paths.

Game references: Sonic the Hedgehog (1991), western PAL cartridge; Crash Bandicoot (1996), SCUS-94900 disc. Local visual studies used the Sonic PAL specimen photographed by [Grillo Games](https://www.grillogames.de/products/sega-mega-drive-spiel-sonic-the-hedgehog-modul-anleitung-ovp-sehr-guter-z), and the [PSX Data Center disc scan](https://psxdatacenter.com/games/U/C/SCUS-94900.html) (entry credits SPECIALT1212 for high-resolution covers). Those images are not distributed here. SEGA, Sony, Universal and Naughty Dog artwork/marks remain outside the model license; source attribution is not a rights grant.
