"""Generate illustrated, searchable per-gap report from installed compatibility bytes."""
import csv,html,json,re,hashlib
from pathlib import Path
from collections import Counter
import UnityPy
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'docs/resource-audit';OUT=BASE/'new-backup';IMG=OUT/'repair-images';IMG.mkdir(exist_ok=True)
results=json.loads((OUT/'本次逐项修复结果.json').read_text())
audit={r['requested']:r for r in json.loads((OUT/'本次修复候选审计.json').read_text())['items']}
old={r['原始引用资源名'].removeprefix('ast_'):r for r in csv.DictReader((BASE/'缺口说明表.csv').open(encoding='utf-8-sig'))}
policy={r['model']:r for r in json.loads((ROOT/'config/monster-recovery.json').read_text())['bundles']}
cache={};proof=[]
proof_file=OUT/'修补报告图像证据.json'
if proof_file.exists():
 for entry in json.loads(proof_file.read_text()):
  row=policy.get(entry['model'])
  if row and row['sha256']==entry['sha256'] and all((OUT/image).exists() for _,image in entry['images']):
   path=ROOT/'resources/reconstructed/monsters/bundles'/row['bundle']
   if hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']:
    cache[entry['model']]=[tuple(v) for v in entry['images']];proof.append(entry)
def pictures(model):
 if model in cache:return cache[model]
 row=policy.get(model);found=[]
 if row:
  path=ROOT/'resources/reconstructed/monsters/bundles'/row['bundle']
  assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
  for obj in UnityPy.load(str(path)).objects:
   if obj.type.name!='Texture2D':continue
   data=obj.read();name=data.m_Name;filename=re.sub(r'[^\w.-]','_',model+'__'+name)+'.png'
   image=data.image.convert('RGBA');image.thumbnail((256,256));image.save(IMG/filename)
   found.append((name,'repair-images/'+filename))
  proof.append(dict(model=model,sha256=row['sha256'],images=found))
 cache[model]=found;return found
rows=[]
for item in results['items']:
 name=item['original'];short=name.removeprefix('ast_');a=audit[name];prior=old.get(short,{})
 models=item['models'];p=next((policy[m] for m in models if m in policy),{})
 images=[]
 for model in models:
  available=pictures(model)
  images.extend([v for v in available if v[0]==name] if item['category']=='贴图' else available)
 images=list(dict.fromkeys(images))
 if not images:
  for file in sorted((BASE/'images').glob(short+'*.png'))[:4]:images.append((file.stem,'../images/'+file.name))
 if not images:
  for previous in re.findall(r'ms\d+_[A-Za-z0-9_]+',prior.get('当前有效引用','')):
   for file in sorted((BASE/'images').glob(previous.removesuffix('_zako')+'*.png'))[:4]:images.append((file.stem+'（此前替代）','../images/'+file.name))
 images=list(dict.fromkeys(images))
 reason='已安装兼容包；尚待实机验收' if '已安装' in item['status'] else '新备份未找到同族素材，沿用此前处理' if '无同族' in item['status'] else '原优先目录已有资源，本次未覆盖' if '原优先' in item['status'] else '同族两源缺原动作所需胸颈及四肢骨链，需重新绑定骨架和权重；保留原方案'
 rows.append(dict(类别=item['category'],原始引用=name,状态=item['status'],恢复方式=('同名素材' if item['material_match']=='找到' else '同族素材（推测）') if '已安装' in item['status'] else '保留原处理',此前替代=prior.get('当前有效引用','见昨日加载链报告'),本次来源模型=p.get('source_model',''),本次来源包=p.get('source',''),涉及关卡与怪物=a['quests'],说明=reason,图片=images))
with (OUT/'资源修补前后对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=[k for k in rows[0] if k!='图片']);w.writeheader();w.writerows({k:v for k,v in r.items() if k!='图片'} for r in rows)
intro='统计口径为昨天加载链复核后的218项模型／贴图缺口（区别于更早的209项图像表）。已修补仅指本地安装，未部署到运行服务，未完成实机验收。图像来自实际安装包解码的UV贴图缩略图，不是3D渲染；未修补项如有图片，展示此前替代资源。既有通关闪退仍未解决。'
md=['# 资源修补前后对照报告','',intro,'','|状态|数量|','|---|---:|']+[f'|{s}|{n}|' for s,n in results['summary']['status'].items()]
body=[]
for title,predicate in [('仍未修补',lambda r:'无同族' in r['状态'] or '待解决' in r['状态']),('已修补',lambda r:'已安装' in r['状态']),('已有资源保留',lambda r:'原优先' in r['状态'])]:
 subset=[r for r in rows if predicate(r)];md+=['',f'## {title}（{len(subset)}项）','']
 body.append(f'<h2>{title}（{len(subset)}项）</h2>')
 for r in subset:
  md += [f"### {r['类别']}：{r['原始引用']}",'']+[f"- {k}：{v}" for k,v in r.items() if k not in ('图片','类别','原始引用')]+['']+[f'![{n}]({p})' for n,p in r['图片']]+['']
  fields=''.join(f'<dt>{html.escape(k)}</dt><dd>{html.escape(str(v))}</dd>' for k,v in r.items() if k not in ('图片',))
  pictures_html=''.join(f'<figure><a href="{p}"><img loading="lazy" src="{p}" alt="{html.escape(n)}"></a><figcaption>{html.escape(n)}</figcaption></figure>' for n,p in r['图片'])
  body.append(f'<article data-status="{html.escape(r["状态"])}"><h3>{html.escape(r["原始引用"])}</h3><dl>{fields}</dl><div class="images">{pictures_html}</div></article>')
(OUT/'资源修补前后对照报告.md').write_text('\n'.join(md)+'\n')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>资源修补前后对照报告</title><style>body{font:16px system-ui;max-width:1400px;margin:30px auto;padding:16px;background:#f5f6f8;color:#202735}header{position:sticky;top:0;background:#fff;padding:16px;border-bottom:2px solid #345}article{background:white;padding:20px;margin:16px 0;border-radius:10px}dt{font-weight:bold}dd{margin:4px 0 12px;overflow-wrap:anywhere;white-space:pre-wrap}.images{display:flex;flex-wrap:wrap}figure{margin:8px}img{max-width:180px;max-height:180px;background:#ddd}figcaption{max-width:200px;overflow-wrap:anywhere;font-size:12px}input,select{padding:10px;margin:4px}h3{overflow-wrap:anywhere}</style><h1>资源修补前后对照报告</h1><p>INTRO</p><header><strong>已修补194项 · 未修补23项 · 已有原资源保留1项</strong><br><input id="q" placeholder="搜索模型、关卡、怪物或替代来源"><select id="status"><option value="">全部状态</option><option>已安装</option><option>无同族</option><option>待解决</option><option>原优先</option></select><span id="count"></span></header>BODY<script>function filter(){let n=0;document.querySelectorAll('article').forEach(e=>{let ok=e.textContent.toLowerCase().includes(q.value.toLowerCase())&&e.dataset.status.includes(statusSelect.value);e.hidden=!ok;if(ok)n++});document.getElementById('count').textContent='显示 '+n+' 项'}const q=document.getElementById('q'),statusSelect=document.getElementById('status');q.oninput=filter;statusSelect.onchange=filter;filter()</script></html>'''
(OUT/'资源修补前后对照报告.html').write_text(page.replace('INTRO',html.escape(intro)).replace('BODY',''.join(body)))
(OUT/'修补报告图像证据.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
assert len(rows)==218
print(json.dumps(dict(rows=len(rows),status=dict(Counter(r['状态'] for r in rows)),illustrated=sum(bool(r['图片']) for r in rows),bundles=len(proof)),ensure_ascii=False))
