"""Build an explicitly inferred marker for a missing unit-enemy book bundle.

Requires the offline UnityPy tool. Original bundles and master data stay intact.
This is a Fenris marker, not a recovery of the original book artwork.
"""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE_SHA256='8ee34859e01f71985f023f255933c838ff30da80848cf0efd0cdc9bda6b5dac8'
PREFAB='ast_ms00_book_el_05'


def build_book(source,output,book_color=5):
    import UnityPy
    if type(book_color) is not int or book_color not in range(1,7):
        raise ValueError('Original book colors are 1 through 6')
    prefab_name=f'ast_ms00_book_el_0{book_color}'
    source=Path(source);output=Path(output)
    if output.exists():raise FileExistsError(output)
    source_bytes=source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Source differs from audited original Fenris bundle')
    env=UnityPy.load(source_bytes)
    matches=0
    for obj in env.objects:
        if obj.type.name!='AssetBundle':continue
        bundle=obj.read()
        containers=[]
        for name,info in bundle.m_Container:
            if info.asset.type.name=='GameObject' and info.asset.path_id==609:
                prefab=info.asset.read()
                if prefab.m_Name!='g01_kn_grt_fire_01':raise ValueError('Unexpected source prefab')
                prefab.m_Name=prefab_name;prefab.save()
                containers.append((prefab_name,info));matches+=1
        # Only publish the audited marker entry; retain its serialized dependencies.
        bundle.m_Container=containers
        bundle.m_Name='local-shingetsu-book-marker'
        bundle.save()
    if matches!=1:raise ValueError('Expected one audited enemy-facing Fenris prefab')
    # Match Unity 3.5's native asset activation encoding. A serialized 1 here
    # failed the 20710 entry A/B check; disabling only the clone did not help.
    activation_changes=[]
    for obj in env.objects:
        if obj.type.name!='GameObject':continue
        tree=obj.read_typetree()
        if tree['m_IsActive']!=0:
            activation_changes.append(obj.path_id)
            tree['m_IsActive']=0
            obj.save_typetree(tree)
    # Unity cannot load two archives with the same internal serialized filename.
    # The real character bundle must remain independently loadable for battle.
    original_names=list(env.file.files)
    for name in original_names:
        asset=env.file.files.pop(name)
        salt=f'inferred-events-book-{book_color}-native-activation-v2:'
        unique='CustomAssetBundle-'+hashlib.md5((salt+name).encode()).hexdigest()
        asset.name=unique
        env.file.files[unique]=asset
    payload=env.file.save()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as file:file.write(payload)
    return dict(policy='inferred-book-native-activation-v2',source_bundle=source.name,
                source_sha256=SOURCE_SHA256,source_prefab_path_id=609,
                generated_bundle=output.name,generated_sha256=hashlib.sha256(payload).hexdigest(),
                prefab=prefab_name,original_internal_files=original_names,
                generated_internal_files=list(env.file.files),
                activation_flag=0,activation_changed_gameobject_ids=activation_changes,
                runtime_scope='20710 entry only; battle transition and completion not validated',
                reason='Original book bundle absent; temporary Fenris map marker only. Battle character remains original.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.report.exists():raise FileExistsError(args.report)
    report=build_book(args.source,args.output)
    with args.report.open('x',encoding='utf-8') as file:
        file.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
