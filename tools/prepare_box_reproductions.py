#!/usr/bin/env python3
"""Package audited game-box reproductions without changing their neutral templates.

By default, write reviewable payloads, archives and draft manifests under dist.
Use --install only after the independent neutral-template commit is complete to
install the five nested asset directories and update the catalog. Exact source,
export, artwork and template hashes must match the successful audit reports.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from inspect_glb import read_glb
from prepare_box_templates import CONFIG as TEMPLATES, VIEWS, png_dimensions, write_json
from verify import ROOT, SEMVER, safe, sha, verify_package

VERSION = '0.1.0'
DATE = '2026-10-16'
RIGHTS = ('Original modeling contributions only: CC BY-NC-ND 4.0. Game artwork, '
          'marks, product designs, scans and source photography are excluded. '
          'Attribution and the maintainer\'s request do not grant rights to those elements.')
GAMES = {
    'nes': {
        'game': 'super-mario-bros', 'name': 'Super Mario Bros.',
        'consoleName': 'NES', 'edition': 'Early US black-box edition with an integrated rear hanger',
        'description': 'A pristine early Super Mario Bros. carton with its printed outer panels, articulated tuck lid and dust ears, empty black sleeve and foam spacer.',
    },
    'snes': {
        'game': 'super-mario-world', 'name': 'Super Mario World',
        'consoleName': 'Super Nintendo', 'edition': 'US retail cardboard-box presentation',
        'description': 'A pristine Super Mario World retail carton with printed panels, two articulated end closures and a removable folded cartridge tray.',
    },
    'nintendo-64': {
        'game': 'super-mario-64', 'name': 'Super Mario 64',
        'consoleName': 'Nintendo 64', 'edition': 'Original US K-A retail presentation',
        'description': 'A pristine original-edition Super Mario 64 carton with printed panels, articulated end closures and a removable folded Game Pak cradle.',
    },
    'mega-drive': {
        'game': 'sonic-the-hedgehog', 'name': 'Sonic the Hedgehog',
        'consoleName': 'Mega Drive', 'edition': 'Western PAL Mega Drive presentation',
        'description': 'A fresh Sonic the Hedgehog clamshell with the PAL wrap, restored booklet covers, intact retail hanger and articulated spine.',
    },
    'playstation-1': {
        'game': 'crash-bandicoot', 'name': 'Crash Bandicoot',
        'consoleName': 'PlayStation 1', 'edition': 'Original US black-label SCUS-94900 presentation',
        'description': 'A clean Crash Bandicoot clear-tray jewel case with original-edition booklet covers, both sides of the folded tray card and an articulated lid.',
    },
}


def identifier(console):
    return console + '-' + GAMES[console]['game'] + '-box'


def assert_public(value):
    """Reject accidental machine paths before metadata enters a public payload."""
    if isinstance(value, dict):
        for child in value.values():
            assert_public(child)
    elif isinstance(value, list):
        for child in value:
            assert_public(child)
    elif isinstance(value, str) and any(marker in value for marker in ('/private/', '/Users/', 'file://')):
        raise ValueError('Private machine path found in public metadata')


def verify_draft_package(manifest_path, archive):
    """Verify a review archive before it has any public catalog entry."""
    manifest = json.loads(manifest_path.read_text())
    record = manifest['release']['archive']
    if archive.stat().st_size != record['bytes'] or sha(archive) != record['sha256']:
        raise ValueError('Draft archive checksum differs from its manifest')
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if len(names) != len(set(names)) or set(names) != set(manifest['files']) | {'FILES.json'}:
            raise ValueError('Unexpected, missing or duplicate files in draft archive')
        expected = {'assetId': manifest['id'], 'version': manifest['version'], 'files': manifest['files']}
        if json.loads(package.read('FILES.json')) != expected:
            raise ValueError('Draft archive internal file index differs from manifest')
        for name, record in manifest['files'].items():
            safe(name)
            payload = package.read(name)
            if len(payload) != record['bytes'] or hashlib.sha256(payload).hexdigest() != record['sha256']:
                raise ValueError('Draft payload checksum mismatch: ' + name)
        for preview in manifest['previews']:
            if manifest['files'][preview['view'] + '.png']['sha256'] != preview['sha256']:
                raise ValueError('Draft preview differs from its packaged image')


def geometry_evidence(console):
    evidence = json.loads((ROOT / 'docs' / TEMPLATES[console]['evidence']).read_text())
    if 'models' in evidence:
        model = evidence['models'][console]
        evidence['models'] = {console: model}
        evidence['sources'] = [source for source in evidence['sources'] if source['id'] in model['sourceIds']]
    return evidence


def selected_artwork_sources(catalog, asset_id):
    """Require an explicit per-asset selection instead of copying a source catalog."""
    assets = catalog.get('assets', {})
    if isinstance(assets, list):
        assets = {entry['assetId']: entry for entry in assets}
    if asset_id not in assets:
        raise ValueError('Missing per-asset artwork source selection: ' + asset_id)
    entry = copy.deepcopy(assets[asset_id])
    selected = entry.get('usedSourceIds')
    if selected is None and isinstance(entry.get('slots'), dict):
        selected = list(dict.fromkeys(source_id for ids in entry['slots'].values() for source_id in ids))
    sources = catalog.get('sources', [])
    if isinstance(sources, dict):
        sources = [dict(value, id=key) for key, value in sources.items()]
    if not selected or len(selected) != len(set(selected)):
        raise ValueError('Missing or duplicate usedSourceIds: ' + asset_id)
    by_id = {item['id']: item for item in sources}
    if set(selected) - set(by_id):
        raise ValueError('Unknown artwork reference in ' + asset_id)
    return {'schemaVersion': 1, 'assetId': asset_id,
            'publicationRights': catalog.get('publicationRights', 'not-established'), 'selection': entry,
            'sources': [by_id[source_id] for source_id in selected]}


def artwork_inputs(asset_id, folder, glb, construction):
    mapping = json.loads((folder / 'mapping.json').read_text())
    provenance = json.loads((folder / 'provenance.json').read_text())
    if provenance.get('assetId') != asset_id:
        raise ValueError('Artwork provenance identifies the wrong asset')
    records = provenance.get('slots', provenance.get('faces', {}))
    expected_slots = set(construction['artworkSlots'].values())
    if set(mapping) != expected_slots or set(records) != expected_slots:
        raise ValueError('Artwork mapping/provenance does not cover every artwork slot: ' + asset_id)
    images = {}
    for slot, filename in mapping.items():
        path = Path(filename)
        if not path.is_absolute():
            path = ROOT / path if (ROOT / path).is_file() else folder / path
        path = path.resolve()
        if path.parent != folder.resolve() or path.suffix.lower() != '.png':
            raise ValueError('Only prepared face PNGs from the asset artwork folder may be packaged')
        record = records[slot]
        if record.get('sha256', record.get('outputSha256')) != sha(path):
            raise ValueError('Stale artwork provenance for ' + asset_id + ': ' + slot)
        if list(png_dimensions(path)) != record.get('outputPixels'):
            raise ValueError('Artwork pixel dimensions differ from provenance: ' + slot)
        images[slot] = path

    document, binary, _ = read_glb(glb)
    embedded = []
    for node in document['nodes']:
        slot = node.get('extras', {}).get('artworkSlot')
        if not slot:
            continue
        for primitive in document['meshes'][node['mesh']]['primitives']:
            material = document['materials'][primitive['material']]
            texture = material['pbrMetallicRoughness'].get('baseColorTexture')
            if texture is None:
                raise ValueError('Artwork slot lacks an embedded albedo texture: ' + node['name'])
            texture_record = document['textures'][texture['index']]
            image = document['images'][texture_record['source']]
            view = document['bufferViews'][image['bufferView']]
            offset = view.get('byteOffset', 0)
            digest = hashlib.sha256(binary[offset:offset + view['byteLength']]).hexdigest()
            if digest != sha(images[slot]):
                raise ValueError('Embedded print differs from its prepared PNG: ' + node['name'])
            embedded.append({'node': node['name'], 'slot': slot, 'sha256': digest})
    public_mapping = {slot: 'artwork/' + slot + '.png' for slot in images}
    provenance['sourceCatalog'] = 'artwork-sources.json'
    for slot, record in records.items():
        record['output'] = public_mapping[slot]
    report = {'status': 'passed', 'assetId': asset_id, 'glbSha256': sha(glb),
              'method': 'Every artwork node albedo image matches the corresponding prepared PNG byte-for-byte.',
              'surfaces': embedded}
    assert_public(provenance)
    return images, provenance, public_mapping, report


def audit_inputs(console, args, validation, source_report, source_catalog):
    asset_id = identifier(console)
    folder = args.base / 'reproductions' / asset_id
    glb, blend = folder / (asset_id + '.glb'), folder / (asset_id + '.blend')
    structural = next(item for item in validation['assets'] if item['file'] == glb.name)
    engine_asset = next(item for item in validation['godot']['assets'] if item['id'] == asset_id)
    source_asset = next(item for item in source_report['assets'] if item['id'] == asset_id)
    for path, entries in ((glb, (structural, engine_asset)), (blend, (source_asset,))):
        if any(entry.get('sha256') != sha(path) for entry in entries):
            raise ValueError('Stale reproduction validation report: ' + path.name)
    if structural.get('status') != 'passed' or not engine_asset.get('namedPartsPresent'):
        raise ValueError('Incomplete reproduction validation: ' + asset_id)
    parity = structural.get('geometryParity', {})
    template = args.base / 'templates' / (console + '-box') / (console + '-box.glb')
    template_manifest = json.loads((ROOT / 'assets' / 'templates' / console / 'box' / 'versions' / '0.1.0.json').read_text())
    if template_manifest['files'][template.name]['sha256'] != sha(template):
        raise ValueError('Geometry comparison template differs from its independent v0.1.0 release: ' + console)
    if (parity.get('status') != 'passed' or parity.get('templateSha256') != sha(template)
            or parity.get('reproductionSha256') != sha(glb)):
        raise ValueError('Missing or stale neutral-template geometry comparison: ' + asset_id)
    construction = json.loads((folder / 'construction.json').read_text())
    if construction['artworkSlots'] != structural['artworkSlots']:
        raise ValueError('Construction metadata differs from audited artwork slots')
    for view in VIEWS:
        png_dimensions(folder / (view + '.png'))
    artwork = artwork_inputs(asset_id, args.base / 'artwork' / asset_id, glb, construction)
    references = selected_artwork_sources(source_catalog, asset_id)
    if set(references['selection'].get('slots', {})) != set(artwork[0]):
        raise ValueError('Source catalog does not identify every prepared artwork slot')
    evidence = geometry_evidence(console)
    for value in (construction, structural, engine_asset, source_asset, references, evidence):
        assert_public(value)
    return {'folder': folder, 'structural': structural, 'engine': engine_asset,
            'source': source_asset, 'construction': construction, 'artwork': artwork,
            'references': references, 'evidence': evidence}


def documents(console, version, date, data, engine_version, blender_version):
    game, asset_id = GAMES[console], identifier(console)
    title = game['consoleName'] + ' — ' + game['name'] + ' box reproduction'
    images, provenance, _, _ = data['artwork']
    dimensions = ' × '.join(f'{v:g}' for v in data['construction']['nominalDimensionsMm'])
    records = provenance.get('slots', provenance.get('faces', {}))
    rows = []
    for slot, path in images.items():
        record = records[slot]
        effective = record.get('effectiveRectifiedPixels')
        if effective is None and record.get('cropPixels'):
            left, top, right, bottom = record['cropPixels']
            effective = [right - left, bottom - top]
            if record.get('rotateCounterclockwise90'):
                effective.reverse()
        detail = ' × '.join(str(v) for v in effective) if effective else 'See per-face provenance'
        width, height = png_dimensions(path)
        rows.append(f'| `{slot}` | {detail} | {width} × {height} | [`{slot}.png`](artwork/{slot}.png) |')
    slots = '\n'.join(rows)
    source_links = '\n'.join('- [' + source.get('title', source['id']) + ']('
                             + source.get('url', source.get('sourcePage', '')) + '). '
                             + source.get('credit', '') + '. ' + source.get('usedFor', source.get('notes', ''))
                             for source in data['references']['sources'])
    method = provenance.get('method', provenance.get('workflow', 'The prepared-face provenance records the local restoration process.'))
    limitations = provenance.get('limitations', 'Source resolution limits fine print; cleanup does not recover missing original detail.')
    if not isinstance(limitations, str):
        limitations = ' '.join(limitations)
    edition_notes = data['references']['selection'].get('limitations', [])
    if isinstance(edition_notes, str):
        edition_notes = [edition_notes]
    limitations = ' '.join([limitations, *edition_notes])
    parity = data['structural']['geometryParity']
    rounding = parity.get('nonArtworkUvFloat32Rounding', [])
    parity_note = ''
    if rounding:
        changes = sum(item['changedScalars'] for item in rounding)
        delta = max(item['maximumDelta'] for item in rounding)
        parity_note = (f' The exporter rounded {changes} non-artwork UV scalars by at most {delta:.3g}; '
                       'this is recorded separately and does not change any printed-face UV coordinates.')
    body = f'''# {title}

**Version:** {version} · **Date:** {date} · **Creator:** Lincoln Aleixo

{game['description']}

![Closed box](hero.png)

![Open box](open.png)

## Edition and contents

Selected edition: **{game['edition']}**. This reproduction uses the independently released [{console} neutral box template](https://github.com/lincolnaleixo/retro-cartridge-models/tree/main/assets/templates/{console}/box), with the same packaging geometry, hinge hierarchy, normalized print UVs and opening animation. Cartridge and CD models remain separate assets; no game media is enclosed. Printed booklet covers, where present, surround approximate blank interior leaves rather than a complete reproduced manual.

The shell and print aim for a pristine, newly unboxed appearance. {method} {limitations} Restoration is a visual approximation rather than proof of original ink values, manufacturing tolerances or missing lettering. Upsampling does not add authentic detail. Paper texture, scan blur and small source imperfections may remain visible at close range.

## Prepared artwork

| Artwork slot | Approximate effective source pixels | Prepared image pixels | Release file |
| --- | --- | --- | --- |
{slots}

Every listed PNG is embedded byte-for-byte in its GLB artwork slot and included separately in the release for reproducible application. The package contains the used prepared faces, their source citations and transformation provenance; it does not include unused research photographs or raw specimen images. Separate files do not grant additional rights to the artwork.

## Import and validation

| Property | Value |
| --- | --- |
| Units and axes | Meters; X width, Y up, +Z front |
| Pivot | Bottom center of the nominal closed envelope |
| Nominal closed size | {dimensions} mm |
| Initial pose | Closed |
| Animation | `Open`, 0 to 2 seconds |

The self-contained GLB passed structural, image, UV, hierarchy and animation checks. Direct comparison with its neutral template verified identical positions, normals, artwork UVs, triangle indices, node transforms and animation keys.{parity_note} Godot {engine_version} imported and evaluated both animation endpoints; Blender {blender_version} reopened the packed editable source and checked both poses. Release reports bind these checks to exact binary hashes.

{TEMPLATES[console]['limitations']} Transparent materials and printed-paper highlights can vary between renderers. Godot does not honor the exported specular extension; apply a printed-material specular level of 0.18 when matching the Blender preview lighting.

The release includes editable `.blend`, portable `.glb`, six previews, construction and reference evidence, prepared PNGs, provenance and validation reports. Run the repository's `tools/create_game_boxes.py` from the unpacked release directory, passing `--console {console} --asset-id {asset_id} --artwork artwork-mapping.json --output regenerated`, to rebuild with the included artwork mapping.

See [credits](CREDITS.md) and [changelog](CHANGELOG.md). {RIGHTS}
'''
    credits = f'''# Credits — {title}

Original parametric model, artwork preparation and release: **Lincoln Aleixo**.

## Artwork sources actually used

{source_links}

The bundled `artwork-sources.json` identifies this edition's selected references. `artwork-provenance.json` records source and output hashes, source pixel dimensions and restoration operations. `artwork-embedding-report.json` verifies the exact prepared images applied to each print surface.

{method} {limitations} Prepared-face resolution limits fine lettering and image detail; local cleanup cannot establish exact original print colors or recover unseen design information. No generated replacement game illustration or invented lettering is asserted.

## Geometry references

The independent neutral {console} box release supplies the construction. Its relevant sources and measurement caveats are retained in `geometry-reference-evidence.json`. {TEMPLATES[console]['limitations']}

## Rights scope

{RIGHTS} The maintainer requested these game-specific reproductions and their publication, but that request is not a license from the respective artwork or photograph owners. No redistribution license in third-party print, trademarks or source photography is asserted. Source attribution documents provenance and does not establish permission. The included prepared images and editable source do not expand the collection license. Read `LICENSE` and `NOTICE.md`.
'''
    changelog = f'''# Changelog — {title}

## {version} — {date}

- Added the first independently versioned {game['name']} box reproduction using the neutral {console} box template.
- Applied edition-specific prepared print to each artwork slot, retaining unprinted interior stock and pristine packaging materials.
- Included the actual prepared PNG faces and per-slot source, edit and image-hash provenance; recorded restoration and resolution limits.
- Preserved template positions, normals, artwork UVs, indices, hinge transforms and the two-second Open clip, verified through a complete decoded-data comparison.{parity_note}
- Validated the self-contained export, exact embedded artwork, Godot import and both animation endpoints, then reopened the editable Blender source.
- Kept existing neutral templates, cartridge and disc releases unchanged.
'''
    return title, {'README.md': body, 'CREDITS.md': credits, 'CHANGELOG.md': changelog}


def stage(console, args, data, audit, source_report):
    game, asset_id = GAMES[console], identifier(console)
    directory = ROOT / 'assets' / 'reproductions' / console / game['game'] / 'box'
    manifest_path = directory / 'versions' / (args.version + '.json')
    tag = asset_id + '-v' + args.version
    if subprocess.run(['git', 'show-ref', '--verify', '--quiet', 'refs/tags/' + tag], cwd=ROOT).returncode == 0:
        raise ValueError('Refusing to modify an existing tagged release: ' + tag)
    title, docs = documents(console, args.version, args.date, data, audit['godot']['engine'], source_report['blender'])
    images, provenance, mapping, embedding = data['artwork']
    with tempfile.TemporaryDirectory(prefix=asset_id + '-', dir=args.base) as temporary:
        temporary = Path(temporary)
        payload = temporary / 'payload'
        (payload / 'artwork').mkdir(parents=True)
        for suffix in ('.blend', '.glb'):
            shutil.copy2(data['folder'] / (asset_id + suffix), payload)
        for name in ('LICENSE', 'NOTICE.md'):
            shutil.copy2(ROOT / name, payload)
        for name, text in docs.items():
            (payload / name).write_text(text)
        for slot, path in images.items():
            shutil.copy2(path, payload / 'artwork' / (slot + '.png'))
        engine_report = {'status': 'passed', 'engine': audit['godot']['engine'], 'assets': [data['engine']]}
        source = {key: value for key, value in source_report.items() if key != 'assets'}
        source['assets'] = [data['source']]
        json_files = {'construction.json': data['construction'], 'geometry-reference-evidence.json': data['evidence'],
                      'artwork-sources.json': data['references'], 'artwork-provenance.json': provenance,
                      'artwork-mapping.json': mapping, 'artwork-embedding-report.json': embedding,
                      'glb-inspection.json': data['structural'], 'godot-import-report.json': engine_report,
                      'source-reopen-report.json': source}
        for name, value in json_files.items():
            assert_public(value)
            write_json(payload / name, value)
        previews = []
        for view in VIEWS:
            path = data['folder'] / (view + '.png')
            width, height = png_dimensions(path)
            previews.append({'view': view, 'path': (directory.relative_to(ROOT) / 'previews' / args.version / path.name).as_posix(),
                             'bytes': path.stat().st_size, 'sha256': sha(path), 'width': width, 'height': height})
            shutil.copy2(path, payload)
        structural = data['structural']
        validation = {key: structural[key] for key in ('meshes', 'primitives', 'triangles', 'materials', 'images', 'selfContained', 'cameras', 'lights')}
        validation.update({'embeddedImages': structural['images'], 'externalImages': 0,
                           'artworkSlots': structural['artworkSlots'], 'animation': structural['animation'],
                           'geometryPreservation': structural['geometryParity'],
                           'artworkPreservation': 'Every prepared face PNG is embedded byte-for-byte in its named artwork slot.',
                           'godot': {'version': audit['godot']['engine'], 'headlessImport': 'passed',
                                     'endpointInspection': 'Closed/Open world bounds, named parts, decoded images and artwork UVs verified.'},
                           'editableSource': 'Reopened in Blender ' + source_report['blender'] + '; packed resources and both poses checked.',
                           'previewLighting': 'Actual GLB reimport in a neutral white studio, Standard view transform, exposure -1.0; dimensions recorded per preview.'})
        manifest = {'schemaVersion': 1, 'id': asset_id, 'version': args.version, 'title': title,
                    'creator': 'Lincoln Aleixo', 'license': 'CC-BY-NC-ND-4.0', 'licenseScope': RIGHTS,
                    'date': args.date, 'coordinateSystem': {'units': 'meters', 'axes': 'X width, Y up, positive Z front',
                                                           'pivot': 'bottom center of nominal closed envelope'},
                    'nominalDimensionsMm': data['construction']['nominalDimensionsMm'],
                    'measurementBasis': data['construction']['referenceBasis'] + '. ' + TEMPLATES[console]['limitations'],
                    'changes': ['Added ' + game['edition'] + ' artwork to the independently released neutral box.',
                                'Preserved complete template geometry and Open animation.',
                                'Included prepared face PNGs, exact source/edit provenance and documented restoration limits.'],
                    'validation': validation, 'previews': previews, 'release': {'tag': tag, 'archive': {}}, 'files': {}}
        draft = temporary / 'manifest.json'
        write_json(draft, manifest)
        archive_name = asset_id + '-' + args.version + '.zip'
        archive = temporary / archive_name
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'package.py'), str(draft), str(payload), str(archive)], check=True)
        destination = args.base / 'packages' / archive_name
        staged_payload = args.base / 'payloads' / asset_id
        if destination.exists() and sha(destination) != sha(archive):
            raise ValueError('Refusing to replace a differing versioned archive: ' + destination.name)
        if staged_payload.exists():
            existing = {p.relative_to(staged_payload).as_posix(): sha(p) for p in staged_payload.rglob('*') if p.is_file()}
            incoming = {p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob('*') if p.is_file()}
            if existing != incoming:
                raise ValueError('Existing payload differs; use a fresh staging directory: ' + asset_id)
        tracked = subprocess.run(['git', 'cat-file', '-e', 'HEAD:' + manifest_path.relative_to(ROOT).as_posix()],
                                 cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if tracked and manifest_path.read_bytes() != draft.read_bytes():
            raise ValueError('Refusing to rewrite a committed version manifest: ' + asset_id)
        draft_destination = args.base / 'manifests' / (asset_id + '-' + args.version + '.json')
        draft_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(draft, draft_destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(archive, destination)
        if not staged_payload.exists():
            shutil.copytree(payload, staged_payload)
        if args.install:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(draft, manifest_path)
            for name, text in docs.items():
                if name == 'README.md':
                    for view in VIEWS:
                        text = text.replace('](' + view + '.png)', '](previews/' + args.version + '/' + view + '.png)')
                    # Artwork is distributed in the release, not ordinary Git.
                    for slot in images:
                        text = text.replace(f'[`{slot}.png`](artwork/{slot}.png)', f'`artwork/{slot}.png` in release ZIP')
                (directory / name).write_text(text)
            preview_directory = directory / 'previews' / args.version
            preview_directory.mkdir(parents=True, exist_ok=True)
            for view in VIEWS:
                shutil.copy2(payload / (view + '.png'), preview_directory)
        verify_draft_package(draft_destination, destination)
    return {'id': asset_id, 'title': title, 'latest': args.version, 'manifest': manifest_path.relative_to(ROOT).as_posix(),
            'displayTitle': game['name'] + ' · Retail box', 'kind': 'BOX REPRODUCTION',
            'description': game['description'], 'credits': (directory.relative_to(ROOT) / 'CREDITS.md').as_posix(), 'rights': RIGHTS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT / 'dist' / 'game-boxes-20261016')
    parser.add_argument('--version', default=VERSION)
    parser.add_argument('--date', default=DATE)
    parser.add_argument('--console', action='append', choices=tuple(GAMES))
    parser.add_argument('--install', action='store_true', help='install metadata/previews and update catalog after the neutral-template commit')
    args = parser.parse_args()
    args.base = args.base.resolve()
    if not SEMVER.fullmatch(args.version):
        raise ValueError('Invalid version')
    selected = args.console or list(GAMES)
    if args.install:
        for console in selected:
            path = f'assets/templates/{console}/box/versions/0.1.0.json'
            subprocess.run(['git', 'cat-file', '-e', 'HEAD:' + path], cwd=ROOT, check=True)
    audit = json.loads((args.base / 'reproduction-validation.json').read_text())
    source = json.loads((args.base / 'reproduction-godot-audit' / 'source-reopen-report.json').read_text())
    sources = json.loads((ROOT / 'docs' / 'game-box-artwork-sources.json').read_text())
    if audit.get('status') != 'passed' or audit.get('godot', {}).get('status') != 'passed' or source.get('status') != 'passed':
        raise ValueError('Successful structural, engine and source-reopen reports are required')
    inputs = {console: audit_inputs(console, args, audit, source, sources) for console in selected}
    entries = [stage(console, args, inputs[console], audit, source) for console in selected]
    if args.install:
        catalog_path = ROOT / 'catalog.json'
        catalog = json.loads(catalog_path.read_text())
        for entry in entries:
            positions = [i for i, item in enumerate(catalog['assets']) if item['id'] == entry['id']]
            if len(positions) > 1:
                raise ValueError('Duplicate catalog entry: ' + entry['id'])
            if positions:
                catalog['assets'][positions[0]] = entry
            else:
                catalog['assets'].append(entry)
        write_json(catalog_path, catalog)
        for entry in entries:
            verify_package(ROOT / entry['manifest'], args.base / 'packages' / (entry['id'] + '-' + args.version + '.zip'))
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'verify.py')], check=True)
    print(('Installed' if args.install else 'Drafted') + ' and verified ' + str(len(entries)) + ' box reproductions.')


if __name__ == '__main__':
    main()
