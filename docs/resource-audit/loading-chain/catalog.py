"""Fresh content inventory, including raw Unity serialized cache and APK Resources pointers."""
from pathlib import Path
import json,hashlib,zipfile,struct,csv,sys
import UnityPy
HERE=Path(__file__).parent;WS=HERE.parents[3]
sources=[];seen={};files={};objects={};bindings=[];exports=[];errors=[];coverage=[]
def serialized_header(head,size):
 if len(head)<20:return False
 meta,total,version,offset=struct.unpack('>4I',head[:16])
 return 5<=version<=30 and 0<meta<=size and 0<offset<=size and (total==size or version>=22)
def process(blob,origin,category):
 sha=hashlib.sha256(blob).hexdigest()
 if sha in seen:
  sources[seen[sha]]['origins'].append(dict(path=origin,category=category));return seen[sha]
 sid=len(sources);seen[sha]=sid;sources.append(dict(sha256=sha,size=len(blob),origins=[dict(path=origin,category=category)],files=[]))
 try:
  env=UnityPy.load(blob)
  fs={id(o.assets_file):o.assets_file for o in env.objects}
  for i,sf in enumerate(fs.values()):
   fid=f'{sid}:{i}';sources[sid]['files'].append(fid)
   files[fid]=dict(source=sid,name=sf.name,externals=[e.path for e in sf.externals],objects={})
   for o in sf.objects.values():
    oid=f'{fid}:{o.path_id}';name=''
    try:name=o.peek_name() or ''
    except Exception as e:errors.append(dict(source=sid,path_id=o.path_id,stage='name',error=str(e)[:150]))
    objects[oid]=dict(file=fid,path_id=o.path_id,type=o.type.name,name=name)
    files[fid]['objects'][str(o.path_id)]=oid
    if o.type.name=='ResourceManager':
     try:
      for path,ptr in o.read_typetree()['m_Container']:bindings.append(dict(path=path,file=fid,pointer=ptr))
     except Exception as e:errors.append(dict(source=sid,stage='ResourceManager',error=str(e)[:150]))
   # AssetBundle exports contain exact loadable names, distinct from object names.
   for o in sf.objects.values():
    if o.type.name=='AssetBundle':
     try:
      tree=o.read_typetree()
      for name,info in tree['m_Container']:exports.append(dict(name=name,file=fid,pointer=info['asset']))
     except Exception as e:errors.append(dict(source=sid,stage='AssetBundle',error=str(e)[:150]))
  if not fs:coverage.append(dict(origin=origin,status='non-object payload',size=len(blob)))
 except Exception as e:errors.append(dict(source=sid,stage='parse',error=str(e)[:180]))
 return sid
roots=[WS/'RTD_SERVER/resources',WS/'RTD_CLIENT/resources',WS/'RTD_CLIENT/inputs',WS/'RTD_CLIENT/build',WS/'RTD_CLIENT/dist']
apks=[]
for root in roots:
 for f in root.rglob('*'):
  if not f.is_file():continue
  if f.suffix.lower()=='.apk':apks.append(f);continue
  size=f.stat().st_size
  with f.open('rb') as stream:head=stream.read(48)
  iscache=f.name.startswith('CustomAssetBundle')
  if iscache or head.startswith((b'UnityFS',b'UnityRaw',b'UnityWeb')) or serialized_header(head,size):
   origin=str(f.relative_to(WS));category='preload90' if 'RTD_CLIENT/resources/UnityCache/' in origin else 'reconstructed' if '/reconstructed/' in origin else 'local_resource'
   sid=process(f.read_bytes(),origin,category);coverage.append(dict(origin=origin,status='parsed',source=sid,size=size))
for apk in sorted(set(apks)):
 with zipfile.ZipFile(apk) as z:
  for entry in z.infolist():
   n=entry.filename
   if not n.startswith('assets/') or n.endswith('/'):continue
   # Inventory every APK asset; only Unity-compatible content is parsed.
   with z.open(entry) as stream:head=stream.read(48)
   origin=str(apk.relative_to(WS))+':'+n
   if n.startswith('assets/rtd-cache/') and '/CustomAssetBundle' in n:category='apk_preload'
   elif n.startswith('assets/bin/Data/') and '/Managed/' not in n:category='apk_data'
   else:category='apk_other'
   if category=='apk_preload' or head.startswith((b'UnityFS',b'UnityRaw',b'UnityWeb')) or serialized_header(head,entry.file_size):
    sid=process(z.read(entry),origin,category);coverage.append(dict(origin=origin,status='parsed',source=sid,size=entry.file_size))
   else:coverage.append(dict(origin=origin,status='not Unity object data',size=entry.file_size))
result=dict(sources=sources,files=files,objects=objects,bindings=bindings,exports=exports,errors=errors,coverage=coverage)
(HERE/'catalog.json').write_text(json.dumps(result,ensure_ascii=False))
def csvout(name,header,rows):
 with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(header);w.writerows(rows)
csvout('全部资源对象.csv',['对象键','名称','类型','PathID','序列化文件','来源'],([oid,o['name'],o['type'],o['path_id'],files[o['file']]['name'],'；'.join(a['path'] for a in sources[files[o['file']]['source']]['origins'])] for oid,o in objects.items()))
preload=[(sid,s,o) for sid,s in enumerate(sources) for o in s['origins'] if o['category']=='preload90']
csvout('90个预载文件核对.csv',['路径','大小','SHA256','对象数','同内容APK位置'],([o['path'],s['size'],s['sha256'],sum(len(files[f]['objects']) for f in s['files']),'；'.join(a['path'] for a in s['origins'] if a['category']=='apk_preload')] for sid,s,o in preload))
csvout('APK资源覆盖.csv',['来源条目','大小','状态','内容编号'],([r['origin'],r['size'],r['status'],r.get('source','')] for r in coverage if '.apk:' in r['origin']))
print(json.dumps(dict(sources=len(sources),files=len(files),objects=len(objects),bindings=len(bindings),exports=len(exports),preloads=len(preload),errors=len(errors)),ensure_ascii=False),flush=True)
assert len(preload)==90, f'Expected 90 preload files, found {len(preload)}'
