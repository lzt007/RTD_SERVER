"""Offline Unity 5 -> Unity 3.5 visual recovery. Requires UnityPy and Pillow.
Never edits original files. Outputs are inferred compatibility assets, not original art.
"""
import copy
import hashlib
import json
import struct
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WS=ROOT.parent
BACKUP=WS/'resources/unpacked/assets/assets/quest'
WOLF_SOURCE=BACKUP/'330_ms01_wolf_lv1_f_01.unity3d'
TEMPLATE=WS/'RTD_CLIENT/resources/UnityCache/Shared/9071c5348d32c63e68d2251b1a5bcf45ecc9bd3e/CustomAssetBundle-af49d4e7e10ee1241b268c1e3e5562e7'
APK=WS/'RTD_CLIENT/inputs/original/game.apk'

def merge_schema(value, template):
    if isinstance(template,bytes):return bytes(value)
    if isinstance(template,dict):
        return {k:merge_schema(value.get(k,v),v) for k,v in template.items()}
    if isinstance(template,tuple):
        return tuple(merge_schema(v,t) for v,t in zip(value,template))
    if isinstance(template,list) and template:
        return [merge_schema(v,template[0]) for v in value]
    return copy.deepcopy(value)

def pointers(tree):
    if isinstance(tree,dict):
        if 'm_PathID' in tree and 'm_FileID' in tree:yield tree
        else:
            for v in tree.values():yield from pointers(v)
    elif isinstance(tree,(list,tuple)):
        for v in tree:yield from pointers(v)

def motion_paths(family):
    import UnityPy
    catalog=json.loads((ROOT/'docs/resource-audit/loading-chain/catalog.json').read_text())
    result=set()
    with zipfile.ZipFile(APK) as z:
        for obj in catalog['objects'].values():
            if obj['type']!='AnimationClip' or obj['name'] not in {f'ms01_{family}_wait_01',f'ms01_{family}_atk_01'}:continue
            source=catalog['sources'][catalog['files'][obj['file']]['source']]
            prefix=str(APK.relative_to(WS))+':'
            origin=next((o for o in source['origins']
                         if o['category']=='apk_data' and o['path'].startswith(prefix)),None)
            if origin is None:raise ValueError('Original APK motion provenance unavailable')
            entry=origin['path'][len(prefix):]
            t=next(o for o in UnityPy.load(z.read(entry)).objects if o.path_id==obj['path_id']).read_typetree()
            for k in ('m_RotationCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves'):
                result.update(c['path'] for c in t[k])
    if not result:raise ValueError('Original motions not found')
    return result

def hierarchy_paths(trees):
    transforms={i:t for i,(typ,t) in trees.items() if typ=='Transform'}
    def walk(i,prefix):
        t=transforms[i];yield prefix
        for ch in t['m_Children']:
            child=transforms[ch['m_PathID']]
            name=trees[child['m_GameObject']['m_PathID']][1]['m_Name']
            yield from walk(ch['m_PathID'],prefix+'/'+name if prefix else name)
    # Runtime adds the wait/attack clips to each child animation, not the prefab root.
    return [set(walk(i,'')) for i,t in transforms.items()
            if trees[t['m_GameObject']['m_PathID']][1]['m_Name']=='move']

def convert_model(source,output,model,textures):
    import UnityPy
    from UnityPy.helpers.MeshHelper import MeshHandler
    from PIL import Image
    env=UnityPy.load(str(source));target=UnityPy.load(str(TEMPLATE)).file
    templates={}
    for obj in target.objects.values():templates.setdefault(obj.type.name,obj)
    original_trees={k:o.read_typetree() for k,o in templates.items()}
    objects={};trees={};images={};vertices=0
    src={o.path_id:o for o in env.objects}
    vertices=sum(o.read_typetree()['m_VertexData']['m_VertexCount'] for o in env.objects if o.type.name=='Mesh' and o.assets_file.header.version<=9)
    shader_id=next(i for i,o in src.items() if o.type.name=='Shader')
    root_id=next(i for i,o in src.items() if o.type.name=='GameObject' and o.read_typetree()['m_Name'].startswith('ast_'))
    def add(typ,tree,pid):
        obj=copy.copy(templates[typ]);obj.assets_file=target;obj.path_id=pid
        obj.save_typetree(merge_schema(tree,original_trees[typ]));objects[pid]=obj;trees[pid]=(typ,tree)
    texture_obj=next(o for o in env.objects if o.type.name=='Texture2D')
    for pid,obj in src.items():
        typ=obj.type.name;t=obj.read_typetree()
        if typ=='AssetBundle':continue
        if typ=='Shader':t=copy.deepcopy(original_trees['Shader'])
        elif typ=='Material':
            # Original Android shader and its matching saved-property defaults.
            t=copy.deepcopy(original_trees['Material']);t['m_Name']=model
            t['m_Shader']={'m_FileID':0,'m_PathID':shader_id}
            for key,v in t['m_SavedProperties']['m_TexEnvs']:
                v['m_Texture']={'m_FileID':0,'m_PathID':texture_obj.path_id if key['name']=='_MainTex' else 0}
        elif typ=='Texture2D':continue
        elif typ=='GameObject':
            if obj.assets_file.header.version>9:
                # Unity 5 scene activation flags are not the native 3.5 asset
                # convention. Match the audited old prefab, including children.
                t['m_IsActive']=original_trees['GameObject']['m_IsActive']
            if pid==root_id:t['m_Name']='ast_'+model
        elif typ=='SkinnedMeshRenderer':
            t['m_LightmapIndex']=255;t['m_LightProbeAnchor']=t.get('m_ProbeAnchor',{'m_FileID':0,'m_PathID':0})
            t['m_UseLightProbes']=False
        elif typ=='Mesh' and obj.assets_file.header.version>9:
            if t['m_MeshCompression']:raise ValueError('Compressed mesh requires explicit conversion')
            mesh=MeshHandler(obj.read());mesh.process()
            count=len(mesh.m_Vertices);vertices+=count
            vd=copy.deepcopy(original_trees['Mesh']['m_VertexData'])
            vd['m_VertexCount']=count;vd['m_CurrentChannels']=9
            vd['m_DataSize']=list(b''.join(struct.pack('<5f',*p[:3],*uv[:2]) for p,uv in zip(mesh.m_Vertices,mesh.m_UV0)))
            vd['m_Streams[0]'].update(channelMask=9,offset=0,stride=20,align=16)
            for i in range(1,4):vd[f'm_Streams[{i}]'].update(channelMask=0,offset=0,stride=0,align=16)
            t['m_VertexData']=vd
            for sub in t['m_SubMeshes']:
                if sub['topology']!=0:raise ValueError('Only triangle lists supported')
                sub['isTriStrip']=0;sub['triangleCount']=sub['indexCount']//3
        add(typ,t,pid)
    exports=[('ast_'+model,root_id)]
    for index,(name,path) in enumerate(textures.items()):
        tex=next(o for o in UnityPy.load(str(path)).objects if o.type.name=='Texture2D')
        data=tex.read()
        if tex.assets_file.header.version<=9 and data.m_TextureFormat==2:
            px=struct.unpack('<'+str(data.m_Width*data.m_Height)+'H',data.image_data[:data.m_Width*data.m_Height*2])
            image=Image.frombytes('RGBA',(data.m_Width,data.m_Height),bytes(((v>>sh)&15)*17 for v in px for sh in (12,8,4,0))).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        else:image=data.image.convert('RGBA')
        if name.endswith('_silver') and tex.assets_file.header.version<=9:
            # Inferred metallic counterpart: original geometry/UV, grayscale gold artwork.
            alpha=image.getchannel('A');image=image.convert('L').convert('RGBA');image.putalpha(alpha)
        images[name]=image
        t=copy.deepcopy(original_trees['Texture2D'])
        t.update(m_Name=name,m_Width=image.width,m_Height=image.height,m_TextureFormat=4,
                 m_CompleteImageSize=image.width*image.height*4,m_MipMap=False,m_IsReadable=True,
                 m_ImageCount=1,m_TextureDimension=2)
        t['image data']=image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
        pid=texture_obj.path_id if index==0 else 10000+index
        add('Texture2D',t,pid);exports.append((name,pid))
    ab=copy.deepcopy(original_trees['AssetBundle'])
    ab['m_Name']='compatible-'+model
    ab['m_PreloadTable']=[{'m_FileID':0,'m_PathID':i} for i in objects]
    ab['m_Container']=[(name,dict(preloadIndex=0,preloadSize=len(objects),asset=dict(m_FileID=0,m_PathID=pid))) for name,pid in exports]
    ab['m_MainAsset']=dict(preloadIndex=0,preloadSize=0,asset=dict(m_FileID=0,m_PathID=0))
    add('AssetBundle',ab,1)
    target.objects=objects
    target.externals=[]
    unique='CustomAssetBundle-'+hashlib.md5(('wolf-slime-recovery-v1:'+model).encode()).hexdigest()
    target.name=unique
    wrapper=UnityPy.load(str(ROOT/'resources/bundles/ms01_sla_lv1_gold.unity3d')).file
    wrapper.files={unique:target}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(wrapper.save())
    check=UnityPy.load(str(output));sf=next(iter(check.objects)).assets_file
    missing=[]
    for obj in check.objects:
        for p in pointers(obj.read_typetree()):
            if p['m_PathID'] and (p['m_FileID'] or p['m_PathID'] not in sf.objects):missing.append(p)
    mesh_roundtrip=True
    for pid,(typ,tree) in trees.items():
        if typ!='Mesh':continue
        actual=sf.objects[pid].read_typetree()
        expected_mesh=merge_schema(tree,original_trees['Mesh'])
        for field in ('m_VertexData','m_SubMeshes','m_IndexBuffer','m_Skin','m_BindPose'):
            if actual[field]!=expected_mesh[field]:mesh_roundtrip=False
        count=actual['m_VertexData']['m_VertexCount']
        if len(actual['m_Skin'])!=count:raise ValueError('Skin/vertex count mismatch')
        for weights in actual['m_Skin']:
            if abs(sum(weights[f'weight[{i}]'] for i in range(4))-1)>1e-4:raise ValueError('Invalid skin weights')
            for i in range(4):
                if weights[f'weight[{i}]'] and not 0<=weights[f'boneIndex[{i}]']<len(actual['m_BindPose']):raise ValueError('Invalid bone index')
    for obj in check.objects:
        if obj.type.name!='SkinnedMeshRenderer':continue
        renderer=obj.read_typetree();mesh=sf.objects[renderer['m_Mesh']['m_PathID']].read_typetree()
        if len(renderer['m_Bones'])!=len(mesh['m_BindPose']):raise ValueError('Renderer bone/bindpose mismatch')
    family='wolf' if 'wolf' in model else ('slawing' if 'slawing' in model else 'sla')
    expected=motion_paths(family)
    skeletons=hierarchy_paths(trees)
    missing_paths=sorted(set().union(*(expected-paths for paths in skeletons))) if skeletons else ['no move hierarchy']
    roundtrip=all(check.container[name].read().image.convert('RGBA').tobytes()==im.tobytes() for name,im in images.items())
    report=dict(model=model,source=str(Path(source).relative_to(WS)),source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                bundle=output.name,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),internal_file=unique,
                vertices=vertices,mesh_roundtrip=mesh_roundtrip,missing_pointers=missing,missing_motion_paths=missing_paths,texture_roundtrip=roundtrip,
                textures={name:dict(source=str(Path(p).relative_to(WS)),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for name,p in textures.items()})
    if missing or missing_paths or not roundtrip or not mesh_roundtrip:raise ValueError(report)
    return report

def extract_originals(directory):
    """Flatten actual APK Resources prefab closure; resolve every external PPtr."""
    import UnityPy
    from functools import lru_cache
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((ROOT/'docs/resource-audit/loading-chain/catalog.json').read_text())
    files=catalog['files'];sources=catalog['sources'];objects=catalog['objects']
    by_name={}
    for fid,f in files.items():
        if any('.apk:' in x['path'] and x['category']=='apk_data' for x in sources[f['source']]['origins']):
            names={x['path'].split('/')[-1] for x in sources[f['source']]['origins'] if '.apk:' in x['path'] and x['category']=='apk_data'}
            for name in names:by_name.setdefault(name,[]).append(fid)
    def resolve(fid,p):
        if not p['m_PathID']:return None
        if p['m_FileID']:
            name=files[fid]['externals'][p['m_FileID']-1].split('/')[-1]
            matches=by_name[name]
            if len(matches)!=1:raise ValueError('Ambiguous APK external '+name)
            fid=matches[0]
        return files[fid]['objects'][str(p['m_PathID'])]
    with zipfile.ZipFile(APK) as z:
        @lru_cache(None)
        def read_file(fid):
            source=sources[files[fid]['source']]
            origin=next(x for x in source['origins'] if '.apk:' in x['path'] and x['category']=='apk_data')
            return UnityPy.load(z.read(origin['path'].split(':',1)[1])).file
        proof={}
        def record(fid):
            source=sources[files[fid]['source']]
            origin=next(x for x in source['origins'] if '.apk:' in x['path'] and x['category']=='apk_data')
            member=origin['path'].split(':',1)[1]
            proof[member]=hashlib.sha256(z.read(member)).hexdigest()
        def reader(oid):
            obj=objects[oid];record(obj['file']);return read_file(obj['file']).objects[obj['path_id']]
        binding=next(b for b in catalog['bindings'] if b['path']=='prefab/enemies/ms01_sla_lv1')
        root=resolve(binding['file'],binding['pointer']);queue=[root];trees={}
        while queue:
            oid=queue.pop()
            if oid in trees:continue
            t=reader(oid).read_typetree();trees[oid]=t
            queue += [resolve(objects[oid]['file'],p) for p in pointers(t) if p['m_PathID']]
        ids={oid:i+100 for i,oid in enumerate(trees)}
        target=UnityPy.load(str(TEMPLATE)).file;templates={o.type.name:o for o in target.objects.values()};out={}
        for oid,t in trees.items():
            t=copy.deepcopy(t)
            for p in pointers(t):
                key=resolve(objects[oid]['file'],p)
                p.update(m_FileID=0,m_PathID=ids[key] if key else 0)
            if oid==root:t['m_Name']='ast_ms01_sla_lv1'
            obj=copy.copy(templates[objects[oid]['type']]);obj.assets_file=target;obj.path_id=ids[oid]
            obj.save_typetree(t);out[obj.path_id]=obj
        target.objects=out;target.externals=[]
        prefab=directory/'original-sla-lv1.assets';prefab.write_bytes(target.save())
        textures={}
        for attr in ('fire','water','holy','dark'):
            name='ms01_sla_lv1_'+attr
            binding=next(b for b in catalog['bindings'] if b['path']=='prefab/enemies/textures/'+name)
            oid=resolve(binding['file'],binding['pointer'])
            path=directory/(name+'.assets');path.write_bytes(read_file(objects[oid]['file']).save());textures[attr]=path;record(objects[oid]['file'])
    (directory/'original-apk-dependencies.json').write_text(json.dumps(proof,indent=2)+'\n')
    return prefab,textures

def build(active_models,output):
    """Build only model families referenced by the caller's audited playable quests."""
    output=Path(output);source_dir=output/'sources'
    normal,normal_textures=extract_originals(source_dir)
    reports=[]
    for model,requested in sorted(active_models.items()):
        if model in {'ms01_sla_lv1','ms01_sla_lv1_gold','ms01_sla_lv4_gold'}:continue
        if 'wolf' in model:
            # Both recovered designs bind to the original wolf motions. Level/design
            # correspondence is inferred, not recovered original level-specific art.
            design='330' if model.endswith(('lv1','lv2')) else '550'
            paths={a:BACKUP/(f'330_ms01_wolf_lv1_{code}_01.unity3d' if design=='330' else f'550_ms01_wolf_{code}_01.unity3d') for a,code in [('fire','f'),('water','w'),('holy','h'),('dark','d')]}
            attrs=[a for a in paths if model.endswith('_'+a)]
            if attrs:source=paths[attrs[0]];textures={model:source}
            else:source=paths['fire'];textures={model+'_'+a:p for a,p in paths.items() if model+'_'+a in requested}
            reason='Recovered wolf '+design+' design; legacy level/special-design correspondence inferred; no gameplay scaling.'
        elif model.endswith(('_gold','_silver')):
            source=ROOT/f'resources/bundles/ms01_sla_lv{4 if "lv4" in model else 1}_gold.unity3d'
            textures={model:source}
            reason='Original gold slime geometry; '+('inferred grayscale silver palette, not recovered original silver artwork.' if model.endswith('_silver') else 'inferred reuse for missing level variant.')
        elif model.startswith('ms01_sla_'):
            source=normal
            if '_sh_' in model:textures={model:normal_textures[model.rsplit('_',1)[1]]}
            else:textures={model+'_'+a:p for a,p in normal_textures.items() if model+'_'+a in requested}
            reason='Original APK normal Lv1 slime geometry and matching original attribute texture reused for missing variant; level appearance inferred.'
        else:continue
        canonical=ROOT/'resources/bundles'/(model+'.unity3d')
        if canonical.exists():raise ValueError('Refusing to shadow an existing resource '+model)
        report=convert_model(source,output/'bundles'/(model+'.unity3d'),model,textures)
        report['inferred']=True;report['reason']=reason;report['requested_textures']=requested
        reports.append(report)
        print('Built',model,flush=True)
    import sys
    sys.path.insert(0,str(ROOT))
    from rtd.masters.catalog import load_catalog
    raw,_=load_catalog()
    manifest=dict(original_apk_dependencies=json.loads((source_dir/'original-apk-dependencies.json').read_text()),source_enemy_master_hash=raw[20]['hash'],policy='wolf-slime-compatibility-v1',apk_sha256=hashlib.sha256(APK.read_bytes()).hexdigest(),
                  template_sha256=hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
                  scope='Currently playable story and repaired events; input active model list required.',
                  unchanged_existing=['ms01_sla_lv1','ms01_sla_lv1_gold','ms01_sla_lv4_gold'],bundles=reports)
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active-models',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'resources/reconstructed/monsters')
    args=parser.parse_args()
    result=build(json.loads(args.active_models.read_text()),args.output)
    config=ROOT/'config/monster-recovery.json'
    config.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
