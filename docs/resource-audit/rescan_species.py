"""Independent raw resource scan; no prior asset manifests used."""
from pathlib import Path
import json,zipfile,hashlib,re
import UnityPy
p=Path(__file__).parent;workspace=p.parents[2];seen={};sources=[];objects=[];containers=[];errors=[];inventory=[];resource_entries=[]
pattern=re.compile(r'bear|wolf|crab|bird|fugu|tatu|golem|(?:^|[_/])sco|(?:^|[_/])fish|(?:^|[_/])fly|(?:^|[_/])oct|boar|pig|hog|crow|eagle|hawk|chicken|raven|scorp|torto|turtle',re.I)
def scan(data,origin):
 blob=Path(data).read_bytes() if isinstance(data,Path) else data;sha=hashlib.sha256(blob).hexdigest()
 if sha in seen:sources[seen[sha]]['duplicates'].append(origin);return
 sid=len(sources);seen[sha]=sid;sources.append(dict(origin=origin,sha256=sha,duplicates=[],objects=0))
 try:env=UnityPy.load(blob)
 except Exception as e:errors.append([origin,str(e)[:200]]);return
 sources[sid]['objects']=len(env.objects)
 for o in env.objects:
  try:n=o.peek_name() or ''
  except Exception:n=''
  if n and o.type.name in ('GameObject','Mesh','Texture2D','Material','AnimationClip'):
   inventory.append(dict(name=n,type=o.type.name,path_id=o.path_id,source=sid))
  if o.type.name=='ResourceManager':
   try:
    for key,ptr in o.read_typetree()['m_Container']:
     resource_entries.append(dict(path=key,pointer=ptr,source=sid))
   except Exception as exc:errors.append([origin+':ResourceManager',str(exc)[:150]])
  if pattern.search(n):
   row=dict(name=n,type=o.type.name,path_id=o.path_id,source=sid)
   if o.type.name=='GameObject':
    try:row['components']=[c[1].type.name for c in o.read().m_Component]
    except:pass
   objects.append(row)
 for name,obj in env.container.items():
  if pattern.search(name):containers.append(dict(name=name,type=obj.type.name,path_id=obj.path_id,source=sid))
roots=[workspace/'RTD_SERVER/resources',workspace/'RTD_CLIENT/resources',workspace/'RTD_CLIENT/inputs',workspace/'RTD_CLIENT/apks',workspace/'RTD_CLIENT/build',workspace/'RTD_CLIENT/dist']
# Discover bundles by file signature, not by extension or former manifest.
archives=[]
for root in roots:
 if not root.exists():continue
 for f in root.rglob('*'):
  if not f.is_file():continue
  if f.suffix.lower()=='.apk':archives.append(f);continue
  try:
   with f.open('rb') as stream:head=stream.read(16)
  except OSError:continue
  if f.name.startswith('CustomAssetBundle') or head.startswith((b'UnityFS',b'UnityRaw',b'UnityWeb')) or f.name in ('mainData','resources.assets') or f.name.startswith('sharedassets') or (f.name.startswith('level') and f.name[5:].isdigit()):scan(f,str(f.relative_to(workspace)))
for apk in archives:
 with zipfile.ZipFile(apk) as z:
  for n in z.namelist():
   if (n.startswith('assets/bin/Data/') and '/Managed/' not in n and not n.endswith('/')) or ('assets/rtd-cache/' in n and 'CustomAssetBundle' in n):
    scan(z.read(n),str(apk.relative_to(workspace))+':'+n)
result=dict(roots=[str(r.relative_to(workspace)) for r in roots],sources=sources,objects=objects,containers=containers,errors=errors,inventory=inventory,resource_entries=resource_entries)
(p/'独立资源重扫证据.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
lines=['# 敌人物种独立重扫','','不读取旧资源存在性清单。按文件签名发现Unity资源包，并检查APK内Data资源、缓存、角色包与重建目录；按内容哈希去重。模型、贴图、材质、网格、动画分别统计；同名动画不能证明物种模型存在。',f'扫描{len(sources)}份独立内容，命中物种关键词对象{len(objects)}个，容器引用{len(containers)}个，解析异常{len(errors)}项。','','|名称|对象类型|来源|PathID|','|---|---|---|---|']
for r in sorted(objects,key=lambda r:(r['name'],r['type'])):lines.append('|'+ '|'.join([r['name'],r['type'],sources[r['source']]['origin'],str(r['path_id'])])+'|')
(p/'敌人物种独立重扫.md').write_text('\n'.join(lines)+'\n')
print(dict(sources=len(sources),objects=len(objects),containers=len(containers),errors=len(errors)))
