#!/usr/bin/env python3
"""Build an isolated Pages artifact from catalog entries and verified release ZIPs."""
import html
import json
import math
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from verify import ROOT, manifest_path, preview_path, safe, verify_manifest, verify_package, version_manifests

def viewer_metadata(manifest, package, model):
    """Read articulated poses from the already verified release's inspection."""
    animation=manifest.get('validation',{}).get('animation')
    if animation is None:return {}
    report_name='glb-inspection.json'
    if report_name not in manifest['files']:
        raise ValueError(f"{manifest['id']}: animated release has no verified inspection report")
    report=json.loads(package.read(report_name))
    if (report.get('status')!='passed' or report.get('file')!=model
            or report.get('sha256')!=manifest['files'][model]['sha256']
            or report.get('animation')!=animation):
        raise ValueError(f"{manifest['id']}: animation inspection does not match the released GLB")
    result={'animation':animation}
    for pose in ('closed','open'):
        bounds=report.get('worldVertexBounds',{}).get(pose,{})
        for key in ('min','max','dimensions'):
            values=bounds.get(key)
            if (not isinstance(values,list) or len(values)!=3
                    or any(type(n) not in (int,float) or not math.isfinite(n) for n in values)):
                raise ValueError(f"{manifest['id']}: invalid {pose} world bounds")
        for low,high,size in zip(bounds['min'],bounds['max'],bounds['dimensions']):
            if size<=0 or not math.isclose(high-low,size,rel_tol=1e-6,abs_tol=1e-9):
                raise ValueError(f"{manifest['id']}: inconsistent {pose} world bounds")
        result[f'{pose}Bounds']=bounds
    return result

def main():
    output=ROOT/'_site'
    if output.is_symlink():raise ValueError('site output must not be a symlink')
    if output.exists():shutil.rmtree(output)
    shutil.copytree(ROOT/'site',output)
    catalog=json.loads((ROOT/'catalog.json').read_text())
    gallery={'assets':[]};cards=[]
    for asset in catalog['assets']:
        directory=manifest_path(asset).parent.parent.relative_to(ROOT)
        history_url=f'https://github.com/lincolnaleixo/retro-cartridge-models/blob/main/{directory.as_posix()}/CHANGELOG.md'
        item={**asset,'historyUrl':history_url,'versions':[]}
        manifests=version_manifests(asset)
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
                poses=viewer_metadata(m,z,models[0])
            previews=[]
            for preview in m['previews']:
                source=preview_path(m,preview);name=preview['view']+source.suffix
                shutil.copy2(source,dest/name)
                previews.append({'view':preview['view'],'url':(folder/name).as_posix()})
            item['versions'].append({'version':m['version'],'modelUrl':(folder/'model.glb').as_posix(),
                'dimensions':m.get('measuredBoundsMm',m['nominalDimensionsMm']),
                **poses,
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
