# Repository rules

## Single source of instructions

This file is the single source of repository rules. Read it before changing any file. Edit rules here only; never maintain a separate copy for a particular agent or harness.

`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and `.clinerules/00-repository.md` are relative symlinks to this file. Cursor and Windsurf use small always-on adapters that instruct the agent to read this file; those adapters must contain no independent project rules. Preserve these links and adapters when editing instructions.

## Changelog is mandatory for every change

Every change must update the root `CHANGELOG.md` in the same commit. This includes model geometry, materials, textures, UVs, renders, exports, metadata, scripts, automation, documentation, rules, configuration, fixes and deletions. Documentation-only changes and small corrections are not exempt.

If a change affects a model or its files, also update `assets/<asset-id>/CHANGELOG.md` for each affected model. Describe what changed, why, and the visible or practical effect; record relevant validation and known limitations without claiming checks that were not run. Use concrete before/after details for visual changes.

Put pending changes under `Unreleased`. When publishing a model release, move its pending asset notes into a dated version section and reference that version from the root changelog. Preserve previous entries. Documentation or tooling changes alone do not require inventing a new model version.

A change is not complete and must not be committed or published without its corresponding changelog entry. A correction solely to a changelog may be recorded in the corrected entry itself; it does not require an endlessly recursive entry about editing the changelog.

## English-only authored content

Write all repository and gallery content in English: UI text, accessibility labels, loading/error messages, descriptions, metadata, documentation, rules, changelogs and release notes. Use English number formatting. Preserve proper names and authentic third-party artwork rather than translating text printed on the modeled object.

## Models and releases

Follow `VERSIONING.md`. Each model has its own version, changelog, previews and manifest. Published tags, release archives, manifests and preview snapshots must remain unchanged; publish a new model version for changes to a released asset.

Keep editable `.blend` sources and self-contained `.glb` exports in release packages. Git tracks the catalog, manifests, previews, documentation and tools. Keep scale, axes and pivot explicit; document any import-contract change.

Use comparable camera framing and lighting to review visual improvements. Inspect the actual renders and exported model, especially the detail being changed. Treat measurements inferred from photographs as approximate, never official manufacturing dimensions.

## Validation and public content

Run `python3 tools/verify.py` before completing a change. For a release, also verify the package and the published download using the commands in `VERSIONING.md`. Recheck engine import when a model/export change could affect it.

Preserve the license and attribution scope in `LICENSE`, `NOTICE.md` and `CREDITS.md`. Do not add third-party artwork or reference photos without establishing their publication rights. Never copy private repository history, credentials, personal contact information or internal machine paths into this public repository or its release packages.
