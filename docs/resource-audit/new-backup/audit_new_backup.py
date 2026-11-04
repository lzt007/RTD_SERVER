from pathlib import Path
import json,csv,hashlib,collections,re
import UnityPy
base=Path('/home/workspace/resources/unpacked');out=Path('/home/workspace/RTD_SERVER/docs/resource-audit/new-backup');out.mkdir(exist_ok=True)
old=json.load(open('/home/workspace/RTD_SERVER/docs/resource-audit/loading-chain/catalog.json'));oldhash={s['sha256'] for s in old['sources']};assets=[];sources=[];errors=[];versions=collections.Counter();hits=[]
for p in base.rglob('*'):
 if not p.is_file() or p.suffix.lower()=='.apk':continue
 blob=p.read_bytes()
 if not (p.suffix=='.unity3d' or blob.startswith((b'UnityFS',b'UnityWeb',b'UnityRaw'))):continue
 try:
  env=UnityPy.load(blob);sid=len(sources);sources.append(dict(path=str(p.relative_to(base)),sha256=hashlib.sha256(blob).hexdigest(),size=len(blob),objects=len(env.objects)))
  for o in env.objects:
   if hasattr(o.assets_file,'unity_version'):versions[str(o.assets_file.unity_version)]+=1
   name=o.peek_name() or ''
   if name and o.type.name in ('GameObject','Texture2D','Mesh','Material','AnimationClip'):
    assets.append(dict(source=sid,name=name,type=o.type.name,path_id=o.path_id))
 except Exception as exc:errors.append([str(p),str(exc)])
index=collections.defaultdict(list)
for a in assets:index[a['name'].lower(),a['type']].append(a)
missing=list(csv.DictReader(open('/home/workspace/RTD_SERVER/docs/resource-audit/loading-chain/决策缺口表.csv',encoding='utf-8-sig')))
rows=[]
for r in missing:
 typ='Texture2D' if r['类别']=='贴图' else 'GameObject';found=index.get((r['原始引用名'].lower(),typ),[])
 rows.append([r['类别'],r['原始引用名'],'找到' if found else '未找到','；'.join(sorted({sources[a['source']]['path'] for a in found})),r['使用关卡及怪物']])
with (out/'旧缺口补齐对照.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['类别','原引用','新备份是否命中','来源包','原使用关卡及怪物']);w.writerows(rows)
result=dict(sources=sources,assets=assets,errors=errors,unity_versions=dict(versions),old_gap_count=len(rows),gap_hits=sum(r[2]=='找到' for r in rows),new_content=sum(s['sha256'] not in oldhash for s in sources))
(out/'新备份资源索引.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print({k:v for k,v in result.items() if k not in ('sources','assets')},flush=True)
# Export exact requested scorpion textures using actual bitmap data.
from PIL import Image
for a in assets:
 if a['type']!='Texture2D' or not re.search(r'ms01_sco_lv[14]',a['name']):continue
 src=base/sources[a['source']]['path'];e=UnityPy.load(str(src));obj=next(o for o in e.objects if o.path_id==a['path_id'] and o.type.name=='Texture2D');d=obj.read()
 try:
  if d.m_TextureFormat==2:
   import struct
   px=struct.unpack('<'+str(d.m_Width*d.m_Height)+'H',d.image_data[:d.m_Width*d.m_Height*2]);im=Image.frombytes('RGBA',(d.m_Width,d.m_Height),bytes(((v>>sh)&15)*17 for v in px for sh in (12,8,4,0))).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
  else:im=d.image
  im.save(out/(a['name']+'.png'))
 except Exception as exc:print('image error',a['name'],str(exc))
