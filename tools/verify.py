#!/usr/bin/env python3
"""Validate catalog metadata, preview checksums and versioned release packages."""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
SEMVER=re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()

def safe(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or not p.parts:
        raise ValueError(f'unsafe relative path: {name}')
    return name

def catalog_asset(asset_id):
    catalog=json.loads((ROOT/'catalog.json').read_text())
    matches=[asset for asset in catalog['assets'] if asset['id']==asset_id]
    if len(matches)!=1:raise ValueError(f'unknown or duplicate asset id: {asset_id}')
    return matches[0]

def manifest_path(asset,version=None):
    """Locate releases by the catalog rather than by their stable asset ID."""
    relative=PurePosixPath(safe(asset['manifest']))
    if (relative.parts[0]!='assets' or relative.parent.name!='versions'
            or len(relative.parts)<4 or relative.suffix!='.json'):
        raise ValueError(f'invalid catalog manifest path: {relative}')
    path=ROOT/relative
    if version is not None:
        if not SEMVER.fullmatch(version):raise ValueError('invalid version')
        path=path.with_name(version+'.json')
    if not path.resolve().is_relative_to((ROOT/'assets').resolve()):
        raise ValueError(f'manifest escapes assets: {relative}')
    return path

def version_manifests(asset):
    latest=manifest_path(asset)
    paths=list(latest.parent.glob('*.json'))
    if latest not in paths:raise ValueError(f'missing catalog manifest: {latest}')
    if any(not SEMVER.fullmatch(path.stem) for path in paths):
        raise ValueError(f'invalid version filename in {latest.parent}')
    return sorted(paths,key=lambda path:tuple(map(int,path.stem.split('.'))),reverse=True)

def preview_path(manifest,preview):
    """Resolve immutable release paths after a catalog directory relocation.

    Historical manifests retain assets/<id>/previews/... exactly as published.
    New manifests may use the current catalog directory. Neither form may read
    another asset, leave the preview directory or follow an escaping symlink.
    """
    directory=manifest_path(catalog_asset(manifest['id'])).parent.parent
    relative=PurePosixPath(safe(preview['path']))
    prefixes=(PurePosixPath(directory.relative_to(ROOT).as_posix()),
              PurePosixPath('assets')/manifest['id'])
    for prefix in prefixes:
        if relative.is_relative_to(prefix/'previews'):
            path=directory/'previews'/relative.relative_to(prefix/'previews')
            if path.resolve().is_relative_to(directory.resolve()/'previews'):
                return path
            raise ValueError(f'preview escapes asset directory: {relative}')
    raise ValueError(f'preview belongs to a different asset: {relative}')

def check_entry(path,entry):
    if path.stat().st_size!=entry['bytes'] or sha(path)!=entry['sha256']:
        raise ValueError(f'checksum/size mismatch: {path}')

def verify_manifest(path):
    m=json.loads(path.read_text())
    if m['schemaVersion']!=1 or not SEMVER.fullmatch(m['version']):raise ValueError(path)
    if m['license']!='CC-BY-NC-ND-4.0':raise ValueError('unexpected license')
    if not m['creator'] or not m['changes']:raise ValueError('missing attribution or changes')
    if m['release']['tag']!=f"{m['id']}-v{m['version']}":raise ValueError('tag mismatch')
    for entry in m['previews']:check_entry(preview_path(m,entry),entry)
    for name,entry in m['files'].items():
        safe(name)
        if not re.fullmatch('[a-f0-9]{64}',entry['sha256']) or entry['bytes']<=0:raise ValueError(name)
    for suffix in ('.blend','.glb'):
        if not any(n.endswith(suffix) for n in m['files']):raise ValueError('missing editable source/export')
    return m

def verify_package(manifest,path):
    m=verify_manifest(manifest);check_entry(path,m['release']['archive'])
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('duplicate ZIP entry')
        if set(names)!=set(m['files'])|{'FILES.json'}:raise ValueError('unexpected/missing package files')
        index=json.loads(z.read('FILES.json'))
        if index!={'assetId':m['id'],'version':m['version'],'files':m['files']}:raise ValueError('embedded manifest mismatch')
        for name,entry in m['files'].items():
            safe(name)
            if z.getinfo(name).file_size!=entry['bytes']:raise ValueError(name)
            h=hashlib.sha256()
            with z.open(name) as f:
                for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
            if h.hexdigest()!=entry['sha256']:raise ValueError(name)
    print(f"Verified {m['id']} {m['version']}: {len(m['files'])} package files")

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group()
    g.add_argument('--package',nargs=2,metavar=('MANIFEST','ZIP'))
    g.add_argument('--download',nargs=2,metavar=('ASSET','VERSION'))
    a=p.parse_args()
    if a.package:return verify_package(Path(a.package[0]).resolve(),Path(a.package[1]).resolve())
    if a.download:
        asset,version=a.download
        if not re.fullmatch('[a-z0-9-]+',asset) or not SEMVER.fullmatch(version):raise ValueError('invalid asset/version')
        path=manifest_path(catalog_asset(asset),version);m=verify_manifest(path)
        if (m['id'],m['version'])!=(asset,version):raise ValueError('requested release mismatch')
        archive=m['release']['archive'];url=archive['url']
        expected=f"https://github.com/lincolnaleixo/retro-cartridge-models/releases/download/{m['release']['tag']}/"
        if not url.startswith(expected):raise ValueError('unexpected release host/path')
        dest=ROOT/'.downloads'/asset/version/safe(archive['name']);dest.parent.mkdir(parents=True,exist_ok=True)
        temp=dest.with_suffix('.partial')
        with urllib.request.urlopen(url,timeout=60) as response,temp.open('wb') as output:
            for block in iter(lambda:response.read(1024*1024),b''):output.write(block)
        check_entry(temp,archive);temp.replace(dest)
        return verify_package(path,dest)
    catalog=json.loads((ROOT/'catalog.json').read_text());seen=set();count=0
    for asset in catalog['assets']:
        if asset['id'] in seen:raise ValueError('duplicate asset id')
        seen.add(asset['id']);latest=verify_manifest(manifest_path(asset))
        if (latest['id'],latest['version'])!=(asset['id'],asset['latest']):raise ValueError('catalog version mismatch')
        for path in version_manifests(asset):
            m=verify_manifest(path)
            if path.stem!=m['version'] or m['id']!=asset['id']:raise ValueError(path)
            count+=1
    print(f'Catalog verified: {len(seen)} assets, {count} versions')

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,zipfile.BadZipFile) as e:
        print(f'Validation failed: {e}',file=sys.stderr);sys.exit(1)
