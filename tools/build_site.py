#!/usr/bin/env python3
"""Build an isolated Pages artifact from catalog entries and verified release ZIPs."""
import html
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from verify import ROOT, safe, verify_manifest, verify_package

def main():
    output=ROOT/'_site'
    if output.is_symlink():raise ValueError('site output must not be a symlink')
    if output.exists():shutil.rmtree(output)
    shutil.copytree(ROOT/'site',output)
    catalog=json.loads((ROOT/'catalog.json').read_text())
    gallery={'assets':[]};cards=[]
    for asset in catalog['assets']:
        item={**asset,'versions':[]}
        manifests=sorted((ROOT/'assets'/asset['id']/'versions').glob('*.json'),
                         key=lambda p:tuple(map(int,p.stem.split('.'))),reverse=True)
        for path in manifests:
            m=verify_manifest(path)
            archive=ROOT/'.downloads'/m['id']/m['version']/safe(m['release']['archive']['name'])
            if not archive.exists():
                subprocess.run([sys.executable,str(ROOT/'tools/verify.py'),'--download',m['id'],m['version']],check=True)
            verify_package(path,archive)
            folder=Path('models')/m['id']/m['version'];dest=output/folder;dest.mkdir(parents=True,exist_ok=True)
            models=[n for n in m['files'] if n.endswith('.glb')]
            if len(models)!=1:raise ValueError('expected one GLB per model version')
            with zipfile.ZipFile(archive) as z:
                (dest/'model.glb').write_bytes(z.read(models[0]))
            previews=[]
            for preview in m['previews']:
                source=ROOT/safe(preview['path']);name=preview['view']+source.suffix
                shutil.copy2(source,dest/name)
                previews.append({'view':preview['view'],'url':(folder/name).as_posix()})
            item['versions'].append({'version':m['version'],'modelUrl':(folder/'model.glb').as_posix(),
                'dimensions':m.get('measuredBoundsMm',m['nominalDimensionsMm']),
                'changes':m['changes'],'previews':previews,
                'releaseUrl':f"https://github.com/lincolnaleixo/retro-cartridge-models/releases/tag/{m['release']['tag']}"})
        gallery['assets'].append(item)
        current=next(v for v in item['versions'] if v['version']==item['latest']);esc=html.escape
        cards.append(f'''<article class="card" data-asset="{esc(item['id'])}">
<a class="card-image" href="#{esc(item['id'])}" data-explore="{esc(item['id'])}" aria-label="Explore {esc(item['displayTitle'])}"><img src="{esc(current['previews'][0]['url'])}" alt="{esc(item['displayTitle'])}" width="600" height="400"></a>
<div class="card-copy"><div class="meta"><span>{esc(item['kind'])}</span><span>v{esc(item['latest'])}</span></div><h3>{esc(item['displayTitle'])}</h3><p>{esc(item['description'])}</p><div class="card-links"><a href="#{esc(item['id'])}" data-explore="{esc(item['id'])}">Explore in 3D ↗</a><a href="{esc(current['releaseUrl'])}">Blender + GLB ↓</a></div></div></article>''')
    template=(output/'index.html').read_text()
    (output/'index.html').write_text(template.replace('<!-- ASSET_CARDS -->','\n'.join(cards)))
    (output/'gallery.json').write_text(json.dumps(gallery,indent=2,ensure_ascii=False)+'\n')
    (output/'.nojekyll').touch()
    for name in ['LICENSE','NOTICE.md','CREDITS.md']:shutil.copy2(ROOT/name,output/name)
    print(f'Pages artifact: {len(gallery["assets"])} models in {output}')

if __name__=='__main__':main()
