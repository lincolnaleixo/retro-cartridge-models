# Versioning and releases

Each asset is versioned independently: `MAJOR.MINOR.PATCH`. A tag is named `<asset-id>-v<version>`, for example `snes-ntsc-u-v0.1.0`.

- **MAJOR:** incompatible scale, axes, pivot, scene structure or other import-contract change.
- **MINOR:** improved shape, materials, UVs, detail or a new supported variant while retaining the import contract.
- **PATCH:** a correction to packaging, metadata or a defect without a planned visual redesign.

Version `0.x` identifies a developing reconstruction whose fidelity is still being refined. Public history begins at 0.1.0; earlier private experiments are described as pre-publication work, not invented public releases.

## What belongs to a version

Each `assets/<id>/versions/<version>.json` records the title, creator, license, axes, dimensions, mesh/material/texture counts, changes, preview hashes, package file hashes, and the release ZIP hash. The catalog points to exactly one latest version for each asset. Old manifests and preview folders are retained.

GitHub release packages hold the editable `.blend`, portable `.glb`, renders and notices. They are the binary snapshots for that version. Keeping binary snapshots out of ordinary Git prevents every model iteration from making all future clones substantially larger. GitHub supports release assets for distributing large files: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github

Treat published tags, packages, checksums and version manifests as immutable. If anything must change, publish a new version; do not replace an old release asset in place. Checksums detect a changed download even if a hosting administrator replaces it.

## Preparing the next version

1. Work from the previous release's Blender source. Keep the public neutral-label variant and rights notes explicit.
2. Export a self-contained GLB and validate its import in the target engine. Record scale, pivot and any compatibility change.
3. Render comparable hero, top and bottom views. Keep framing and lighting constant when judging geometry; if lighting changes, record that separately. Add a matching side/profile view when changing curvature.
4. Create a new version manifest and preview folder. Record concrete before/after changes, their reference basis, known approximations and checks performed. Update the per-asset changelog and catalog.
5. Run `python3 tools/package.py <manifest.json> <payload-directory> <output.zip>` to record file hashes and build the package. Then run `python3 tools/verify.py --package <manifest.json> <output.zip>`.
6. Commit the metadata and previews, tag that exact commit, and create a GitHub release with the ZIP and release notes. Verify the published download with `python3 tools/verify.py --download <asset-id> <version>`.

Only the maintainer publishes releases. The availability of editable sources or a packaging tool does not grant downstream permission to redistribute adaptations beyond the license.
