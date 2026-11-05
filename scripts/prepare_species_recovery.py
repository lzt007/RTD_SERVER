"""Per-family candidates: exact artwork, then species/attribute/level; originals untouched."""
import argparse,copy,hashlib,json,re
from pathlib import Path
from PIL import Image,ImageOps
from prepare_monster_recovery import ROOT,WS,convert_model,pointers
from prepare_wolf_closed_bundle import rebuild
from prepare_squirrel_recovery import shadow_image
POLICY='species-attribute-level-scale-v2'
ATTRS={'f':'fire','w':'water','h':'holy','d':'dark','u':'un'}
def family(name):
 m=re.search(r'ms\d+_[^_]+',name);return m[0] if m else ''
def attribute(name):
 tokens=name.split('_')
 for token in tokens[2:]:
  if token in ('fire','water','holy','dark','un','gold','silver'):return token
  if token in ATTRS:return ATTRS[token]
 return None
def level(name):
 m=re.search(r'_lv(\d+)',name)
 if m:return int(m[1])
 return 1

def lineage(name):
 f=family(name)
 if f in ('ms01_mind','ms03_mind'):return 'mind'
 if f=='ms04_dra' or f.endswith(("_bd","_sen","_sr")):
  suffix=name.split(f+"_",1)[-1].split("_")[0]
  return f+"_"+suffix
 return f
def choose_source(target,attr,names):
 names=[n for n in names if lineage(n)==lineage(target)]
 if not names:return None
 return min(names,key=lambda n:(n!=target,attribute(n)!=attr,max(level(n)-level(target),0)>0,abs(level(n)-level(target)),n))
def level_scale(tier):return round(min(1.9,1.+.3*max(0,tier-1)),2)
def scale_for(target,source):
 return max(1.,level_scale(level(target))/level_scale(level(source)))
def design(name):
 name=re.sub(r'^ast_','',name)
 return re.sub(r'_(fire|water|holy|dark|un|f|w|h|d|u)(?=_|$)','_ATTR',name)
def recolor(image,attr):
 alpha=image.getchannel('A');gray=ImageOps.grayscale(image)
 colors={'fire':('#28100c','#fca477'),'water':('#091c35','#87ccff'),'holy':('#302508','#fff0a0'),'dark':('#190d2c','#bf91e8'),'un':('#161616','#dddddd'),'gold':('#382206','#ffe08a'),'silver':('#15191c','#e0e8ef')}
 low,high=colors[attr];result=ImageOps.colorize(gray,low,high).convert('RGBA');result.putalpha(alpha);return result

def polish(path,output,model,source_model,tints,shadow=False):
 import UnityPy
 env=UnityPy.load(str(path));objects={o.path_id:o for o in env.objects}
 root=next(o for o in env.objects if o.type.name=='GameObject' and o.read_typetree()['m_Name']=='ast_'+model)
 transform=next(objects[p['m_PathID']] for _,p in root.read_typetree()['m_Component'] if objects[p['m_PathID']].type.name=='Transform')
 tree=transform.read_typetree();scale=scale_for(model,source_model);tree['m_LocalScale']={k:v*scale for k,v in tree['m_LocalScale'].items()};transform.save_typetree(tree)
 expected={}
 for obj in env.objects:
  if obj.type.name=='GameObject':
   tree=obj.read_typetree();tree['m_IsActive']=0;obj.save_typetree(tree)
  if obj.type.name!='Texture2D':continue
  tree=obj.read_typetree();name=tree['m_Name'];image=obj.read().image.convert('RGBA')
  if name in tints:image=recolor(image,tints[name])
  if shadow:image=shadow_image(image)
  expected[name]=image.tobytes();tree['image data']=image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes();obj.save_typetree(tree)
 # Source materials already reference their source textures. Only a newly tinted
 # model-named copy needs rebinding; exact multi-material prefabs retain each map.
 if model in tints:
  texture_id=next(o.path_id for o in env.objects if o.type.name=='Texture2D' and o.read_typetree()['m_Name']==model)
  for obj in env.objects:
   if obj.type.name!='Material':continue
   tree=obj.read_typetree()
   for key,value in tree['m_SavedProperties']['m_TexEnvs']:
    if key['name']=='_MainTex':value['m_Texture']={'m_FileID':0,'m_PathID':texture_id}
   obj.save_typetree(tree)
 path.write_bytes(env.file.save());info=rebuild(path,output,policy=POLICY)
 check=UnityPy.load(str(output));ids={o.path_id for o in check.objects}
 for obj in check.objects:
  for ptr in pointers(obj.read_typetree()):
   if ptr['m_PathID'] and (ptr['m_FileID'] or ptr['m_PathID'] not in ids):raise ValueError('Unclosed reference')
  if obj.type.name=='Texture2D' and obj.read().image.convert('RGBA').tobytes()!=expected[obj.read_typetree()['m_Name']]:raise ValueError('Pixel mismatch')
 return {**info,'visual_scale':scale,'recolored_textures':tints,'shadow_recolor':shadow,'activation_flag':0,'runtime_verified':False}

def build(species,only_models=None,excluded_sources=None):
 index=json.loads((ROOT/'docs/resource-audit/new-backup/新备份资源索引.json').read_text());sources=index['sources']
 from collections import defaultdict
 texture_options_by_source=defaultdict(list)
 for asset in index['assets']:
  if asset['type']=='Texture2D':texture_options_by_source[asset['source']].append(asset['name'])
 cross_species_fallback=False
 if species=='ms01_fish':
  audit=next(r for r in json.loads((ROOT/'docs/resource-audit/全种族四来源审计.json').read_text()) if r['family']==species)
  cross_species_fallback=all(not entries for entries in audit['sources'].values())
 candidates={a['name'][4:]:a for a in index['assets'] if a['type']=='GameObject' and a['name'].startswith('ast_') and (family(a['name'])==species or (species=='ms03_mind' and family(a['name'])=='ms01_mind') or (cross_species_fallback and family(a['name'])=='ms01_fugu'))}
 raw=json.loads((ROOT/'resources/master-data/ENEMY_UNIT_MASTER.json').read_text())['result'][0]['data_list']
 existing=json.loads((ROOT/'config/monster-recovery.json').read_text());targets={r['model']:r for r in existing['bundles'] if family(r['model'])==species}
 apk=json.loads((ROOT/'docs/resource-audit/全种族APK内置扫描.json').read_text())
 native={o['name'].removeprefix('ast_') for o in apk[0]['objects'] if o['type']=='GameObject' and not any(token in o['name'] for token in ('_wait','_atk'))}
 for enemy in raw:
  if family(enemy['model'])==species and enemy['model'] not in native:targets.setdefault(enemy['model'],{})
 motion_names={};actions={}
 for line in (ROOT/'docs/resource-audit/loading-chain/loader-definitions.tsv').read_text().splitlines():
  parts=line.split('\t')
  if parts[0]=='M':motion_names[int(parts[1])]=parts[2]
  elif parts[0]=='A':actions[(int(parts[1]),int(parts[2]))]=int(parts[3])
 out=ROOT/'resources/reconstructed/species-recovery'/species;out.mkdir(parents=True,exist_ok=True);(out/'bundles').mkdir(exist_ok=True)
 rows=json.loads((out/'validation.json').read_text()) if only_models and (out/'validation.json').exists() else [];rows=[r for r in rows if r['model'] not in (only_models or [])]
 failures=json.loads((out/'failures.json').read_text()) if only_models and (out/'failures.json').exists() else []
 failures=[r for r in failures if r['model'] not in (only_models or [])]
 for model in sorted(targets):
  if only_models and model not in only_models:continue
  if (ROOT/'resources/bundles'/(model+'.unity3d')).exists():continue
  requested=sorted({r['texture'] for r in raw if r['model']==model}-{'na'})
  values={r['attribute'] for r in raw if r['model']==model}
  native_attr={1:'un',2:'fire',3:'water',4:'holy',5:'dark'}.get(next(iter(values))) if len(values)==1 else None
  attr=attribute(model) or (attribute(requested[0]) if requested else None) or native_attr or 'un'
  usable=[n for n in candidates if n not in (excluded_sources or set()) and not (species=='ms01_wolf' and n.startswith('550_'))]
  selection_model=model.replace('ms01_fish','ms01_fugu') if cross_species_fallback else model
  chosen=choose_source(selection_model,attr,usable)
  if not chosen:failures.append(dict(model=model,reason='No same-species source'));continue
  prefixes=set()
  for enemy in raw:
   if enemy['model']!=model:continue
   for column in (0,1):
    motion=motion_names.get(actions.get((enemy['type']+36,column)),'')
    if motion.endswith(('_wait_01','_atk_01')):prefixes.add(motion.rsplit('_',2)[0])
  motion_family=next(iter(prefixes)) if len(prefixes)==1 else species
  if any(tag in species for tag in ('_dra','_four','_fly','_wolf')):
   from select_backup_skeleton import select_source
   ranked=[];remaining=[n for n in usable if lineage(n)==lineage(model)]
   while remaining:
    name=choose_source(model,attr,remaining);ranked.append(candidates[name]);remaining.remove(name)
   selected,score=select_source(ranked,sources,WS/'resources/unpacked',motion_family);chosen=selected['name'].removeprefix('ast_')
  source=WS/'resources/unpacked'/sources[candidates[chosen]['source']]['path']
  source_adaptations=[]
  if model=='ms01_suika_01':
   from suika_head_adapter import adapt
   adapted=out/'sources'/'suika-head-source.unity3d';source_adaptations.append(adapt(source,adapted));source=adapted
  if model=='ms03_mind_01':
   from mind_boss_adapter import adapt
   adapted=out/'sources'/(chosen+'-bear-controls.unity3d');source_adaptations.append(adapt(source,adapted));source=adapted
  if cross_species_fallback:
   from mind_boss_adapter import adapt
   adapted=out/'sources'/(chosen+'-fish-controls.unity3d');source_adaptations.append(adapt(source,adapted,chosen,'ms01_fish',True));source=adapted
  jobs={};tints={};provenance={};texture_aliases={}
  names=requested or [model]
  for name in names:
   wanted=attribute(name) or attr
   same_design=[n for n in candidates if design(n)==design(chosen) and attribute(n)==wanted]
   selected=min(same_design) if same_design else chosen
   jobs[name]=WS/'resources/unpacked'/sources[candidates[selected]['source']]['path'];provenance[name]=selected
   texture_options=texture_options_by_source[candidates[selected]['source']]
   texture_name=name if name in texture_options else next((n for n in texture_options if attribute(n)==wanted),None)
   if texture_name is None and len(texture_options)==1:texture_name=texture_options[0]
   if texture_name is None:
    texture_name=next((n for n in texture_options if attribute(n)=='water'),None) or next(iter(texture_options),None)
   if texture_name is not None:
    texture_aliases[name]=texture_name
    actual_attr=attribute(texture_name)
    if actual_attr!=wanted and (selected!=model or name!=model):tints[name]=wanted
   elif selected!=model and attribute(selected)!=wanted:tints[name]=wanted
  try:
   temp=out/(model+'.unity3d');row=convert_model(source,temp,model,jobs,source_model=chosen,motion_family=motion_family,texture_aliases=texture_aliases)
   info=polish(temp,out/'bundles'/temp.name,model,chosen,tints,shadow='_sh_' in model and chosen!=model)
   row.update(info);row['skeleton_adaptations']+=source_adaptations;row.update(inferred=chosen!=model or bool(tints) or info['visual_scale']!=1 or bool(source_adaptations),reason='Four-source review: same-species artwork; attribute matched first; level scale/color inferred where missing.',source_model=chosen,cross_species_fallback=cross_species_fallback,texture_source_models=provenance,texture_source_names=texture_aliases,texture_selection_revision='explicit-source-name-v2',status='validated_candidate')
   if cross_species_fallback:row['reason']='No ms01_fish artwork in four-source named-object audit; aquatic pufferfish fallback, original fish motion binding independently checked; inferred substitute.'
   rows.append(row);print('Validated',model,'<-',chosen,flush=True)
  except Exception as exc:
   alternatives=[n for n in usable if n!=chosen and lineage(n)==lineage(model)]
   recovered=None
   if alternatives:
    print('Trying next same-species source',model,chosen,type(exc).__name__,str(exc)[:600],flush=True)
    retried,_=build(species,[model],set(excluded_sources or set())|{chosen})
    recovered=next((r for r in retried if r['model']==model),None)
   if recovered:
    recovered.setdefault('source_selection_failures',[]).insert(0,dict(source_model=chosen,error=type(exc).__name__,detail=str(exc)[:1500]));rows.append(recovered)
   else:
    failures.append(dict(model=model,source_model=chosen,error=type(exc).__name__,detail=str(exc)[:1500]));print('Blocked',model,type(exc).__name__,flush=True)
  (out/'validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(out/'failures.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2)+'\n')
 (out/'validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(out/'failures.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2)+'\n')
 return rows,failures
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('species');parser.add_argument('--only',nargs='*');args=parser.parse_args();build(args.species,args.only)
