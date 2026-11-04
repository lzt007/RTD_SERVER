"""Match wolf source-object activation flags to native Unity 3.5 assets.

Changes no mesh, material, texture, animation, hierarchy or gameplay data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import UnityPy

ROOT=Path(__file__).resolve().parents[1]
POLICY='wolf-native-activation-v4'

def build(source_dir,output):
    rows=json.loads((source_dir/'validation.json').read_text());output.mkdir(parents=True,exist_ok=True);result=[]
    for row in rows:
        env=UnityPy.load(str(source_dir/row['bundle']));before={o.path_id:(o.type.name,o.get_raw_data(),o.read_typetree() if o.type.name=='GameObject' else None) for o in env.objects};changed=[]
        for obj in env.objects:
            if obj.type.name!='GameObject':continue
            t=obj.read_typetree()
            if t['m_IsActive']!=0:
                changed.append(obj.path_id);t['m_IsActive']=0;obj.save_typetree(t)
        sf=next(iter(env.objects)).assets_file;unique='CustomAssetBundle-'+hashlib.md5((POLICY+':'+row['model']).encode()).hexdigest();sf.name=unique;env.file.files={unique:sf}
        path=output/row['bundle'];path.write_bytes(env.file.save());check=UnityPy.load(str(path));after={o.path_id:o for o in check.objects}
        if set(after)!=set(before):raise ValueError('Object set changed')
        for i,(typ,raw,oldtree) in before.items():
            if typ=='GameObject':
                expected={**oldtree,'m_IsActive':0}
                if after[i].read_typetree()!=expected:raise ValueError('GameObject fields other than activation changed')
            elif after[i].get_raw_data()!=raw:raise ValueError('Non-GameObject bytes changed')
        if set(check.container)!=set(env.container):raise ValueError('Exports changed')
        result.append({**row,'policy':POLICY,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'internal_file':unique,'retained_object_bytes_unchanged':False,'non_gameobject_bytes_unchanged':True,'only_gameobject_activation_changed':True,'activation_flag':0,'activation_changed_gameobject_ids':changed,'runtime_verified':False})
    (output/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'resources/reconstructed/wolf-closure-v3-candidate');p.add_argument('--output',type=Path,default=ROOT/'resources/reconstructed/wolf-native-activation-v4-candidate');args=p.parse_args();build(args.source,args.output)
