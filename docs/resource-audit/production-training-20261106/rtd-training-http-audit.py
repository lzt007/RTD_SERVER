import json,pathlib,sys,hashlib,urllib.request,collections
import UnityPy
ROOT=pathlib.Path('/home/workspace/RTD_SERVER');PROD=pathlib.Path('/home/RTD_SERVER');OUT=ROOT/'docs/resource-audit/production-training-20261106'
snap=json.loads(pathlib.Path('/tmp/rtd-training-snapshot.json').read_text());cfg=json.loads((PROD/'rtd.config.json').read_text());host=cfg['resources']['host'];host='127.0.0.1' if host=='0.0.0.0' else '::1' if host=='::' else host
base='http://'+('['+host+']' if ':' in host else host)+':'+str(cfg['resources']['port']);opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
defs={};local=set()
for line in (ROOT/'docs/resource-audit/loading-chain/loader-definitions.tsv').read_text().splitlines():
 r=line.split('\t')
 if r[0] in ('B','G'):defs[r[1]]=dict(version=int(r[2]),path=r[3]+'/'+r[1]+'.unity3d')
 if r[0]=='L':local.add(r[1])
enemies={e['id']:e for r in snap['rows'] for e in r['enemies']};names=sorted({e['model'] for e in enemies.values()}-local);bundles={}
manifest=json.loads((PROD/'config/monster-recovery.json').read_text());expected={r['bundle']:r['sha256'] for r in manifest['bundles']}
for name in names:
 filename=name+'.unity3d';definition=defs.get(name);row=dict(bundle=filename,definition=definition)
 if not definition:row['status']='missing_client_download_definition';bundles[name]=row;continue
 candidates=[PROD/'resources/bundles'/filename,PROD/'resources/reconstructed/events/bundles'/filename,PROD/'resources/reconstructed/monsters/bundles'/filename];file=next((p for p in candidates if p.is_file()),None)
 if file is None:row['status']='missing_production_file';bundles[name]=row;continue
 data=file.read_bytes();sha=hashlib.sha256(data).hexdigest();row.update(sha256=sha,source=file.relative_to(PROD).as_posix(),manifest_sha256_match=sha==expected.get(filename) if filename in expected else None)
 try:
  with opener.open(base+'/'+definition['path'],timeout=20) as response:served=response.read();row['http_status']=response.status
  row['http_sha256_match']=hashlib.sha256(served).hexdigest()==sha
 except Exception as exc:row['status']='http_failed';row['error_type']=type(exc).__name__;bundles[name]=row;continue
 env=UnityPy.load(data);exports=[];roots=[]
 row['texture_names']=sorted({obj.read().m_Name for obj in env.objects if obj.type.name=='Texture2D'})
 row['expected_textures']=sorted({e['texture'] for e in enemies.values() if e['model']==name and e.get('texture') not in ('', 'na','0',None)})
 row['named_texture_misses']=sorted(set(row['expected_textures'])-set(row['texture_names']))
 for obj in env.objects:
  if obj.type.name=='AssetBundle':
   for key,entry in obj.read().m_Container:
    ptr=entry.asset
    if key.lower() in ('ast_'+name.lower(),name.lower()):
     exports.append(dict(name=key,type=ptr.type.name,path_id=ptr.path_id));roots.append(ptr.deref())
 issues=[];seen=set();types=collections.Counter();queue=roots[:]
 while queue:
  obj=queue.pop();key=(id(obj.assets_file),obj.path_id)
  if key in seen:continue
  seen.add(key);types[obj.type.name]+=1
  if obj.type.name in ('Texture2D','Mesh','AnimationClip','MonoScript','TextAsset','AudioClip'):continue
  try:tree=obj.read_typetree()
  except Exception as exc:issues.append(dict(type=obj.type.name,path_id=obj.path_id,issue='typetree_unavailable'));continue
  def walk(v,path=''):
   if isinstance(v,dict):
    if 'm_FileID' in v and 'm_PathID' in v:
     pid=v['m_PathID'];fid=v['m_FileID']
     if not pid:return
     if not fid:
      target=obj.assets_file.objects.get(pid)
      if target is None:issues.append(dict(type=obj.type.name,path_id=obj.path_id,field=path,issue='missing_local_pointer',target=pid))
      else:queue.append(target)
     else:
      externals=obj.assets_file.externals
      external=externals[fid-1].path if 0<fid<=len(externals) else 'invalid_FileID'
      if 'unity default resources' not in external.lower() and 'unity_builtin_extra' not in external.lower():issues.append(dict(type=obj.type.name,path_id=obj.path_id,field=path,issue='external_pointer_requires_resolution',external=external))
    else:
     for k,value in v.items():walk(value,path+'.'+str(k))
   elif isinstance(v,(list,tuple)):
    for i,value in enumerate(v):walk(value,path+'['+str(i)+']')
  walk(tree)
 row.update(exports=exports,reachable_objects=len(seen),reachable_types=dict(types),dependency_issues=issues,status='verified' if roots and row['http_sha256_match'] and not issues else 'review_required');bundles[name]=row
 print(name,row['status'],len(issues),flush=True)
result=dict(revision=snap['revision'],quests=[dict(quest_id=r['quest']['id'],name=r['quest']['name'],open=r['open'],blocked=r['blocked'],map=r['quest']['map'],map_dimensions=[r['level']['width'],r['level']['height']],map_data_valid=len(bytes.fromhex(r['level']['map_data']))==r['level']['width']*r['level']['height'],enemies=[e['id'] for e in r['enemies']]) for r in snap['rows']],enemy_records=list(enemies.values()),bundles=bundles,local_models=sorted({e['model'] for e in enemies.values()}&local))
(OUT/'production-http-and-bundle-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('bundles',len(bundles),'statuses',dict(collections.Counter(r['status'] for r in bundles.values())))
