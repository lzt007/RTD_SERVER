"""Prepare a separate missing-resource overlay without touching original bundles."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.reconstruct_shingetsu_book import build_book


def prepare(root,output):
    root=Path(root);output=Path(output)
    if output.exists():raise FileExistsError(output)
    assets=json.loads((root/'config/event-reconstruction-assets.json').read_text())
    output.mkdir(parents=True)
    reports=[]
    for name,source in assets['bundle_sources'].items():
        if (root/'resources/bundles'/name).is_file():continue
        data=(root/source['source']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=source['sha256']:raise ValueError('Original source hash differs')
        with (output/name).open('xb') as file:file.write(data)
        reports.append(dict(filename=name,policy='recovered-original-cache-copy',sha256=source['sha256']))
    for color in range(1,7):
        name=f'ms00_book_el_0{color}.unity3d'
        if (root/'resources/bundles'/name).is_file():continue
        reports.append(build_book(root/'resources/bundles/151-160.unity3d',output/name,book_color=color))
    (output.parent/'resource-provenance.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    return reports


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    reports=prepare(Path(__file__).resolve().parents[1],args.output)
    print('Prepared bundles:',len(reports))
