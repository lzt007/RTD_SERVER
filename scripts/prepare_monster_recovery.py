"""Offline Unity 5 -> Unity 3.5 visual recovery. Requires UnityPy and Pillow.
Never edits original files. Outputs are inferred compatibility assets, not original art.
"""
import copy
import hashlib
import json
import struct
import zipfile
from functools import lru_cache
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

@lru_cache(maxsize=1)
def motion_catalog():
    return json.loads((ROOT/'docs/resource-audit/loading-chain/catalog.json').read_text())

@lru_cache(maxsize=None)
def motion_paths(family, clip_names=None):
    import UnityPy
    catalog=motion_catalog()
    result=set();found=set()
    names=set(clip_names) if clip_names is not None else ({f'{family if family.startswith("ms") else "ms01_"+family}_wait_01',f'{family if family.startswith("ms") else "ms01_"+family}_atk_01'} if family!='death' else {'ms00_death_wait_01','ms00_death_atk_01'})
    with zipfile.ZipFile(APK) as z:
        for obj in catalog['objects'].values():
            if obj['type']!='AnimationClip' or obj['name'] not in names:continue
            source=catalog['sources'][catalog['files'][obj['file']]['source']]
            prefix=str(APK.relative_to(WS))+':'
            origin=next((o for o in source['origins']
                         if o['category']=='apk_data' and o['path'].startswith(prefix)),None)
            if origin is None:continue
            entry=origin['path'][len(prefix):]
            t=next(o for o in UnityPy.load(z.read(entry)).objects if o.path_id==obj['path_id']).read_typetree()
            found.add(obj['name'])
            for k in ('m_RotationCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves'):
                result.update(c['path'] for c in t[k])
    if not result or (clip_names is not None and found!=names):raise ValueError('Original motions not found')
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

def unused_brightness_keywords(keywords, script):
    """One known Standard-material leftover, absent from custom brightness variants."""
    return (keywords=='_ALPHAPREMULTIPLY_ON' and 'Shader "Character/brightness"' in script
            and 'Blend SrcAlpha OneMinusSrcAlpha' in script and keywords not in script
            and not any(token in script for token in ('multi_compile','shader_feature','Keywords {')))

def redundant_transparent_tag(tags, script):
    """A material tag identical to the custom shader's own tag changes no state."""
    import re
    values=re.findall(r'"RenderType"\s*=\s*"([^"]+)"',script)
    return (list(tags)==[('RenderType','Transparent')] and bool(values)
            and all(value=='Transparent' for value in values)
            and 'Shader "Character/brightness"' in script)

@lru_cache(maxsize=1)
def native_animation_controller_templates():
    """Use the shipped 3.5 script schema, never a Unity 5 MonoScript hash/layout."""
    import UnityPy
    catalog=motion_catalog()
    for meta in catalog['objects'].values():
        if meta['type']!='MonoScript' or meta['name']!='AnimationController':continue
        source=catalog['sources'][catalog['files'][meta['file']]['source']]
        origin=next((o for o in source['origins'] if o['category']=='preload90'),None)
        if origin is None:continue
        env=UnityPy.load(str(WS/origin['path']))
        script=next(o for o in env.objects if o.path_id==meta['path_id'])
        for obj in env.objects:
            if obj.type.name!='MonoBehaviour':continue
            tree=obj.read_typetree()
            if tree.get('m_Script',{}).get('m_PathID')==script.path_id and tree['m_Script']['m_FileID']==0:
                return {'MonoScript':script,'MonoBehaviour':obj}
    raise ValueError('Native AnimationController templates unavailable')

def convert_model(source,output,model,textures, *, source_model=None, motion_family=None, texture_aliases=None):
    import UnityPy
    from UnityPy.helpers.MeshHelper import MeshHandler
    from PIL import Image
    env=UnityPy.load(str(source));target=UnityPy.load(str(TEMPLATE)).file
    templates={}
    for obj in target.objects.values():templates.setdefault(obj.type.name,obj)
    if any(o.type.name in ('MonoScript','MonoBehaviour') for o in env.objects):
        for typ,obj in native_animation_controller_templates().items():
            obj=copy.copy(obj);schema=copy.deepcopy(obj.serialized_type)
            occupied={t.class_id for t in target.types}
            if obj.type_id in occupied and typ=='MonoBehaviour':
                obj.type_id=min(occupied|{0})-1
                if schema is not None:schema.class_id=obj.type_id
            if schema is not None and obj.type_id not in occupied:target.types.append(schema)
            obj.serialized_type=schema;templates[typ]=obj
    original_trees={k:o.read_typetree() for k,o in templates.items()}
    objects={};trees={};images={};vertices=0;shader_reports=[]
    src={o.path_id:o for o in env.objects}
    vertices=sum(o.read_typetree()['m_VertexData']['m_VertexCount'] for o in env.objects if o.type.name=='Mesh' and o.assets_file.header.version<=9)
    shader_id=next(i for i,o in src.items() if o.type.name=='Shader')
    root_id=next(i for i,o in src.items() if o.type.name=='GameObject' and (o.read_typetree()['m_Name']=='ast_'+source_model if source_model else o.read_typetree()['m_Name'].startswith('ast_')))
    from backup_skeleton_compat import adapt_ms02_dragon_tail
    adapted_source,skeleton_adaptations=adapt_ms02_dragon_tail({i:(o.type.name,o.read_typetree()) for i,o in src.items()},motion_family)
    source_reachable=set(src)
    if source_model is not None:
        source_reachable=set();todo=[root_id]
        while todo:
            current=todo.pop()
            if current in source_reachable:continue
            source_reachable.add(current)
            if current not in src:raise ValueError('Missing source dependency '+str(current))
            for pointer in pointers(src[current].read_typetree()):
                if pointer['m_FileID']:raise ValueError('External source dependency requires explicit resolution')
                if pointer['m_PathID']:todo.append(pointer['m_PathID'])
    def add(typ,tree,pid):
        obj=copy.copy(templates[typ]);obj.assets_file=target;obj.path_id=pid
        obj.save_typetree(merge_schema(tree,original_trees[typ]));objects[pid]=obj;trees[pid]=(typ,tree)
    for pid,obj in src.items():
        if pid not in source_reachable:continue
        typ=obj.type.name;t=copy.deepcopy(adapted_source[pid][1])
        if typ=='AssetBundle':continue
        if typ=='MonoScript':
            if any(t.get(k)!=original_trees['MonoScript'].get(k) for k in ('m_ClassName','m_Namespace','m_AssemblyName')):raise ValueError('Unsupported native script class')
            t=copy.deepcopy(original_trees['MonoScript'])
        elif typ=='MonoBehaviour':
            if set(t)!=set(original_trees['MonoBehaviour']):raise ValueError('Unsupported script serialized fields')
            script=src[t['m_Script']['m_PathID']].read_typetree()
            if script.get('m_ClassName')!='AnimationController':raise ValueError('Unsupported behaviour class')
        elif typ=='Shader':
            if source_model is not None:
                from backup_shader_compatibility import native_shader_for
                t,proof=native_shader_for(t,original_trees['Shader'])
            else:t=copy.deepcopy(original_trees['Shader'])
        elif typ=='Material':
            # Original Android shader and its matching saved-property defaults.
            source_material=t
            if source_model is not None:
                from backup_shader_compatibility import validate_shader_mapping, native_shader_for
                source_shader=src[source_material['m_Shader']['m_PathID']].read_typetree()
                ignored_keywords=unused_brightness_keywords(source_material.get('m_ShaderKeywords',''),source_shader.get('m_Script',''))
                for field,default in (('m_CustomRenderQueue',-1),('m_ShaderKeywords',''),('stringTagMap',[]),('disabledShaderPasses',[])):
                    if field=='m_ShaderKeywords' and ignored_keywords:continue
                    if field=='stringTagMap' and redundant_transparent_tag(source_material.get(field,[]),source_shader.get('m_Script','')):continue
                    if source_material.get(field,default)!=default and field not in original_trees['Material']:
                        raise ValueError('Unsupported material render override '+field)
                shader_pointer=source_material['m_Shader']
                if shader_pointer['m_FileID']:raise ValueError('External shader requires explicit resolution')
                mapped_shader,proof=native_shader_for(src[shader_pointer['m_PathID']].read_typetree(),original_trees['Shader'])
                if ignored_keywords:proof['unused_source_material_keywords']=['_ALPHAPREMULTIPLY_ON']
                if redundant_transparent_tag(source_material.get('stringTagMap',[]),source_shader.get('m_Script','')):proof['redundant_source_material_tags']=[['RenderType','Transparent']]
                shader_reports.append(proof)
            t=copy.deepcopy(original_trees['Material']);t['m_Name']=source_material.get('m_Name',model)
            t['m_Shader']=copy.deepcopy(source_material['m_Shader']) if source_model is not None else {'m_FileID':0,'m_PathID':shader_id}
            for field in ('m_Floats','m_Colors'):
                t['m_SavedProperties'][field]=copy.deepcopy(source_material.get('m_SavedProperties',{}).get(field,t['m_SavedProperties'][field]))
            for key,v in t['m_SavedProperties']['m_TexEnvs']:
                source_env=next((value for prop,value in source_material.get('m_SavedProperties',{}).get('m_TexEnvs',[]) if prop['name']==key['name']),None)
                v.update(copy.deepcopy(source_env)) if source_env else None
                if source_env is None:v['m_Texture']={'m_FileID':0,'m_PathID':0}
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
    texture_environments={str(Path(source)):env}
    texture_jobs=[(o.read_typetree()['m_Name'],source,o,o.path_id,False) for o in env.objects if o.type.name=='Texture2D']
    for index,(name,path) in enumerate(textures.items()):
        texture_environment=texture_environments.get(str(Path(path)))
        if texture_environment is None:
            texture_environment=UnityPy.load(str(path));texture_environments[str(Path(path))]=texture_environment
        candidates=[o for o in texture_environment.objects if o.type.name=='Texture2D']
        selected_name=(texture_aliases or {}).get(name,name)
        exact=[o for o in candidates if o.read_typetree()['m_Name']==selected_name]
        attr=name.rsplit('_',1)[-1]
        matched=exact or [o for o in candidates if o.read_typetree()['m_Name'].endswith('_'+attr)]
        if not matched and len(candidates)!=1:raise ValueError('Ambiguous texture mapping '+name)
        tex=(matched or candidates)[0]
        existing=next((o.path_id for o in env.objects if o.type.name=='Texture2D' and o.read_typetree()['m_Name']==name),None)
        texture_jobs.append((name,path,tex,existing or 10000+index,True))
    for name,path,tex,pid,export in texture_jobs:
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
        add('Texture2D',t,pid)
        if export:exports.append((name,pid))
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
    family=motion_family or ('wolf' if 'wolf' in model else ('slawing' if 'slawing' in model else 'sla'))
    reachable=set(); pending=[root_id]
    while pending:
        current=pending.pop()
        if current in reachable:continue
        reachable.add(current)
        pending.extend(p['m_PathID'] for p in pointers(trees[current][1]) if not p['m_FileID'] and p['m_PathID'] and p['m_PathID'] in trees)
    motion_info=validate_motion_paths({i:trees[i] for i in reachable},family,model,source_trees=adapted_source)
    missing_paths=motion_info['missing_motion_paths']
    roundtrip=all(sf.objects[pid].read().image.convert('RGBA').tobytes()==images[name].tobytes() for name,path,tex,pid,export in texture_jobs)
    report=dict(model=model,source=str(Path(source).relative_to(WS)),source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                bundle=output.name,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),internal_file=unique,
                vertices=vertices,mesh_roundtrip=mesh_roundtrip,missing_pointers=missing,missing_motion_paths=missing_paths,texture_roundtrip=roundtrip,
                textures={name:dict(source=str(Path(p).relative_to(WS)),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for name,p in textures.items()})
    report['skeleton_adaptations']=skeleton_adaptations
    report['shader_mapping']=shader_reports
    report.update(motion_info)
    report.update(validate_embedded_motion_roundtrip(env,check,source_reachable,adapted_source))
    if missing or missing_paths or not roundtrip or not mesh_roundtrip:raise ValueError(report)
    return report

def extract_originals(directory, family="sla"):
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
        binding=next(b for b in catalog['bindings'] if b['path']=='prefab/enemies/ms01_'+family+'_lv1')
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
            if oid==root:t['m_Name']='ast_ms01_'+family+'_lv1'
            obj=copy.copy(templates[objects[oid]['type']]);obj.assets_file=target;obj.path_id=ids[oid]
            obj.save_typetree(t);out[obj.path_id]=obj
        target.objects=out;target.externals=[]
        prefab=directory/('original-'+family+'-lv1.assets');prefab.write_bytes(target.save())
        textures={}
        for attr in ('fire','water','holy','dark'):
            name='ms01_'+family+'_lv1_'+attr
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


def validate_embedded_motion_roundtrip(source_env, converted_env, only_path_ids=None, source_overrides=None):
    """Reject animation conversions that lose authored samples or packed curves."""
    original={o.path_id:o.read_typetree() for o in source_env.objects if o.type.name=='AnimationClip' and (only_path_ids is None or o.path_id in only_path_ids)}
    if source_overrides is not None:original={pid:source_overrides[pid][1] for pid in original}
    converted={o.path_id:o.read_typetree() for o in converted_env.objects if o.type.name=='AnimationClip'}
    reports=[]
    def normalized(value):
        if isinstance(value,dict):
            # Unity 3.5 has quaternion curves but no newer Euler rotation-order tag.
            return {k:normalized(v) for k,v in value.items() if k!='m_RotationOrder'}
        if isinstance(value,(tuple,list)):return [normalized(v) for v in value]
        return value
    for pid,src in original.items():
        if pid not in converted:raise ValueError('Embedded animation clip missing after conversion '+str(pid))
        dst=converted[pid];name=src.get('m_Name',str(pid))
        if src.get('m_Legacy') is False:raise ValueError('Non-legacy muscle animation requires explicit bake: '+name)
        if src.get('m_EulerCurves'):raise ValueError('Euler animation requires quaternion bake: '+name)
        if src.get('m_PPtrCurves'):raise ValueError('Object-reference animation unsupported by target: '+name)
        samples={}
        for key in ('m_RotationCurves','m_CompressedRotationCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves'):
            a=src.get(key,[]);b=dst.get(key,[])
            if normalized(a)!=normalized(b):raise ValueError('Animation curve/packed-data loss '+name+':'+key)
            samples[key]=sum(len(c.get('curve',{}).get('m_Curve',[])) for c in a)
        for key in ('m_SampleRate','m_WrapMode','m_Compressed'):
            if src.get(key)!=dst.get(key):raise ValueError('Animation metadata loss '+name+':'+key)
        if not any(samples.values()) and not src.get('m_CompressedRotationCurves'):
            raise ValueError('Embedded clip contains no supported animation samples: '+name)
        reports.append(dict(name=name,path_id=pid,samples=samples,compressed_rotation_curves=len(src.get('m_CompressedRotationCurves',[]))))
    return dict(embedded_motion_roundtrip=True,embedded_motion_samples=reports)


def validate_motion_paths(trees, family, model, source_trees=None):
    """Check original APK runtime clips when present, plus all embedded clips.

    Missing APK clips are reported as such, never claimed to be recovered.
    Embedded animation validation follows the actual Animation component owner.
    """
    def paths_from(transform_id, data=None):
        data=trees if data is None else data
        found=set()
        def walk(tid,prefix):
            found.add(prefix)
            tree=data[tid][1]
            for pointer in tree['m_Children']:
                child=pointer['m_PathID']; node=data[child][1]
                name=data[node['m_GameObject']['m_PathID']][1]['m_Name']
                walk(child,prefix+'/'+name if prefix else name)
        walk(transform_id,'')
        return found
    transforms={t['m_GameObject']['m_PathID']:pid for pid,(typ,t) in trees.items() if typ=='Transform'}
    missing=[]; clips=[]; source_unbound=[]
    for pid,(typ,animation) in trees.items():
        if typ!='Animation':continue
        owner=animation['m_GameObject']['m_PathID']
        actual=paths_from(transforms[owner])
        references=list(animation.get('m_Animations',[]))+[animation.get('m_Animation',{'m_PathID':0})]
        seen_clips=set()
        for pointer in references:
            clip_id=pointer['m_PathID']
            if not clip_id or clip_id in seen_clips:continue
            seen_clips.add(clip_id)
            clip_type,clip=trees[clip_id]
            if clip_type!='AnimationClip':raise ValueError('Animation references non-clip')
            clips.append(clip.get('m_Name',str(clip_id)))
            required={c['path'] for key in ('m_RotationCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves') for c in clip.get(key,[])}
            absent=required-actual
            if source_trees is not None and owner in transforms:
                source_transforms={t['m_GameObject']['m_PathID']:i for i,(typ,t) in source_trees.items() if typ=='Transform'}
                source_animation=source_trees.get(pid)
                source_clip=source_trees.get(clip_id)
                if (source_animation and source_clip and owner in source_transforms
                        and source_clip[1].get('m_Name') == clip.get('m_Name')
                        and source_animation[1]['m_GameObject']['m_PathID']==owner):
                    source_actual=paths_from(source_transforms[owner],source_trees)
                    for path in sorted(absent-source_actual):
                        curves=[(key,c) for key in ('m_RotationCurves','m_PositionCurves','m_ScaleCurves','m_FloatCurves') for c in clip.get(key,[]) if c['path']==path]
                        safe=True
                        for key,c in curves:
                            keys=c.get('curve',{}).get('m_Curve',[])
                            is_static_scale=key=='m_ScaleCurves'
                            is_source_static_position=key=='m_PositionCurves'
                            safe &= (is_static_scale or is_source_static_position) and len(keys)==1 and all(isinstance(v,(int,float)) and __import__('math').isfinite(v) and (v!=0 or is_source_static_position) for v in keys[0].get('value',{}).values()) and set(keys[0].get('value',{}))=={'x','y','z'} and all(keys[0].get(slope)==dict(x=0.,y=0.,z=0.) for slope in ('inSlope','outSlope'))
                            safe &= any({k:v for k,v in c.items() if k!='curve'}=={k:v for k,v in sc.items() if k!='curve'} and {k:v for k,v in c.get('curve',{}).items() if k!='m_RotationOrder'}=={k:v for k,v in sc.get('curve',{}).items() if k!='m_RotationOrder'} for sc in source_clip[1].get(key,[]))
                        if curves and safe:
                            absent.remove(path);source_unbound.append(dict(animation_id=pid,clip_id=clip_id,path=path,reason='Source already unbound single constant sample preserved verbatim',curve_types=[key for key,c in curves],samples=[c['curve']['m_Curve'][0] for key,c in curves]))
            missing.extend(absent)
    # Original EnemyData type 33 uses MotionAssign's org sword clips, not
    # names derived from the ms03_sen resource family.
    original_clips=('org_atk_swd_01','org_wait_swd_01') if model=='ms03_sen_olgadia_01' else None
    try:
        expected=motion_paths(family,original_clips) if original_clips else motion_paths(family)
    except ValueError as exc:
        if str(exc)!='Original motions not found':raise
        original='not_present_in_original_apk'
        if not clips and family not in {'book','floor','kaidan'}:
            missing.append('no original or embedded motion evidence')
    else:
        original='validated_original_apk_type33' if original_clips else 'validated_original_apk'
        skeletons=hierarchy_paths(trees)
        if not skeletons:missing.append('no move hierarchy for original runtime clips')
        for paths in skeletons:missing.extend(expected-paths)
    result=dict(missing_motion_paths=sorted(set(missing)),motion_provenance=original,original_motion_scope='wait_and_attack',embedded_motion_clips=sorted(set(clips)),source_unbound_motion_paths=source_unbound)
    if original_clips:result['original_motion_clips']=list(original_clips)
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active-models',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'resources/reconstructed/monsters')
    args=parser.parse_args()
    result=build(json.loads(args.active_models.read_text()),args.output)
    config=ROOT/'config/monster-recovery.json'
    config.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
