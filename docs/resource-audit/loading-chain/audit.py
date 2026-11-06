"""Resolve typed Resources bindings, bundle exports and reachable serialized dependencies."""
from pathlib import Path
from collections import defaultdict,Counter,deque
from functools import lru_cache
import os,sys,json,csv,zipfile,re,tempfile,html
import UnityPy
P=Path(__file__).parent;ROOT=P.parents[2];WS=ROOT.parent
D=json.loads((P/'catalog.json').read_text());F=D['files'];O=D['objects'];S=D['sources']
def writecsv(name,header,rows):
 with (P/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(header);w.writerows(rows)
def origins(sid):return S[sid]['origins']
def provenance(oid):return '；'.join(a['path'] for a in origins(F[O[oid]['file']]['source']))
def original(oid):return any(a['category']!='reconstructed' for a in origins(F[O[oid]['file']]['source']))
byfile=defaultdict(set);byname=defaultdict(list)
for fid,f in F.items():
 byfile[Path(f['name'].replace('\\','/')).name.lower()].add(fid)
 if len(S[f['source']]['files'])==1:
  for a in origins(f['source']):byfile[a['path'].replace('\\','/').rsplit('/',1)[-1].lower()].add(fid)
for oid,o in O.items():byname[o['name'].lower(),o['type']].append(oid)
def resolve(fid,ptr):
 pid=str(ptr['m_PathID']);ext=ptr['m_FileID']
 if pid=='0':return [],'null'
 if not ext:
  oid=F[fid]['objects'].get(pid);return ([oid],'resolved') if oid else ([], 'local PathID missing')
 if ext>len(F[fid]['externals']):return [],'external FileID invalid'
 path=F[fid]['externals'][ext-1].replace('\\','/');base=path.rsplit('/',1)[-1].lower()
 if 'unity default resources' in base or 'unity_builtin_extra' in base:return [],'engine builtin'
 candidates=[f for f in byfile[base] if pid in F[f]['objects']]
 # Prefer exact same APK/directory context, choosing original APK when parent has that alias.
 parents=[a['path'].rsplit('/',1)[0] for a in origins(F[fid]['source'])]
 def score(f):
  shared=[a['path'].rsplit('/',1)[0] for a in origins(F[f]['source']) if a['path'].rsplit('/',1)[0] in parents]
  return (any('/inputs/original/' in a for a in shared), bool(shared), F[f]['source']==F[fid]['source'])
 if not candidates:return [],'external file/PathID missing: '+path
 best=max(map(score,candidates));candidates=[f for f in candidates if score(f)==best]
 return sorted({F[f]['objects'][pid] for f in candidates}),'resolved' if len(candidates)==1 else 'ambiguous external source'
resource=defaultdict(list);export=defaultdict(list);binding_rows=[]
for row in D['bindings']:
 ids,status=resolve(row['file'],row['pointer']);resource[row['path'].lower()]+=ids
 binding_rows.append([row['path'],status,'；'.join(ids),'；'.join(O[i]['type']+':'+O[i]['name'] for i in ids)])
for row in D['exports']:
 ids,status=resolve(row['file'],row['pointer'])
 for oid in ids:export[row['name'].lower(),O[oid]['type']].append(oid)
writecsv('APK_Resources绑定核对.csv',['Resources路径','外部指针状态','解析对象键','对象类型和名称'],binding_rows)
@lru_cache(maxsize=12)
def load_source(sid):
 a=origins(sid)[0]['path']
 if '.apk:' in a:
  apk,path=a.split(':',1)
  with zipfile.ZipFile(WS/apk) as z:blob=z.read(path)
 else:blob=(WS/a).read_bytes()
 env=UnityPy.load(blob);return list({id(o.assets_file):o.assets_file for o in env.objects}.values())
def object_reader(oid):
 fid=O[oid]['file'];sid,fi=map(int,fid.split(':'));return load_source(sid)[fi].objects[O[oid]['path_id']]
@lru_cache(maxsize=None)
def edges(oid):
 typ=O[oid]['type']
 if typ in ('Texture2D','Mesh','AnimationClip','MonoScript','TextAsset','AudioClip'):return [],[]
 try:tree=object_reader(oid).read_typetree()
 except Exception as exc:return [],[dict(object=oid,issue='typetree unavailable',detail=str(exc)[:180])]
 children=[];issues=[];fid=O[oid]['file']
 def walk(v,path):
  if isinstance(v,dict):
   if 'm_FileID' in v and 'm_PathID' in v:
    found,status=resolve(fid,v);children.extend(found)
    if status not in ('resolved','null','engine builtin'):issues.append(dict(object=oid,field=path,issue=status,pointer=v,targets=found))
   else:
    for k,value in v.items():walk(value,path+'.'+str(k))
  elif isinstance(v,(list,tuple)):
   for i,value in enumerate(v):walk(value,path+f'[{i}]')
 walk(tree,'');return sorted(set(children)),issues
@lru_cache(maxsize=None)
def closure(root):
 q=[root];visited=set();issues=[]
 while q:
  oid=q.pop()
  if oid in visited:continue
  visited.add(oid);children,found=edges(oid);q+=children;issues+=found
 return visited,issues
sys.path.insert(0,str(ROOT))
from rtd.services.api import API
from rtd.masters.catalog import load_catalog
from rtd.policies.quest_content import SINGLE_QUESTS,layer_quests
os.environ.update(RTD_EVENT_RECONSTRUCTION='1',RTD_SHINGETSU_RECONSTRUCTION='1')
with tempfile.TemporaryDirectory() as tmp:api=API(Path(tmp)/'audit.sqlite3')
masters,_=load_catalog();orig={r['id']:r for r in masters[20]['data_list']};effective={r['id']:r for r in api.masters[20]['data_list']};qs={r['id']:r for r in api.masters[30]['data_list']};tables={r['id']:r for r in api.masters[21]['data_list']}
defs={};local=set();unit=set();motion={};action={};category={};effects=defaultdict(set)
for line in (P/'loader-definitions.tsv').read_text().splitlines():
 r=line.split('\t');tag=r[0]
 if tag in ('B','G'):defs[r[1]]=dict(version=int(r[2]),path=r[3]+'/'+r[1]+'.unity3d')
 if tag=='L':local.add(r[1])
 if tag=='U':unit.add(int(r[1]))
 if tag=='M':motion[int(r[1])]=r[2]
 if tag=='A':action[int(r[1]),int(r[2])]=int(r[3])
 if tag=='C':category[int(r[1])]=int(r[2])
 if tag=='E' and len(r)>3 and r[3]:effects[int(r[1])].add(r[3])
# Bundle identity is exact prefab export OR actual filename, never an arbitrary object-name hit.
bundles=defaultdict(set)
for (n,t),ids in export.items():
 if t=='GameObject' and n.startswith('ast_'):
  for oid in ids:bundles[n[4:]].add(F[O[oid]['file']]['source'])
for sid,s in enumerate(S):
 for a in s['origins']:
  base=a['path'].rsplit('/',1)[-1]
  if base.endswith('.unity3d') and base[:-8] in defs:bundles[base[:-8]].add(sid)
requirements={};contexts={};used=set()
def req(scope,qid,e,kind,name,typ,bundle='',path='',conditional=''):
 key=(scope,kind,name,typ,bundle,path,conditional)
 requirements.setdefault(key,set()).add((qid,e['id']));contexts[scope,e['id']]=e
questids=(SINGLE_QUESTS|api.event_quests|layer_quests(api))-api.blocked_quests
for qid in sorted(questids):
 if qid not in qs:continue
 q=qs[qid];t=tables[q['enemy_table_id']]
 for slot in ['boss','death']+[f'enemy{i}' for i in range(1,19)]:
  eid=t[slot+'_set_id']
  if not eid:continue
  for scope,es in [('原始',orig),('当前',effective)]:
   e=es.get(eid,effective.get(eid))
   if not e:continue
   model=e['model'];texture=e.get('texture','');isunit=e['type'] in unit
   base='ms00_book_el_0'+str(e['chara_symbol']-9 if 10<=e['chara_symbol']<=15 else 6) if isunit else model
   if model in local:
    req(scope,qid,e,'模型',model,'GameObject',path='Prefab/Enemies/'+model)
   else:
    req(scope,qid,e,'包',base,'AssetBundle',bundle=base)
    req(scope,qid,e,'模型','ast_'+base,'GameObject',bundle=base)
    req(scope,qid,e,'材质',base,'Material',bundle=base)
   if texture and texture not in ('na','0'):
    req(scope,qid,e,'贴图',texture,'Texture2D',bundle='' if model in local else base,path='Prefab/Enemies/Textures/'+texture if model in local else '')
   if isunit:
    gid=e['chara_g_id']
    if gid>0:
     start=(gid-1)//10*10+1;group=f'{start}-{start+9}'
     req(scope,qid,e,'角色包',group,'AssetBundle',bundle=group)
     req(scope,qid,e,'角色本体',model,'GameObject',bundle=group)
    else:
     req(scope,qid,e,'角色独立包',model,'AssetBundle',bundle=model)
     req(scope,qid,e,'角色本体','ast_'+model,'GameObject',bundle=model)
   # Ordinary nonboss early-returns at action column2 (except type16).
   row=category.get(e['chara_kind'],0) if isunit else e['type']+36
   for col in range(16 if isunit or slot in ('boss','death') or e['type']==16 else 2):
    idx=action.get((row,col));n=motion.get(idx)
    if n:req(scope,qid,e,'动作',n,'GameObject',path='AnimationData/Motion/'+n,conditional='角色有BOOK_SYMBOL时改用方向动画' if isunit else '')
   if isunit:
    for n in ['el_wait','el_boss_tob','el_zako_tob','el_boss_tob_6','el_zako_tob_6']:
     req(scope,qid,e,'方向动画',n,'AnimationClip',path='AnimationData/DirectionAnimation/'+n,conditional='角色书本/朝向分支')
   for n in effects.get(e['atk_ef_id'],effects.get(0,set())):
    if 'ef_damage' not in n:req(scope,qid,e,'攻击效果',n,'GameObject',path='Prefab/ParticleEffects/'+n)
print('requirements',len(requirements),flush=True)
results=[];roots=set();allissues={};reach=set()
for key,refs in sorted(requirements.items()):
 scope,kind,name,typ,bundle,path,conditional=key;ids=[];status='';note=''
 globalhits=sorted(set(export.get((name.lower(),typ),[])+byname.get((name.lower(),typ),[])))
 if typ=='AssetBundle':
  srcs=bundles.get(bundle,set());origsrc={sid for sid in srcs if any(a['category']!='reconstructed' for a in origins(sid))}
  status='原始包存在' if origsrc else '原始包缺失，已有重建包' if srcs else '本地缺包'
  note='；'.join(a['path'] for sid in sorted(srcs) for a in origins(sid))
 elif path:
  ids=[oid for oid in resource.get(path.lower(),[]) if O[oid]['type']==typ]
  status='Resources路径与对象已解析' if ids else '对象存在但Resources路径未绑定' if globalhits else '本地未找到对象'
 else:
  candidate=export.get((name.lower(),typ),[])
  ids=[oid for oid in candidate if F[O[oid]['file']]['source'] in bundles.get(bundle,set())]
  origids=[oid for oid in ids if original(oid)]
  status='原始包内对象存在' if origids else '原始对象缺失，已有重建对象' if ids else '对象存在但不在目标包导出' if globalhits else '本地未找到对象'
  if origids:ids=origids
 if kind=='动作' and name=='null':status='空动作占位（加载失败被代码容忍）'
 if kind=='材质' and not ids:status='同名材质缓存未命中（代码允许为空；模型内材质另按依赖核对）'
 if ids:
  note='；'.join(sorted(set(provenance(i) for i in ids)))
  for oid in ids:
   roots.add(oid);nodes,issues=closure(oid);reach.update(nodes)
   for issue in issues:allissues[json.dumps(issue,sort_keys=True)]=issue
  unresolved=[issue for oid in ids for issue in closure(oid)[1]]
  if unresolved:status+='；依赖待核实'+str(len(unresolved))
 if not ids and globalhits and typ!='AssetBundle':note='其他位置同名对象：'+'；'.join(provenance(i) for i in globalhits)
 qs_used=sorted({qid for qid,eid in refs});enemies=sorted({eid for qid,eid in refs})
 family=re.match(r'(?:ast_)?ms\d+_([^_]+)',name);family=family[1] if family else ''
 results.append(dict(scope=scope,kind=kind,name=name,type=typ,bundle=bundle,path=path or defs.get(bundle,{}).get('path',''),version=defs.get(bundle,{}).get('version',''),status=status,family=family,quest_ids=qs_used,enemies=enemies,uses='；'.join(f"{qs[q]['name']}({q})／{contexts[scope,e]['name']}({e})" for q,e in sorted(refs)),evidence=note,conditional=conditional,objects=ids))
headers=['口径','类别','引用名','对象类型','所属包','加载路径','版本','状态','物种族','关卡与怪物','条件','来源证据']
def values(r):return [r[k] for k in ['scope','kind','name','type','bundle','path','version','status','family','uses','conditional','evidence']]
writecsv('全部加载需求.csv',headers,map(values,results))
missing=[r for r in results if any(s in r['status'] for s in ['缺失','缺包','未找到','未绑定','不在目标包'])]
writecsv('资源缺口与绑定问题.csv',headers,map(values,missing))
writecsv('递归依赖待核实.csv',['对象键','对象名','类型','问题','字段','详情','来源'],([i['object'],O[i['object']]['name'],O[i['object']]['type'],i['issue'],i.get('field',''),i.get('detail',str(i.get('pointer',''))),provenance(i['object'])] for i in allissues.values()))
# Compact complete object inventory: provenance is referenced through source ID instead of repeated thousands of times.
writecsv('全部资源对象.csv',['对象键','名称','类型','序列化文件','来源编号'],([oid,o['name'],o['type'],F[o['file']]['name'],F[o['file']]['source']] for oid,o in O.items()))
writecsv('资源来源.csv',['来源编号','SHA256','大小','全部位置'],([sid,s['sha256'],s['size'],'；'.join(a['path'] for a in s['origins'])] for sid,s in enumerate(S)))
(P/'graph.json').write_text(json.dumps({oid:dict(children=edges(oid)[0],issues=edges(oid)[1]) for oid in sorted(reach)},ensure_ascii=False))
(P/'results.json').write_text(json.dumps(dict(requirements=results,issues=list(allissues.values()),reachable=sorted(reach),roots=sorted(roots),quest_ids=sorted(questids)),ensure_ascii=False))
summary=dict(quest_count=len(questids),requirements=len(results),resource_rows=len(missing),roots=len(roots),reachable=len(reach),issues=len(allissues),status=dict(Counter(r['status'] for r in results)))
(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False),flush=True)
