"""Remove non-exported source scene copies from v2 wolf bundles; retain prefab data."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import UnityPy
from prepare_monster_recovery import pointers

POLICY='wolf-export-closure-v3'
ROOT=Path(__file__).resolve().parents[1]

def rebuild(source,output, *, policy=POLICY):
    env=UnityPy.load(str(source));objects={o.path_id:o for o in env.objects}
    ab_obj=next(o for o in env.objects if o.type.name=='AssetBundle');ab=ab_obj.read_typetree()
    original={i:o.get_raw_data() for i,o in objects.items()}
    def closure(pid):
        found=set();todo=[pid]
        while todo:
            i=todo.pop()
            if i in found:continue
            if i not in objects:raise ValueError('Missing internal dependency')
            found.add(i)
            for p in pointers(objects[i].read_typetree()):
                if p['m_FileID']:raise ValueError('Unexpected external dependency')
                if p['m_PathID']:todo.append(p['m_PathID'])
        return found
    keep={ab_obj.path_id};preload=[];exports=[]
    for name,entry in ab['m_Container']:
        own=closure(entry['asset']['m_PathID']);keep|=own
        updated=copy.deepcopy(entry);updated.update(preloadIndex=len(preload),preloadSize=len(own))
        preload.extend(dict(m_FileID=0,m_PathID=i) for i in sorted(own));exports.append((name,updated))
    main=ab['m_MainAsset']['asset']
    if main['m_PathID']:raise ValueError('Unexpected main asset')
    removed=[dict(path_id=i,type=o.type.name,name=o.read_typetree().get('m_Name')) for i,o in objects.items() if i not in keep]
    ab.update(m_PreloadTable=preload,m_Container=exports);ab_obj.save_typetree(ab)
    sf=ab_obj.assets_file;sf.objects={i:o for i,o in objects.items() if i in keep}
    unique='CustomAssetBundle-'+hashlib.md5((policy+':'+Path(output).stem).encode()).hexdigest()
    sf.name=unique;env.file.files={unique:sf};payload=env.file.save()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(payload)
    check=UnityPy.load(str(output));actual={o.path_id:o for o in check.objects}
    if set(actual)!=keep:raise ValueError('Object set roundtrip mismatch')
    for i in keep-{ab_obj.path_id}:
        if actual[i].get_raw_data()!=original[i]:raise ValueError('Retained prefab object modified')
    if set(check.container)!=set(env.container):raise ValueError('Export names changed')
    return dict(policy=POLICY,sha256=hashlib.sha256(payload).hexdigest(),internal_file=unique,removed_objects=removed,retained_objects=len(keep),retained_object_bytes_unchanged=True,runtime_verified=False)

def build(source_dir,output):
    reports=json.loads((source_dir/'validation.json').read_text());result=[]
    for row in reports:
        info=rebuild(source_dir/row['bundle'],output/row['bundle']);result.append({**row,**info})
    (output/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'resources/reconstructed/wolf-strip-v2-candidate');p.add_argument('--output',type=Path,default=ROOT/'resources/reconstructed/wolf-closure-v3-candidate');args=p.parse_args();build(args.source,args.output)
