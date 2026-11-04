"""Attach final material provenance to the completed uniform backup build."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WS=ROOT.parent

def finalize():
    index=json.loads((ROOT/'docs/resource-audit/new-backup/新备份资源索引.json').read_text())
    names={}
    for asset in index['assets']:
        if asset['type']=='Texture2D':names.setdefault(index['sources'][asset['source']]['path'],set()).add(asset['name'])
    path=ROOT/'resources/reconstructed/backup-recovery/validation.json'
    rows=json.loads(path.read_text())
    for row in rows:
        evidence={}
        for name,texture in row.get('textures',{}).items():
            source=texture['source'].removeprefix('resources/unpacked/')
            inferred=name not in names.get(source,set())
            evidence[name]={'source':texture['source'],'exact_name':not inferred,'inferred':inferred,'reason':'same-family texture correspondence' if inferred else 'exact-name backup texture'}
        row['texture_provenance']=evidence
        row['inferred']=row.get('source_model')!=row['model'] or bool(row.get('skeleton_adaptations')) or any(e['inferred'] for e in evidence.values())
        row['reason']='Recovered backup model and texture artwork; inferred same-family mapping where texture_provenance or source_model differs.' if row['inferred'] else 'Recovered exact-name backup model and textures; native compatibility serialization.'
        row['builder_revision']='backup-type-motion-closure-v2'
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    return rows

if __name__=='__main__':
    print('Finalized',len(finalize()),'rows')
