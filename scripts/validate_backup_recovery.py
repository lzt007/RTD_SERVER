"""Independent structural gate for every generated backup compatibility bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import UnityPy
from prepare_monster_recovery import pointers


def validate(path, expected_hash=None):
    payload=path.read_bytes()
    if expected_hash and hashlib.sha256(payload).hexdigest()!=expected_hash:
        raise ValueError('Manifest hash mismatch: '+str(path))
    env=UnityPy.load(payload)
    objects={o.path_id:o for o in env.objects}
    if len(objects)!=len(env.objects):raise ValueError('Multiple serialized files / duplicate IDs')
    bundle=next(o for o in env.objects if o.type.name=='AssetBundle')
    sf=bundle.assets_file
    assert sf.header.version==9, path
    trees={i:o.read_typetree() for i,o in objects.items()}
    def closure(root):
        found=set();todo=[root]
        while todo:
            pid=todo.pop()
            if pid in found:continue
            assert pid in objects,(path,pid)
            found.add(pid)
            for p in pointers(trees[pid]):
                assert p['m_FileID']==0,(path,p)
                if p['m_PathID']:todo.append(p['m_PathID'])
        return found
    ab=trees[bundle.path_id];union={bundle.path_id}
    for name,entry in ab['m_Container']:
        own=closure(entry['asset']['m_PathID']);union.update(own)
        preload=ab['m_PreloadTable'][entry['preloadIndex']:entry['preloadIndex']+entry['preloadSize']]
        assert {p['m_PathID'] for p in preload}==own,(path,name)
    assert union==set(objects),(path,'unowned objects')
    for pid,obj in objects.items():
        if obj.type.name=='GameObject':assert trees[pid]['m_IsActive']==0,(path,pid)
        if obj.type.name=='Texture2D':obj.read().image.load()
    return dict(bundle=path.name,objects=len(objects),internal_file=sf.name,sha256=hashlib.sha256(payload).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    args=parser.parse_args();rows=[];identities=set()
    for path in sorted(args.directory.glob('*.unity3d')):
        row=validate(path)
        assert row['internal_file'] not in identities,'Duplicate CAB identity'
        identities.add(row['internal_file']);rows.append(row)
    assert rows,'No bundles validated'
    print(json.dumps(dict(validated=len(rows),bundles=rows),ensure_ascii=False,indent=2))
