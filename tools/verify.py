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

def check_entry(path,entry):
    if path.stat().st_size!=entry['bytes'] or sha(path)!=entry['sha256']:
        raise ValueError(f'checksum/size mismatch: {path}')

def verify_manifest(path):
    m=json.loads(path.read_text())
    if m['schemaVersion']!=1 or not SEMVER.fullmatch(m['version']):raise ValueError(path)
    if m['license']!='CC-BY-NC-ND-4.0':raise ValueError('unexpected license')
    if not m['creator'] or not m['changes']:raise ValueError('missing attribution or changes')
    if m['release']['tag']!=f"{m['id']}-v{m['version']}":raise ValueError('tag mismatch')
    for entry in m['previews']:check_entry(ROOT/safe(entry['path']),entry)
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
        path=ROOT/'assets'/asset/'versions'/(version+'.json');m=verify_manifest(path)
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
        seen.add(asset['id']);latest=verify_manifest(ROOT/safe(asset['manifest']))
        if (latest['id'],latest['version'])!=(asset['id'],asset['latest']):raise ValueError('catalog version mismatch')
        for path in (ROOT/'assets'/asset['id']/'versions').glob('*.json'):
            m=verify_manifest(path)
            if path.stem!=m['version'] or m['id']!=asset['id']:raise ValueError(path)
            count+=1
    print(f'Catalog verified: {len(seen)} assets, {count} versions')

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,zipfile.BadZipFile) as e:
        print(f'Validation failed: {e}',file=sys.stderr);sys.exit(1)
