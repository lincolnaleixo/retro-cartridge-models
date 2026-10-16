#!/usr/bin/env python3
"""Stage audited neutral packaging templates as independent immutable releases.

Run after create_game_boxes.py and inspect_game_box.py complete. The source and
engine reports must identify the exact current binary hashes. Repeated runs are
safe: an identical archive is reused; a differing archive or existing tag is
never replaced. Use a new version or a separate staging directory for changes.
"""
import argparse
import json
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

from verify import ROOT, SEMVER, sha, verify_package

VERSION = '0.1.0'
DATE = '2026-10-16'
VIEWS = ('hero', 'front', 'rear', 'top', 'bottom', 'open')
RIGHTS = ('Original contributions: CC BY-NC-ND 4.0. Product designs and third-party '
          'marks are excluded. No game artwork, source photograph or copied logo is included.')
CONFIG = {
    'nes': {
        'title': 'NES — early US retail box template',
        'display': 'NES · Empty retail box',
        'description': 'A pristine portrait carton with an integrated unpunched hanger, tuck lid, dust flaps, interlocking bottom, black sleeve and white foam spacer.',
        'evidence': 'nintendo-box-reference-evidence.json',
        'features': [
            'Real-thickness coated paperboard, unprinted inner stock, scored folds and an internal glue lap.',
            'An early integrated rear hanger stays flush and unpunched; its artwork continues across the die-cut boundary.',
            'The top lid and tuck tongue counter-fold together before the two dust ears open.',
            'Four interlocking bottom panels remain folded during normal opening. Their inspection hinges and the rear hanger retain separate disassembly-angle metadata.',
            'A removable empty black sleeve with a thumb notch sits above the white foam bottom spacer.',
        ],
        'limitations': 'Dimensions, die cuts, foam size and paper gauge are inferred. The early hanger is a selected US variant, not a claim about every NES printing. Foam pore shading is procedural in the source; the portable export retains its clean base material.',
    },
    'snes': {
        'title': 'Super Nintendo — western retail box template',
        'display': 'Super Nintendo · Empty retail box',
        'description': 'A pristine landscape carton with two articulated end closures, tuck tongues, dust ears and a removable folded tray fitted to the western SNES cartridge envelope.',
        'evidence': 'nintendo-box-reference-evidence.json',
        'features': [
            'Real-thickness coated paperboard tube with unprinted inner stock, exposed cut edges, scored folds and a glue lap.',
            'Left and right printed end panels have independent tuck tongues and upper/lower dust ears.',
            'The removable white tray uses hollow folded rails, a 138 × 89.5 mm approximate cartridge opening, finger notches and tucked corner ears.',
            'The normal Open clip leaves the tray seated; its extraction axis and optional translation are recorded separately.',
        ],
        'limitations': 'Protector-fit dimensions establish an approximate envelope. Paper gauge, tray aperture, flap lengths and folds are inferred from photographs, not measured factory die lines.',
    },
    'nintendo-64': {
        'title': 'Nintendo 64 — western retail box template',
        'display': 'Nintendo 64 · Empty retail box',
        'description': 'A pristine landscape carton with articulated end closures and a removable folded white cradle sized for the Nintendo 64 Game Pak.',
        'evidence': 'nintendo-box-reference-evidence.json',
        'features': [
            'Real-thickness coated paperboard tube with unprinted inner stock, exposed cut edges, scored folds and a glue lap.',
            'Both end panels, their tuck tongues and four dust ears retain independent pivots.',
            'The removable folded white cradle has an approximate 119.4 × 80.8 mm cartridge opening, curved finger access and separate inner returns.',
            'The normal Open clip leaves the tray seated; its extraction axis and optional translation are recorded separately.',
        ],
        'limitations': 'Protector-fit dimensions establish an approximate envelope. The tray construction is informed by original and replacement examples; its die line and board thickness are not asserted to match a specific Nintendo factory revision.',
    },
    'mega-drive': {
        'title': 'Mega Drive — western clamshell box template',
        'display': 'Mega Drive · Empty clamshell',
        'description': 'A fresh black clamshell with two spine folds, transparent cover sleeve, sideways cartridge guides, booklet retainers and an intact retail hanger.',
        'evidence': 'mega-drive-box-reference-evidence.json',
        'features': [
            'Hollow black molded front and rear shells with two separate spine pivots and a 180-degree open spread.',
            'Independent clear cover sleeve above the unprinted front, spine and rear paper surfaces.',
            'Opposing sideways cartridge guides with spring tongues, booklet retainers, snap details and tooling witness marks.',
            'The intact retail hanger is a named separate part. A neutral booklet placeholder and cartridge placement anchor remain editable.',
        ],
        'limitations': 'The 129 × 177 × 26 mm body and 188 mm height including hanger are nominal estimates from protector fit and specimen photographs. Mold revision, clip offsets, sleeve thickness and booklet pagination are approximate. Flexible spine folds use rigid pivots.',
    },
    'playstation-1': {
        'title': 'PlayStation 1 — clear-tray jewel case template',
        'display': 'PlayStation 1 · Empty jewel case',
        'description': 'A clean standard jewel case with a clear removable tray, hinged lid, disc-retaining hub, blank booklet and a two-sided folded tray card.',
        'evidence': 'playstation-box-reference-evidence.json',
        'features': [
            'A standard-compatible 142.35 × 124.75 × 10.4 mm envelope with a separate front-lid pivot.',
            'Clear molded lid and removable tray with a central retaining hub and approximate rib, clip and hinge detail.',
            'Independent front booklet, booklet reverse, rear wrap and inner wrap artwork targets; spine folds share the tray-card UV field.',
            'The Open clip rotates the lid to 110 degrees. The standalone CD remains a separate media asset.',
        ],
        'limitations': 'The envelope uses midpoint values from CMC assembly inspection ranges, not proof of the original Sony supplier. Fine molded features, booklet leaves and paper-fit dimensions are approximate. Clear plastic rendering depends on the importing engine.',
    },
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def png_dimensions(path):
    header = path.read_bytes()[:24]
    if header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        raise ValueError('Invalid preview PNG: ' + str(path))
    return struct.unpack('>II', header[16:24])


def source_links(console, evidence):
    sources = evidence['sources']
    if 'models' in evidence:
        selected = evidence['models'][console]['sourceIds']
        sources = [source for source in sources if source.get('id') in selected]
    return '\n'.join('- [' + source.get('kind', source.get('type', 'Reference')) + ']('
                     + source['url'] + '). ' + source.get('usedFor', source.get('limitations', ''))
                     for source in sources)


def release_changes(console, config, version):
    if version == '0.1.0':
        return ['Added the first independent neutral box release with pristine materials, real packaging parts and separately addressable artwork targets.'] + config['features'] + [
            'Preserved meter scale, +Y up, +Z front and a bottom-center closed-envelope pivot; included one two-second Open animation in the portable export.',
            'Verified the actual exported poses, self-contained resources, named parts and UVs; imported and evaluated the animation in Godot and reopened the editable Blender source.',
            'Recorded source-specific approximation limits and retained existing cartridge and disc releases unchanged.',
        ]
    if console == 'playstation-1' and version == '0.2.0':
        return [
            'Restored visibility of the clear disc tray, circular recess, retaining hub, ribs and lid rims by increasing transparent-material coverage and refining surface roughness.',
            'Retained transmission shading plus an alpha fallback for engines that do not import KHR_materials_transmission; reviewed the actual clear-plastic appearance in Blender and Godot.',
            'Updated the previous released editable source while preserving positions, normals, triangle indices, artwork UVs, hinge transforms and opening animation.',
            'Included new actual-export previews, exact-input engine and source validation reports; preserved the 0.1.0 release and separate CD models unchanged.',
        ]
    if console == 'mega-drive' and version == '0.2.0':
        return [
            'Corrected the spine artwork U direction so lettering reads normally from outside the left edge rather than appearing mirrored.',
            'Applied the same idempotent correction when reopening a previous editable source; only SpinePrint U coordinates change, with V, vertices, normals, indices, hinges and animation retained.',
            'Added a printed-face handedness regression check, actual-export spine proofs and hash-bound Blender/Godot validation.',
            'Preserved the 0.1.0 release and every separate cartridge, disc and other box release unchanged.',
        ]
    raise ValueError('Explicit template release notes are required for ' + console + ' ' + version)


def versioned_changelog(title, version, date, changes, previous=''):
    """Prepend this release while retaining every earlier release section."""
    sections = re.split(r'(?m)(?=^## )', previous)
    history = ''.join(section for section in sections
                      if section.startswith('## ') and not re.match(
                          r'## ' + re.escape(version) + r'(?:\s|$)', section))
    entry = '# Changelog — ' + title + '\n\n## ' + version + ' — ' + date + '\n\n'
    entry += '\n'.join('- ' + change for change in changes) + '\n'
    return entry + ('\n' + history if history else '')


def texts(console, config, construction, structural, engine, source, version, date, evidence, previous_changelog=''):
    dimensions = ' × '.join(f'{value:g}' for value in construction['nominalDimensionsMm'])
    slots = '\n'.join(f'| `{name}` | `{slot}` |' for name, slot in construction['artworkSlots'].items())
    features = '\n'.join('- ' + feature for feature in config['features'])
    hinge_names = ', '.join('`' + name + '`' for name in structural['hinges'])
    material_note = ''
    if console == 'playstation-1' and version == '0.2.0':
        material_note = ('\nThe clear shell, rims/catches and tray use alpha coverage 0.16, 0.35 and 0.25, '
                         'respectively, alongside transmission 1.0 and IOR 1.59. This is a reviewed '
                         'portable approximation: Godot 4.7.2 Compatibility does not import the '
                         'transmission extension and uses the alpha fallback. The actual tray/hub '
                         'remains visible and the art remains readable; reflections, tint and '
                         'transmission differ between engines.\n')
    if console == 'mega-drive' and version == '0.2.0':
        material_note = ('\nThe spine UV contract is corrected in this release: viewed from outside the left '
                         'edge (-X) with +Y up, U increases from the rear edge (-Z) to the front edge (+Z). '
                         'The previous release mirrored spine print. Only `SpinePrint` U coordinates changed; '
                         'the mesh, V coordinates, other print targets and opening animation are preserved.\n')
        rounding = structural.get('geometryParity', {}).get('nonArtworkUvFloat32Rounding', [])
        if rounding:
            material_note += (f"\nExport also rounded {sum(item['changedScalars'] for item in rounding)} "
                              'unprinted UV scalars by at most two representable float32 steps. '
                              'The exact migration and rounding are recorded in `glb-inspection.json`.\n')
    body = f'''# {config['title']}

**Version:** {version} · **Date:** {date} · **Creator:** Lincoln Aleixo

{config['description']}
{material_note}

![Closed box](hero.png)

![Open box](open.png)

{features}

## Import contract

| Property | Value |
| --- | --- |
| Units and axes | Meters; X width, Y up, +Z front |
| Pivot | Bottom center of the nominal closed envelope |
| Nominal closed size | {dimensions} mm |
| Initial pose | Closed |
| Animation | `Open`, 0 to 2 seconds |
| Game media | None; cartridge/CD assets are separate |

The editable source preserves separate packaging parts. The portable GLB keeps named artwork surfaces, hinge nodes and removable-insert anchors. Artwork is confined to exterior or explicitly designated paper faces; inner carton stock remains unprinted. These are pristine materials without simulated wear, stains or yellowing.

### Artwork targets

| Named surface | Artwork slot |
| --- | --- |
{slots}

Slots use normalized UV coordinates with upright exterior print orientation. A slot may span several named pieces; those pieces share a continuous UV field where a die cut or fold interrupts the paper. The neutral surfaces carry no game artwork.

### Articulation

The `Open` clip preserves a closed frame at 0 seconds and the inspection opening at 2 seconds. Named hinge nodes: {hinge_names}. Hinge extras record the axis, endpoint quaternions and opening phase. Paper and flexible plastic are approximated by rigid articulated parts, not a deformation simulation.

## Validation and limitations

The self-contained GLB passed structural geometry, hierarchy, artwork UV, embedded-resource and animation-endpoint checks. Godot {engine['engine']} imported it and verified both Open endpoints, named parts and artwork surfaces. Blender {source['blender']} reopened the editable source and checked both poses. Exact binary hashes and measured differences are included in the release validation reports.

{config['limitations']} No manuals with printed content, promotional inserts, shrinkwrap or game media are included. A detached-insert image, where provided, is a separate inspection arrangement; it does not change the default Open clip.

## Generate and review

From the repository root:

```sh
blender -b --python tools/create_game_boxes.py -- --console {console}
python3 tools/inspect_game_box.py dist/game-boxes-20261016/templates/{console}-box/{console}-box.glb
```

The release contains editable `.blend`, portable `.glb`, six standard views, construction metadata, reference evidence, validation reports and license notices. The repository retains versioned preview snapshots and metadata. See [credits](CREDITS.md) and [changelog](CHANGELOG.md).

{RIGHTS}
'''
    credits = f'''# Credits — {config['title']}

Original parametric reconstruction and release: **Lincoln Aleixo**.

The geometry is authored from construction observations and the measurement basis recorded below. No reference photograph, scanned mesh, game artwork or copied manufacturer logo is embedded in this neutral template. Product design, brand names and any third-party rights remain outside the license for original contributions. Attribution does not establish a license in those separate elements.

## Reference basis

{source_links(console, evidence)}

The release includes `reference-evidence.json` with exact source URLs, observations, edition choices and measurement caveats. {config['limitations']}

## License

Original contributions are licensed under **Creative Commons Attribution–NonCommercial–NoDerivatives 4.0 International**. Attribution is required; commercial use and redistribution of adaptations are not granted by this license. The editable source does not change those terms. Read `LICENSE` and `NOTICE.md` in the release.
'''
    changelog = versioned_changelog(config['title'], version, date,
                                   release_changes(console, config, version), previous_changelog)
    return {'README.md': body, 'CREDITS.md': credits, 'CHANGELOG.md': changelog}


def audit_inputs(console, base, validation, source_report):
    asset_id = console + '-box'
    folder = base / 'templates' / asset_id
    structural = next(item for item in validation['assets'] if item['file'] == asset_id + '.glb')
    engine = next(item for item in validation['godot']['assets'] if item['id'] == asset_id)
    source = next(item for item in source_report['assets'] if item['id'] == asset_id)
    for suffix, records in (('.glb', (structural, engine)), ('.blend', (source,))):
        path = folder / (asset_id + suffix)
        current = sha(path)
        if any(record.get('sha256') != current for record in records):
            raise ValueError('Stale validation report for ' + path.name)
    if structural.get('status') != 'passed' or not engine.get('namedPartsPresent'):
        raise ValueError('Incomplete validation for ' + asset_id)
    for view in VIEWS:
        png_dimensions(folder / (view + '.png'))
    construction = json.loads((folder / 'construction.json').read_text())
    if construction['artworkSlots'] != structural['artworkSlots']:
        raise ValueError('Construction artwork contract differs from audited GLB: ' + asset_id)
    return folder, structural, engine, source, construction


def stage(console, config, args, audit, source_report, inputs):
    asset_id = console + '-box'
    folder, structural, engine_asset, source_asset, construction = inputs
    directory = ROOT / 'assets' / 'templates' / console / 'box'
    manifest_path = directory / 'versions' / (args.version + '.json')
    tag = asset_id + '-v' + args.version
    if subprocess.run(['git', 'show-ref', '--verify', '--quiet', 'refs/tags/' + tag], cwd=ROOT).returncode == 0:
        raise ValueError('Refusing to modify an existing tagged release: ' + tag)
    evidence_path = ROOT / 'docs' / config['evidence']
    evidence = json.loads(evidence_path.read_text())
    engine = {'status': 'passed', 'engine': audit['godot']['engine'], 'assets': [engine_asset]}
    source = {key: value for key, value in source_report.items() if key != 'assets'}
    source['assets'] = [source_asset]
    previous_changelog = directory / 'CHANGELOG.md'
    docs = texts(console, config, construction, structural, engine, source,
                 args.version, args.date, evidence,
                 previous_changelog.read_text() if previous_changelog.is_file() else '')
    if (folder / 'insert-inspection.png').is_file():
        docs['README.md'] += '\n## Detached insert inspection\n\n![Detached packaging insert](insert-inspection.png)\n'
    with tempfile.TemporaryDirectory(prefix=asset_id + '-', dir=args.base) as temporary:
        temporary = Path(temporary)
        payload = temporary / 'payload'
        payload.mkdir()
        for suffix in ('.blend', '.glb'):
            shutil.copy2(folder / (asset_id + suffix), payload)
        shutil.copy2(folder / 'construction.json', payload)
        shutil.copy2(evidence_path, payload / 'reference-evidence.json')
        for name in ('LICENSE', 'NOTICE.md'):
            shutil.copy2(ROOT / name, payload / name)
        for name, content in docs.items():
            (payload / name).write_text(content)
        write_json(payload / 'glb-inspection.json', structural)
        write_json(payload / 'godot-import-report.json', engine)
        write_json(payload / 'source-reopen-report.json', source)
        views = list(VIEWS)
        if (folder / 'insert-inspection.png').is_file():
            views.append('insert-inspection')
        previews = []
        for view in views:
            image = folder / (view + '.png')
            width, height = png_dimensions(image)
            relative = directory.relative_to(ROOT) / 'previews' / args.version / image.name
            previews.append({'view': view, 'path': relative.as_posix(), 'bytes': image.stat().st_size,
                             'sha256': sha(image), 'width': width, 'height': height})
            shutil.copy2(image, payload)
        summary = {key: structural[key] for key in ('meshes', 'primitives', 'triangles', 'materials',
                   'images', 'selfContained', 'cameras', 'lights')}
        summary.update({'embeddedImages': structural['images'], 'externalImages': 0,
                        'artworkSlots': structural['artworkSlots'], 'animation': structural['animation'],
                        'godot': {'version': audit['godot']['engine'], 'headlessImport': 'passed',
                                  'endpointInspection': 'Closed/Open world vertex bounds, named packaging parts and artwork UVs verified.'},
                        'previewLighting': 'Actual GLB reimport in a neutral white studio, Standard view transform, exposure -1.0. Pixel dimensions are recorded per preview. Detached-insert views are separate inspection arrangements.',
                        'editableSource': 'Reopened in Blender ' + source_report['blender'] + '; packed resources, named parts and both poses checked.'})
        if structural.get('geometryParity'):
            summary['geometryPreservation'] = structural['geometryParity']
        manifest = {'schemaVersion': 1, 'id': asset_id, 'version': args.version,
                    'title': config['title'], 'creator': 'Lincoln Aleixo', 'license': 'CC-BY-NC-ND-4.0',
                    'licenseScope': RIGHTS, 'date': args.date,
                    'coordinateSystem': {'units': 'meters', 'axes': 'X width, Y up, positive Z front',
                                         'pivot': 'bottom center of nominal closed envelope'},
                    'nominalDimensionsMm': construction['nominalDimensionsMm'],
                    'measurementBasis': construction['referenceBasis'] + '. ' + config['limitations'],
                    'changes': release_changes(console, config, args.version),
                    'validation': summary, 'previews': previews,
                    'release': {'tag': tag, 'archive': {}}, 'files': {}}
        draft_manifest = temporary / 'manifest.json'
        write_json(draft_manifest, manifest)
        archive_name = asset_id + '-' + args.version + '.zip'
        archive = temporary / archive_name
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'package.py'), str(draft_manifest),
                        str(payload), str(archive)], check=True)
        destination = args.base / 'packages' / archive_name
        if destination.exists() and sha(destination) != sha(archive):
            raise ValueError('Refusing to replace a differing versioned archive: ' + str(destination))
        tracked = subprocess.run(['git', 'cat-file', '-e', 'HEAD:' + manifest_path.relative_to(ROOT).as_posix()],
                                 cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if tracked and manifest_path.read_bytes() != draft_manifest.read_bytes():
            raise ValueError('Refusing to rewrite a committed version manifest: ' + str(manifest_path))
        staged_payload = args.base / 'payloads' / asset_id
        if staged_payload.exists():
            existing = {p.relative_to(staged_payload).as_posix(): sha(p) for p in staged_payload.rglob('*') if p.is_file()}
            incoming = {p.relative_to(payload).as_posix(): sha(p) for p in payload.rglob('*') if p.is_file()}
            if existing != incoming:
                raise ValueError('Existing payload differs; select a fresh staging directory: ' + str(staged_payload))
        # All input and archive guards pass before public metadata is installed.
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(draft_manifest, manifest_path)
        for name in docs:
            content = docs[name]
            if name == 'README.md':
                for view in views:
                    content = content.replace('](' + view + '.png)', '](previews/' + args.version + '/' + view + '.png)')
            (directory / name).write_text(content)
        preview_directory = directory / 'previews' / args.version
        preview_directory.mkdir(parents=True, exist_ok=True)
        for view in views:
            shutil.copy2(payload / (view + '.png'), preview_directory)
        if not staged_payload.exists():
            shutil.copytree(payload, staged_payload)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(archive, destination)
    return {'id': asset_id, 'title': config['title'], 'latest': args.version,
            'manifest': manifest_path.relative_to(ROOT).as_posix(), 'displayTitle': config['display'],
            'kind': 'BOX TEMPLATE', 'description': config['description'],
            'credits': (directory.relative_to(ROOT) / 'CREDITS.md').as_posix(), 'rights': RIGHTS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT / 'dist' / 'game-boxes-20261016')
    parser.add_argument('--version', default=VERSION)
    parser.add_argument('--date', default=DATE)
    parser.add_argument('--console', action='append', choices=tuple(CONFIG), help='stage selected console(s); defaults to all five')
    args = parser.parse_args()
    args.base = args.base.resolve()
    if not SEMVER.fullmatch(args.version):
        raise ValueError('Invalid version')
    audit = json.loads((args.base / 'packaging-validation.json').read_text())
    source = json.loads((args.base / 'godot-audit' / 'source-reopen-report.json').read_text())
    if audit.get('status') != 'passed' or audit.get('godot', {}).get('status') != 'passed' or source.get('status') != 'passed':
        raise ValueError('Successful structural, Godot and source-reopen reports are required')
    selected = args.console or list(CONFIG)
    inputs = {console: audit_inputs(console, args.base, audit, source) for console in selected}
    entries = [stage(console, CONFIG[console], args, audit, source, inputs[console]) for console in selected]
    catalog_path = ROOT / 'catalog.json'
    catalog = json.loads(catalog_path.read_text())
    for entry in entries:
        old = [index for index, item in enumerate(catalog['assets']) if item['id'] == entry['id']]
        if len(old) > 1:
            raise ValueError('Duplicate catalog entry: ' + entry['id'])
        if old:
            catalog['assets'][old[0]] = entry
        else:
            catalog['assets'].append(entry)
    write_json(catalog_path, catalog)
    for entry in entries:
        verify_package(ROOT / entry['manifest'], args.base / 'packages' / (entry['id'] + '-' + args.version + '.zip'))
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'verify.py')], check=True)
    print('Staged and verified ' + str(len(entries)) + ' neutral packaging releases.')


if __name__ == '__main__':
    main()
