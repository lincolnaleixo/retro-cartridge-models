#!/usr/bin/env python3
"""Collect verified current releases into an English offline model library."""
import argparse
import html
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from verify import ROOT, check_entry, safe, sha, verify_manifest, verify_package

REPOSITORY = "https://github.com/lincolnaleixo/retro-cartridge-models"
# Only navigation lives here; versions and checksums come from the catalog.
LAYOUT = {
    "snes-super-mario-world": "reproductions/snes/super-mario-world",
    "mega-drive-sonic-the-hedgehog": "reproductions/mega-drive/sonic-the-hedgehog",
    "playstation-1-crash-bandicoot": "reproductions/playstation-1/crash-bandicoot",
    "snes-ntsc-u": "templates/snes",
    "mega-drive": "templates/mega-drive",
    "playstation-1": "templates/playstation-1",
}


def relative_path(name):
    """Use portable relative paths, including on Windows."""
    safe(name)
    if name in ("", ".") or any(":" in part for part in PurePosixPath(name).parts):
        raise ValueError(f"Unsafe library path: {name}")
    return Path(name)


def release_archive(manifest_path, manifest, cache):
    archive = manifest["release"]["archive"]
    filename = relative_path(archive["name"])
    if len(filename.parts) != 1 or filename.suffix != ".zip":
        raise ValueError("Expected a plain ZIP filename")
    expected = f"{REPOSITORY}/releases/download/{manifest['release']['tag']}/{filename.name}"
    if archive["url"] != expected:
        raise ValueError("Unexpected release download URL")
    destination = cache / filename
    if not destination.exists():
        cache.mkdir(parents=True, exist_ok=True)
        # A temporary file keeps interrupted downloads out of the cache.
        with tempfile.TemporaryDirectory(prefix="library-download-", dir=cache) as temporary:
            download = Path(temporary) / filename
            print(f"Downloading {manifest['id']} {manifest['version']}")
            with urllib.request.urlopen(expected, timeout=60) as response, download.open("xb") as output:
                shutil.copyfileobj(response, output)
            check_entry(download, archive)
            verify_package(manifest_path, download)
            # Do not replace an existing file if another process populated the cache.
            try:
                os.link(download, destination)
            except FileExistsError:
                pass
    verify_package(manifest_path, destination)
    return destination


def write_index(output, records):
    escape = html.escape
    sections = []
    for category, description in (
        ("reproductions", "Game-specific media, organized by console and game."),
        ("templates", "Neutral media, organized by console."),
    ):
        cards = []
        for item in records:
            if not item["path"].startswith(category + "/"):
                continue
            folder = item["path"]
            links = [(item["blend"], "Blender"), (item["glb"], "GLB"),
                     (item["archive"], "ZIP"), ("README.md", "Readme"),
                     ("CREDITS.md", "Credits"), ("release-manifest.json", "Manifest")]
            local_links = " ".join(
                f'<a href="{escape(folder + "/" + name)}">{label}</a>'
                for name, label in links
            )
            cards.append(f'''<article>
<a href="{escape(folder + '/' + item['hero'])}"><img src="{escape(folder + '/' + item['hero'])}" alt="{escape(item['title'])}" loading="lazy"></a>
<div class="copy"><p class="meta">{escape(folder)} · v{escape(item['version'])}</p>
<h3>{escape(item['title'])}</h3><p>{escape(item['description'])}</p>
<nav aria-label="{escape(item['title'])} files">{local_links}</nav>
<p class="rights">{escape(item['rights'])}</p>
<a href="{escape(item['releaseUrl'])}">Published release ↗</a></div></article>''')
        sections.append(f'<section id="{category}"><h2>{category.title()}</h2><p>{description}</p><div class="grid">{"".join(cards)}</div></section>')
    page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Retro Cartridge Models — Offline library</title>
<style>
:root{font:16px/1.6 system-ui,sans-serif;color:#202c3b;background:#f3f4f6}*{box-sizing:border-box}
body{max-width:1180px;margin:auto;padding:32px 24px 64px}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.1;margin-bottom:20px}h2{font-size:2rem;margin-bottom:8px}h3{line-height:1.3}
a{color:#18579e;text-underline-offset:3px}a:focus-visible{outline:3px solid #18579e;outline-offset:4px}header{max-width:800px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:24px}section{margin-top:48px}
article{border:1px solid #d8dde4;border-radius:16px;overflow:hidden;background:white}img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#11151b}.copy{padding:22px}.meta,.rights{font-size:.8rem;color:#526174;overflow-wrap:anywhere}nav{display:flex;gap:16px;flex-wrap:wrap}footer{margin-top:48px;border-top:1px solid #cbd3dc;padding-top:24px}
</style></head><body><header><p>RETRO CARTRIDGE MODELS</p><h1>Your model library.</h1>
<p>Verified Blender sources, portable GLBs and preview images. Reproductions are grouped by console and game; neutral templates are grouped by console. All model files and previews work offline.</p>
<nav aria-label="Library sections"><a href="#reproductions">Reproductions</a><a href="#templates">Templates</a><a href="README.md">Library guide</a><a href="inventory.json">File inventory</a></nav></header>
'''
    page += "\n".join(sections)
    page += f'''<footer><p>Release packages and their embedded files are preserved exactly. Folder classification does not change their license or third-party rights.</p>
<nav aria-label="Collection links"><a href="{REPOSITORY}">Source repository ↗</a><a href="https://lincolnaleixo.github.io/retro-cartridge-models/">Online 3D gallery ↗</a><a href="LICENSE">License</a><a href="NOTICE.md">Rights notice</a></nav></footer></body></html>\n'''
    (output / "index.html").write_text(page, encoding="utf-8")
    lines = ["# Retro Cartridge Models — Offline library", "",
             "Open `index.html` for the visual index. Each game or console folder contains the exact released Blender source, GLB, previews and notices, plus its original ZIP and `release-manifest.json`.", "",
             "## Reproductions and templates", ""]
    lines.extend(f"- [{item['title']}]({item['path']}/README.md) — `{item['path']}/`, version {item['version']}" for item in records)
    lines.extend(["", "## Provenance and reuse", "",
                  "`inventory.json` records the relative paths, sizes and SHA-256 hashes of all other files in this library. Each release manifest records the immutable download URL and package checksums. The original package's `FILES.json` remains unchanged.", "",
                  "Folder names describe organization, not additional permissions. Read each package's license, credits and notice before reuse. Third-party artwork and marks are excluded from the original-contributions license.", "",
                  "The local images and files work offline. Source and published-release links require an internet connection. To update the collection, run the builder again with a new output directory; it never overwrites an existing library.", ""])
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


def build(output, cache):
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; choose a new directory with --output")
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    assets = {asset["id"]: asset for asset in catalog["assets"]}
    packages = []
    for asset_id, folder in LAYOUT.items():
        asset = assets[asset_id]
        manifest_path = ROOT / relative_path(asset["manifest"])
        manifest = verify_manifest(manifest_path)
        if (manifest["id"], manifest["version"]) != (asset_id, asset["latest"]):
            raise ValueError("Catalog version mismatch")
        reserved = {"release-manifest.json", manifest["release"]["archive"]["name"]}
        if reserved.intersection(manifest["files"]):
            raise ValueError("Package conflicts with library metadata")
        for name in manifest["files"]:
            relative_path(name)
        archive = release_archive(manifest_path, manifest, cache)
        packages.append((asset, folder, manifest_path, manifest, archive))

    # This exclusive creation happens only after every package has been verified.
    # Never delete or replace an existing user directory, including empty ones.
    output.mkdir(parents=True)
    records = []
    for asset, folder, manifest_path, manifest, archive in packages:
        destination = output / relative_path(folder)
        destination.mkdir(parents=True)
        with zipfile.ZipFile(archive) as package:
            for name in package.namelist():
                target = destination / relative_path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                # Copy bytes instead of extractall: ZIP links never become symlinks.
                with package.open(name) as source, target.open("xb") as target_file:
                    shutil.copyfileobj(source, target_file)
                if name != "FILES.json":
                    check_entry(target, manifest["files"][name])
        shutil.copyfile(archive, destination / archive.name)
        shutil.copyfile(manifest_path, destination / "release-manifest.json")
        files = manifest["files"]
        hero = next(p for p in manifest["previews"] if p["view"] == "hero")
        records.append({
            "id": asset["id"], "title": asset.get("displayTitle", asset["title"]),
            "description": asset["description"], "rights": asset["rights"],
            "version": manifest["version"], "path": folder, "archive": archive.name,
            "blend": next(name for name in files if name.endswith(".blend")),
            "glb": next(name for name in files if name.endswith(".glb")),
            "hero": next(name for name, entry in files.items() if entry["sha256"] == hero["sha256"]),
            "releaseUrl": f"{REPOSITORY}/releases/tag/{manifest['release']['tag']}",
        })
    for name in ("LICENSE", "NOTICE.md", "CREDITS.md"):
        shutil.copyfile(ROOT / name, output / name)
    write_index(output, records)
    inventory = {"schemaVersion": 1, "assets": records, "files": {
        path.relative_to(output).as_posix(): {"bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(output.rglob("*")) if path.is_file()
    }}
    (output / "inventory.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Library built: {len(records)} assets, {len(inventory['files'])} indexed files in {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/library",
                        help="new output directory (default: dist/library)")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".downloads/library",
                        help="directory of verified release ZIPs, using their original filenames")
    args = parser.parse_args()
    build(args.output, args.cache_dir)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, StopIteration) as error:
        print(f"Library build failed: {error}", file=sys.stderr)
        sys.exit(1)
