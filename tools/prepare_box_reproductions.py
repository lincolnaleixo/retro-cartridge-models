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

VERSION = '0.3.0'
DATE = '2026-10-16'
RIGHTS = ('Original modeling contributions only: CC BY-NC-ND 4.0. Game artwork, '
          'marks, product designs, scans and source photography are excluded. '
          'Attribution and the maintainer\'s request do not grant rights to those elements.')
GAMES = {
    'nes': {
        'game': 'super-mario-bros', 'name': 'Super Mario Bros.',
        'consoleName': 'NES', 'edition': 'Early US black-box edition with an integrated rear hanger',
        'description': 'A pristine early Super Mario Bros. carton with articulated tuck lid, dust ears, black sleeve, foam spacer and the matching removable cartridge.',
    },
    'snes': {
        'game': 'super-mario-world', 'name': 'Super Mario World',
        'consoleName': 'Super Nintendo', 'edition': 'US retail cardboard-box presentation',
        'description': 'A pristine Super Mario World retail carton with printed panels, two articulated end closures and the matching cartridge in its removable folded tray.',
    },
    'nintendo-64': {
        'game': 'super-mario-64', 'name': 'Super Mario 64',
        'consoleName': 'Nintendo 64', 'edition': 'Original US K-A retail presentation',
        'description': 'A pristine original-edition Super Mario 64 carton with printed panels, articulated end closures and the matching Game Pak in its removable folded cradle.',
    },
    'mega-drive': {
        'game': 'sonic-the-hedgehog', 'name': 'Sonic the Hedgehog',
        'consoleName': 'Mega Drive', 'edition': 'Western PAL Mega Drive presentation',
        'description': 'A fresh Sonic the Hedgehog clamshell with the PAL wrap, restored booklet covers, intact retail hanger, articulated spine and matching removable cartridge.',
    },
    'playstation-1': {
        'game': 'crash-bandicoot', 'name': 'Crash Bandicoot',
        'consoleName': 'PlayStation 1', 'edition': 'Original US black-label SCUS-94900 presentation',
        'description': 'A clean Crash Bandicoot clear-tray jewel case with original-edition paper inserts, articulated lid and the matching removable disc on the hub.',
    },
}

REFINEMENTS = {
    'nes': [
        'Rebuilt top and side black fields with clean title and Nintendo glyphs from the matching original rear scan, removing blurred coral ink and white abrasion.',
        'Transcribed the legible original address and warranty wording with a documented approximate narrow sans-serif; retained original front illustration, gold seal and identifiable printed stars.',
        'Reduced scan-screen noise on the original rear and repaired explicitly reviewed empty-field blemishes without thresholding across illustrations or text.',
    ],
    'snes': [
        'Replaced the clipped photographic rear with a complete matching US 1992 scan, preserving all four original screenshots, barcode and retail copy.',
        'Reconstructed four clean edge panels from original period artwork; restored distinct flying and diving Mario poses on the opposite sides, crisp title marks and uninterrupted black fields.',
        'Transcribed damaged legal lines with exact source wording and an approximate typeface; documented source-resolution and reconstruction limits per panel.',
    ],
    'nintendo-64': [
        'Replaced the soft front with clean original US K-A artwork and returned to the full-resolution original rear scan for a 3072-pixel descreened print.',
        'Restored clean original title and console marks on the narrow panels; repaired worn trim and estimated photographic exposure while preserving their original duotone character art.',
        'Documented approximate reconstructed empty fields and the remaining photographic character-detail limits.',
    ],
    'mega-drive': [
        'Removed broad fold glare and dust from the Sonic spine by restoring its measured dark grid while retaining the original title and Mega Drive logo pixels.',
        'Reduced color speckle across the wrap and booklet covers with gentle luminance/chroma descreening; retained the original screenshots and multilingual rear text.',
    ],
    'playstation-1': [
        'Reduced coarse scanned halftone and color noise across the four paper inserts, using a gentler filter for fine rear legal type.',
        'Restored the plain black spine fields and narrow booklet trim, retaining the original SCUS-94900 lettering and complete rear layout.',
        'Adopted the neutral template clear-plastic revision: shell, rim and tray alpha of 0.16, 0.35 and 0.25 make molded details visible while retaining the Godot Compatibility transparency fallback.',
    ],
}

PRINT_POLISH = {
    'nes': [
        'Replaced the enlarged specimen-photo front with sharper Nintendo-attributed original illustration and reconstructed original title/console glyph contours at 4096-pixel height.',
        'Restored clean flat ink, angular Mario/block color regions, smooth lettering and readable edge panels; documented the reconstructed round seal and exact-wording typography where factory vector artwork is unavailable.',
        'Preserved the early no-REV-A layout and original rear screenshots; removed photographed paper wear rather than baking it into a newly unboxed reproduction.',
    ],
    'snes': [
        'Separated flat printed graphics from illustration shading to restore clean colors, typography and dark fields across all six panels.',
        'Rebuilt rear promotional and legal copy from the original wording while preserving the matching US edition layout and four original screenshots.',
        'Prepared close-up print proofs and documented approximations instead of treating enlarged scan pixels as recovered detail.',
    ],
    'nintendo-64': [
        'Retained the clean original K-A front and rebuilt the narrow duotone panels with matching period character artwork.',
        'Restored title/console marks and typeset the exact original rear wording independently of the illustration; preserved the original screenshots.',
        'Recorded source selections, reconstructed graphic elements and remaining original-art resolution limits per face.',
    ],
    'mega-drive': [
        'Adopted the independently published Mega Drive template with corrected spine lettering and cartridge retention geometry fitted to the unchanged full-size media.',
        'Traced original Sonic title and copy contours into clean antialiased ink; rebuilt the measured grid and restored cream/pink paper fields without photographed wear.',
        'Reconstructed the chrome Mega Drive plate and reflection bands, reused the archived clean SEGA wordmark and retained the original shaded character art, screenshots and multilingual rear copy.',
    ],
    'playstation-1': [
        'Refined all four original SCUS-94900 inserts for cleaner close-up print, treating illustrations, small type and solid fields separately.',
        'Preserved the original booklet/rear composition and the previously validated transparent case materials and articulation.',
        'Restored the matching 1994–2009 PlayStation vector wordmark and exact-wording NTSC U/C print; documented per-face changes and reconstruction limits.',
    ],
}


def identifier(console):
    return console + '-' + GAMES[console]['game'] + '-box'


def includes_media(version):
    """Keep source, fit and render validation mandatory after contents debuted."""
    if not SEMVER.fullmatch(version):
        raise ValueError('Invalid version')
    return tuple(map(int, version.split('.'))) >= (0, 3, 0)


def resolve_template(console, root=ROOT):
    """Resolve the exact independently released template selected by catalog."""
    asset_id = console + '-box'
    catalog = json.loads((root/'catalog.json').read_text())
    matches = [entry for entry in catalog['assets'] if entry['id'] == asset_id]
    if len(matches) != 1:
        raise ValueError('Expected one neutral template catalog entry: ' + asset_id)
    entry = matches[0]
    path = root / safe(entry['manifest'])
    manifest = json.loads(path.read_text())
    if manifest.get('id') != asset_id or manifest.get('version') != entry['latest']:
        raise ValueError('Neutral template catalog and manifest disagree: ' + asset_id)
    if not SEMVER.fullmatch(manifest['version']):
        raise ValueError('Invalid neutral template version: ' + asset_id)
    return path, manifest


def release_changes(console, version, template_version):
    game = GAMES[console]
    if console == 'playstation-1' and version == '0.4.0':
        return [
            f'Adopted the independently released PlayStation box template v{template_version}, with lighter non-refractive clear plastic and a separately visible retaining hub so both spines remain readable in Blender, Godot and the web viewer.',
            'Kept the left tray ribbing behind the folded spine paper using the corrected template, removing the physical overlay across the lettering while preserving positive rail thickness.',
            'Removed the template\'s hidden page-stack cap faces beneath the booklet print, eliminating striped depth interference in WebGL while preserving the visible page edges and both original printed faces.',
            'Included the matching Crash Bandicoot disc v0.2.0 with its darker center annulus and hidden overlapping top faces removed, eliminating radial depth-fighting artifacts in the web viewer.',
            'Preserved the original SCUS-94900 artwork and printed UVs, with geometry and Open articulation matching the corrected neutral template; verified that the inward booklet image matches page 28 of the original manual.',
            'Included left and right side inspection views and a mounted-disc hub close-up, in addition to the six standard previews and exact-hash source, fit and engine validation.',
            'Clear-plastic materials use a portable alpha approximation; photographic references do not establish factory tooling dimensions.',
        ]
    if version == '0.1.0':
        return ['Added ' + game['edition'] + ' artwork to the independently released neutral box.',
                'Preserved complete template geometry and Open animation.',
                'Included prepared face PNGs, exact source/edit provenance and documented restoration limits.']
    if version == '0.3.0':
        return [*PRINT_POLISH[console],
                f'Preserved the box subset geometry and Open animation from the independently released {console} template v{template_version}; artwork UVs match that selected template.',
                'Included the matching published cartridge or disc at its original scale beneath a removable Contents parent, preserving its geometry, materials and embedded images exactly.',
                'Included lossless prepared PNGs, source/edit provenance, six standard previews and exact-hash Blender/Godot validation; separately reviewed close-up renders of every exported face.']
    return [*REFINEMENTS[console],
            f'Used the independently released {console} box template v{template_version}; retained its decoded geometry, artwork UVs and Open animation.',
            'Included the revised prepared PNGs, transformation provenance and hash-bound Blender/Godot validation.']


def changelog_with_history(title, version, date, notes, existing=''):
    """Keep every historical release section when installing a new revision."""
    heading = f'## {version} — {date}'
    if any(line.startswith('## ' + version + ' ') for line in existing.splitlines()):
        raise ValueError('Changelog already contains version ' + version)
    history = existing.partition('\n## ')[2]
    text = f'# Changelog — {title}\n\n{heading}\n\n'
    text += '\n'.join('- ' + note for note in notes) + '\n'
    if history:
        text += '\n## ' + history.lstrip('\n')
    return text


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
    template_path, template_manifest = resolve_template(console)
    if template_manifest['files'][template.name]['sha256'] != sha(template):
        raise ValueError('Geometry comparison template differs from its independent v' + template_manifest['version'] + ' release: ' + console)
    if (parity.get('status') != 'passed' or parity.get('templateSha256') != sha(template)
            or parity.get('reproductionSha256') != sha(glb)):
        raise ValueError('Missing or stale neutral-template geometry comparison: ' + asset_id)
    construction = json.loads((folder / 'construction.json').read_text())
    if construction['artworkSlots'] != structural['artworkSlots']:
        raise ValueError('Construction metadata differs from audited artwork slots')
    for view in VIEWS:
        png_dimensions(folder / (view + '.png'))
    render_proof = None
    inspection_views = {}
    if includes_media(args.version):
        render_proof = json.loads((folder / 'render-proof.json').read_text())
        if render_proof.get('sha256') != sha(glb):
            raise ValueError('Previews were rendered from a different export: ' + asset_id)
        render_records = {item['view']: item for item in render_proof['renders']}
        selected_views = list(VIEWS)
        if console in ('nes', 'snes', 'nintendo-64'):
            selected_views.append('contents')
        if console == 'playstation-1' and tuple(map(int, args.version.split('.'))) >= (0, 4, 0):
            selected_views.extend(('left', 'right', 'hub-close'))
        for view in selected_views:
            record = render_records[view]
            if view in VIEWS and record['file'] != view + '.png':
                raise ValueError('Preview proof must identify its packaged view: ' + asset_id + ': ' + view)
            path = folder / safe(record['file'])
            if record['sha256'] != sha(path) or record['pixels'] != list(png_dimensions(path)):
                raise ValueError('Stale preview render: ' + asset_id + ': ' + view)
            if view == 'contents':
                if not record.get('inspectionPose'):
                    raise ValueError('Extracted contents view needs an explicit inspection pose')
            if view not in VIEWS:
                inspection_views[view + '.png'] = path
                record['file'] = 'inspection-views/' + view + '.png'
        render_proof['renders'] = [render_records[view] for view in selected_views]
    artwork = artwork_inputs(asset_id, args.base / 'artwork' / asset_id, glb, construction)
    references = selected_artwork_sources(source_catalog, asset_id)
    if set(references['selection'].get('slots', {})) != set(artwork[0]):
        raise ValueError('Source catalog does not identify every prepared artwork slot')
    evidence = geometry_evidence(console)
    composition = None
    content_sources = {}
    content_fit = None
    if includes_media(args.version):
        composition = json.loads((folder / 'content-composition.json').read_text())
        if (composition.get('status') != 'passed' or composition.get('assetId') != asset_id
                or composition.get('output') != {'glbSha256': sha(glb), 'blendSha256': sha(blend)}
                or composition.get('preservation', {}).get('status') != 'passed'
                or composition.get('contents', {}).get('scale') != [1, 1, 1]):
            raise ValueError('Missing, stale or rescaled media composition: ' + asset_id)
        media = composition['mediaSource']
        preservation = composition['preservation']
        if (preservation.get('composedGlbSha256') != sha(glb)
                or preservation.get('boxGlbSha256') != composition['boxSource']['glbSha256']
                or preservation.get('mediaGlbSha256') != media['glbSha256']
                or preservation.get('mediaScale') != [1, 1, 1]):
            raise ValueError('Stale media byte-preservation proof: ' + asset_id)
        catalog = json.loads((ROOT / 'catalog.json').read_text())
        media_entry = next(item for item in catalog['assets'] if item['id'] == asset_id[:-4])
        media_manifest_path = ROOT / safe(media_entry['manifest'])
        media_manifest = json.loads(media_manifest_path.read_text())
        if (media['assetId'] != media_entry['id'] or media['version'] != media_entry['latest']
                or media['manifestSha256'] != sha(media_manifest_path)
                or media['archiveSha256'] != media_manifest['release']['archive']['sha256']
                or media['glbSha256'] != media_manifest['files'][media['glbFile']]['sha256']
                or media['blendSha256'] != media_manifest['files'][media['blendFile']]['sha256']):
            raise ValueError('Media composition differs from its pinned published release: ' + asset_id)
        content_folder = folder / 'content-source'
        if (content_folder / 'release-manifest.json').read_bytes() != media_manifest_path.read_bytes():
            raise ValueError('Missing exact pinned media manifest: ' + asset_id)
        for path in content_folder.rglob('*'):
            if not path.is_file():
                continue
            name = path.relative_to(content_folder).as_posix()
            if name != 'release-manifest.json':
                expected = media_manifest['files'].get(name)
                if expected is None or expected['sha256'] != sha(path) or expected['bytes'] != path.stat().st_size:
                    raise ValueError('Media provenance file differs from its source release: ' + name)
            content_sources[name] = path
        required_evidence = {'release-manifest.json', 'CREDITS.md', 'LICENSE', 'NOTICE.md'}
        required_evidence.update(name for name in ('artwork-provenance.json', 'measurement-evidence.json')
                                 if name in media_manifest['files'])
        if not required_evidence <= set(content_sources):
            raise ValueError('Missing pinned media source credits/license: ' + asset_id)
        if composition.get('pinnedMediaEvidence', {}).get('files') != {name: sha(path) for name, path in content_sources.items()}:
            raise ValueError('Media evidence receipt differs from included source files: ' + asset_id)
        fit_catalog = json.loads((ROOT / 'docs' / 'box-content-fit.json').read_text())
        fit = next(item for item in fit_catalog['assets'] if item['assetId'] == asset_id)
        if (fit['composedGlbSha256'] != sha(glb) or fit['mediaSource'] != media
                or fit['contentsLocalTransform'] != composition['contents']
                or fit['surfaceFit']['status'] != 'passed'
                or set(fit['surfaceFit']['poses']) != {'closed', 'open'}
                or any(pose['intersectionPairs'] for pose in fit['surfaceFit']['poses'].values())):
            raise ValueError('Incomplete or stale final media fit audit: ' + asset_id)
        content_fit = {key: value for key, value in fit_catalog.items() if key not in ('assets', 'sources')}
        content_fit['assets'] = [fit]
        content_fit['sources'] = [source for source in fit_catalog['sources'] if source['id'] in fit['sourceIds']]
        if set(fit['sourceIds']) != {source['id'] for source in content_fit['sources']}:
            raise ValueError('Unresolved media fit reference: ' + asset_id)
        assert_public(content_fit)
        assert_public(composition)
    for value in (construction, structural, engine_asset, source_asset, references, evidence):
        assert_public(value)
    return {'folder': folder, 'structural': structural, 'engine': engine_asset,
            'source': source_asset, 'construction': construction, 'artwork': artwork,
            'references': references, 'evidence': evidence,
            'composition': composition, 'contentSources': content_sources,
            'renderProof': render_proof, 'inspectionViews': inspection_views,
            'contentFit': content_fit,
            'template': {'id': template_manifest['id'], 'version': template_manifest['version'],
                         'manifest': template_path.relative_to(ROOT).as_posix(), 'sha256': sha(template)}}


def documents(console, version, date, data, engine_version, blender_version):
    game, asset_id = GAMES[console], identifier(console)
    template_version = data['template']['version']
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
    media = data['composition']['mediaSource'] if data.get('composition') else None
    content_note = (f"The matching [{media['assetId']} v{media['version']}]({media['releaseUrl']}) is enclosed at its original scale beneath a removable `Contents` parent. Its published geometry, materials and embedded artwork are preserved exactly; its pinned manifest, original credits and provenance are included in `content-source/`. "
                    'The standalone cartridge/disc release remains unchanged. Contact positions are approximate rigid visualizations; flexible paper and plastic deformation are not simulated.'
                    if media else 'Cartridge and CD models remain separate assets; no game media is enclosed.')
    inspection_note = ('\nThe normal `Open` pose keeps the sleeve/tray seated inside the carton. '
                       'The release also includes `inspection-views/contents.png`, showing the original insert and cartridge moved out together for inspection. '
                       'This documented inspection pose does not change the exported default pose or animation.\n'
                       if 'contents.png' in data.get('inspectionViews', {}) else '')
    if {'left.png', 'right.png', 'hub-close.png'} <= set(data.get('inspectionViews', {})):
        inspection_note += ('\nThe package includes both side profiles and an open disc-hub close-up in '
                            '`inspection-views/`, rendered from this exact export.\n')
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

Selected edition: **{game['edition']}**. This reproduction uses the independently released [{console} neutral box template v{template_version}](https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/{console}-box-v{template_version}), with the same packaging geometry, hinge hierarchy, normalized print UVs and opening animation. {content_note} Printed booklet covers, where present, surround approximate blank interior leaves rather than a complete reproduced manual.
{inspection_note}

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

The self-contained GLB passed structural, image, UV, hierarchy and animation checks. Direct comparison of its box subset with the neutral template verified identical positions, normals, artwork UVs, triangle indices, node transforms and animation keys.{parity_note} The added contents are checked separately against their pinned source release. Godot {engine_version} imported and evaluated both animation endpoints; Blender {blender_version} reopened the packed editable source and checked both poses. Release reports bind these checks to exact binary hashes.

{TEMPLATES[console]['limitations']} Transparent materials and printed-paper highlights can vary between renderers. Godot does not honor the exported specular extension; apply a printed-material specular level of 0.18 when matching the Blender preview lighting.

The release includes editable `.blend`, portable `.glb`, six previews, construction and reference evidence, prepared PNGs, provenance and validation reports. The editable source supports moving or removing `Contents`. Re-exporting through a DCC tool may alter buffer precision. To preserve the original media bytes, use the repository's `tools/compose_box_contents.py` with a print-only box source and the pinned media release. See `content-composition.json` for exact source hashes, parent, placement and preservation checks, and the repository's restoration documentation for the rebuild workflow.

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

## Enclosed game media

{content_note}

## Rights scope

{RIGHTS} The maintainer requested these game-specific reproductions and their publication, but that request is not a license from the respective artwork or photograph owners. No redistribution license in third-party print, trademarks or source photography is asserted. Source attribution documents provenance and does not establish permission. The included prepared images and editable source do not expand the collection license. Read `LICENSE` and `NOTICE.md`.
'''
    history = ROOT/'assets'/'reproductions'/console/game['game']/'box'/'CHANGELOG.md'
    notes = release_changes(console, version, template_version)
    notes += ['Preserved the box subset template positions, normals, artwork UVs, indices, hinge transforms and the two-second Open clip, verified through a complete decoded-data comparison.' + parity_note,
              'Validated the self-contained export, exact embedded artwork, Godot import and both animation endpoints, then reopened the editable Blender source.',
              'Kept all previously published template, box, cartridge and disc releases unchanged.']
    changelog = changelog_with_history(title, version, date, notes, history.read_text() if history.exists() else '')
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
        for name, path in data.get('contentSources', {}).items():
            destination = payload / 'content-source' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        for name, path in data.get('inspectionViews', {}).items():
            (payload / 'inspection-views').mkdir(exist_ok=True)
            shutil.copy2(path, payload / 'inspection-views' / name)
        engine_report = {'status': 'passed', 'engine': audit['godot']['engine'], 'assets': [data['engine']]}
        source = {key: value for key, value in source_report.items() if key != 'assets'}
        source['assets'] = [data['source']]
        json_files = {'construction.json': data['construction'], 'geometry-reference-evidence.json': data['evidence'],
                      'artwork-sources.json': data['references'], 'artwork-provenance.json': provenance,
                      'artwork-mapping.json': mapping, 'artwork-embedding-report.json': embedding,
                      'glb-inspection.json': data['structural'], 'godot-import-report.json': engine_report,
                      'source-reopen-report.json': source}
        if data.get('composition'):
            json_files['content-composition.json'] = data['composition']
            json_files['content-fit-evidence.json'] = data['contentFit']
        if data.get('renderProof'):
            json_files['preview-render-report.json'] = data['renderProof']
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
                           'previewLighting': 'Actual GLB reimport in a neutral white studio, Standard view transform, exposure -1.0; bottom views add an angled underside softbox for legible print; model materials are unchanged and dimensions are recorded per preview.'})
        if data.get('composition'):
            validation['mediaPreservation'] = data['composition']['preservation']
        manifest = {'schemaVersion': 1, 'id': asset_id, 'version': args.version, 'title': title,
                    'creator': 'Lincoln Aleixo', 'license': 'CC-BY-NC-ND-4.0', 'licenseScope': RIGHTS,
                    'date': args.date, 'coordinateSystem': {'units': 'meters', 'axes': 'X width, Y up, positive Z front',
                                                           'pivot': 'bottom center of nominal closed envelope'},
                    'nominalDimensionsMm': data['construction']['nominalDimensionsMm'],
                    'measurementBasis': data['construction']['referenceBasis'] + '. ' + TEMPLATES[console]['limitations'],
                    'changes': release_changes(console, args.version, data['template']['version']),
                    'template': data['template'],
                    'validation': validation, 'previews': previews, 'release': {'tag': tag, 'archive': {}}, 'files': {}}
        if data.get('composition'):
            manifest['contents'] = data['composition']['mediaSource']
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
    parser.add_argument('--base', type=Path, default=ROOT / 'dist' / 'box-polish-20261016')
    parser.add_argument('--version', default=VERSION)
    parser.add_argument('--date', default=DATE)
    parser.add_argument('--console', action='append', choices=tuple(GAMES))
    parser.add_argument('--sources', type=Path, default=ROOT/'docs'/'game-box-artwork-sources.json',
                        help='edition-specific artwork source catalog used for this revision')
    parser.add_argument('--install', action='store_true', help='install metadata/previews and update catalog after the neutral-template commit')
    args = parser.parse_args()
    args.base = args.base.resolve()
    if not SEMVER.fullmatch(args.version):
        raise ValueError('Invalid version')
    selected = args.console or list(GAMES)
    if args.install:
        for console in selected:
            path, _ = resolve_template(console)
            relative = path.relative_to(ROOT).as_posix()
            committed = subprocess.run(['git', 'show', 'HEAD:' + relative], cwd=ROOT,
                                       check=True, capture_output=True).stdout
            if committed != path.read_bytes():
                raise ValueError('Selected template manifest must be committed before installing reproductions: ' + relative)
    audit = json.loads((args.base / 'reproduction-validation.json').read_text())
    source = json.loads((args.base / 'reproduction-godot-audit' / 'source-reopen-report.json').read_text())
    sources = json.loads(args.sources.read_text())
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
