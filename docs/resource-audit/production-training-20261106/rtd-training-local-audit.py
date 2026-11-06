import pathlib,json,hashlib,zipfile,collections
import UnityPy
ROOT=pathlib.Path('/home/workspace/RTD_SERVER');WS=ROOT.parent;OUT=ROOT/'docs/resource-audit/production-training-20261106';P=ROOT/'docs/resource-audit/loading-chain'
d=json.loads((P/'catalog.json').read_text());results=json.loads((OUT/'results.json').read_text());f=d['files'];o=d['objects'];sources=d['sources'];ids=set(results['reachable']);sids={f[o[i]['file']]['source'] for i in ids};checked=[]
for sid in sorted(sids):
 s=sources[sid];origins=sorted(s['origins'],key=lambda a:'/inputs/original/' not in a['path']);match=[]
 for origin in origins:
  path=origin['path']
  try:
   if '.apk:' in path:
    apk,member=path.split(':',1)
    with zipfile.ZipFile(WS/apk) as z:data=z.read(member)
   else:data=(WS/path).read_bytes()
   sha=hashlib.sha256(data).hexdigest()
   if sha==s['sha256']:match.append(path)
  except (OSError,KeyError,zipfile.BadZipFile):continue
 checked.append(dict(source_id=sid,expected_sha256=s['sha256'],verified_origins=match,status='verified' if match else 'stale_source'))
apk=WS/'RTD_CLIENT/inputs/original/game.apk';scenes=[]
with zipfile.ZipFile(apk) as z:
 for name in z.namelist():
  if name.endswith(('globalgamemanagers','mainData')):
   env=UnityPy.load(z.read(name))
   for obj in env.objects:
    if obj.type.name=='BuildSettings':
     tree=obj.read_typetree();scenes.append(dict(member=name,levels=tree.get('levels'),unity_version=tree.get('m_Version')))
result=dict(source_hash_verification=checked,recursive_issues=results['issues'],local_requirements=[r for r in results['requirements'] if r['scope']=='当前' and r['path'].startswith(('AnimationData/','Prefab/Enemies/','Prefab/ParticleEffects/'))],apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest(),build_settings=scenes)
(OUT/'local-source-and-scene-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('verified source hashes',sum(r['status']=='verified' for r in checked),'/',len(checked));print('scene data',str(scenes)[:1600])
