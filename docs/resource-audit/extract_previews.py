"""Extract actual replacement texture atlases and build a self-contained review table."""
from pathlib import Path
import csv,json,zipfile,hashlib,html,re
import UnityPy
from PIL import Image
root=Path(__file__).resolve().parents[2];out=Path(__file__).parent;images=out/'images';images.mkdir(exist_ok=True)
rows=list(csv.DictReader((out/'缺口说明表.csv').open(encoding='utf-8-sig')));wanted=set()
for r in rows:
 for n in r['当前有效引用'].split('；'):
  if n and n!='na':wanted.add(n.lower().removeprefix('ast_').removesuffix('_zako'))
wanted.update(n for n in json.loads((root/'config/event-reconstruction-assets.json').read_text())['textures'] if re.match(r'ms\d+_[^_]+_',n))
records={};errors=[]
def scan(data,source):
 try:env=UnityPy.load(data)
 except Exception as exc:errors.append([source,str(exc)[:150]]);return
 for o in env.objects:
  if o.type.name!='Texture2D':continue
  name=(o.peek_name() or '').lower()
  if not any(name==n or name.startswith(n+'_') for n in wanted):continue
  if name in records:continue
  try:
   d=o.read()
   if d.m_TextureFormat==2:
    import struct
    pixels=struct.unpack('<'+str(d.m_Width*d.m_Height)+'H',d.image_data[:d.m_Width*d.m_Height*2])
    im=Image.frombytes('RGBA',(d.m_Width,d.m_Height),bytes(((p>>s)&15)*17 for p in pixels for s in (12,8,4,0))).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
   else:im=d.image
   filename=re.sub('[^a-zA-Z0-9_-]','_',name)+'.png';im.save(images/filename)
   records[name]=dict(file='images/'+filename,source=source,path_id=o.path_id,width=im.width,height=im.height)
  except Exception as exc:errors.append([source+':'+name,str(exc)[:150]])
paths=sorted(set((root/'resources/bundles').glob('*.unity3d'))|set((root/'resources/cache').rglob('CustomAssetBundle*')))
for p in paths:scan(str(p),str(p.relative_to(root)))
apk=root.parent/'RTD_CLIENT/inputs/original/game.apk'
with zipfile.ZipFile(apk) as z:
 for n in z.namelist():
  if n.startswith('assets/bin/Data/') and '/Managed/' not in n and not n.endswith('/'):
   scan(z.read(n),'original/game.apk:'+n)
matched=0;md=[];body=[]
for r in rows:
 current=[n.lower().removeprefix('ast_').removesuffix('_zako') for n in r['当前有效引用'].split('；') if n and n!='na']
 names=sorted(n for n in records if any(n==c or n.startswith(c+'_') for c in current))
 preview='<br>'.join(f'{html.escape(n)}<br><a href="{records[n]["file"]}"><img loading="lazy" src="{records[n]["file"]}" width="180"></a>' for n in names) or '未提取到对应贴图，不能用其他候选冒充当前替代图'
 if names:matched+=1
 vals=[r['类型'],r['原始引用资源名'],r['当前有效引用'],preview,r['引用关卡与怪物'],r['近名替换候选（现有资源，按优先级）']]
 body.append('<tr>'+''.join('<td>'+(v if i==3 else html.escape(v))+'</td>' for i,v in enumerate(vals))+'</tr>')
 md.append('|'+ '|'.join((v.replace('|','/') if i!=3 else '<br>'.join(f'{n}<br>![{n}]({records[n]["file"]})' for n in names) or '未提取到对应贴图') for i,v in enumerate(vals))+'|')
intro=f'共{len(rows)}项，{matched}项附实际当前替代资源贴图。图片为解包后的UV展开贴图，不是3D怪物渲染；模型条目按当前模型名前缀关联贴图，具体材质绑定仍待核实。点击图片查看原尺寸。'
(out/'缺口图像说明表.html').write_text('<meta charset="utf-8"><title>缺口图像说明表</title><style>body{font-family:sans-serif}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:8px;vertical-align:top}img{background:#ddd;image-rendering:auto}</style><h1>缺口图像说明表</h1><p>'+intro+'</p><table><tr>'+''.join('<th>'+x+'</th>' for x in ['类型','原始引用','当前替代引用','当前替代资源图像（解包贴图）','关卡与怪物','其他近名候选'])+'</tr>'+''.join(body)+'</table>')
(out/'缺口图像说明表.md').write_text('# 缺口图像说明表\n\n'+intro+'\n\n|类型|原始引用|当前替代引用|当前替代资源图像（解包贴图）|关卡与怪物|其他近名候选|\n|---|---|---|---|---|---|\n'+'\n'.join(md)+'\n')
(out/'image-manifest.json').write_text(json.dumps(dict(textures=records,errors=errors,rows=len(rows),rows_with_images=matched),ensure_ascii=False,indent=2))
print({'textures':len(records),'rows_with_images':matched,'rows':len(rows),'errors':len(errors)})
