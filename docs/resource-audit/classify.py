from pathlib import Path
import json,re,csv,html
from collections import defaultdict
p=Path(__file__).parent;assets=json.loads((p.parents[1]/'config/event-reconstruction-assets.json').read_text());manifest=json.loads((p/'image-manifest.json').read_text())['textures'];rows=list(csv.DictReader((p/'缺口说明表.csv').open(encoding='utf-8-sig')))
labels={'bear':'熊','wolf':'狼','sla':'史莱姆','dra':'龙（名称推测）','sco':'蝎类（名称推测）','squ':'squ 类（具体种类待确认）','fish':'鱼类','golem':'石像/魔像','bird':'鸟类','crab':'蟹类','fugu':'河豚类','mind':'mind 类','four':'four 类','fly':'fly 类','oct':'章鱼类','death':'death 类','legend':'legend 类','tatu':'tatu 类'}
families=defaultdict(lambda:dict(models=set(),textures=set(),missing=set(),quests=set()))
for r in rows:
 m=re.match(r'ms\d+_([^_]+)(?:_|$)',r['原始引用资源名'])
 if m:families[m[1]]['missing'].add(r['原始引用资源名']);families[m[1]]['quests'].add(r['引用关卡与怪物'])
for k in ['models','textures']:
 for n in assets[k]:
  m=re.match(r'(?:ast_)?ms\d+_([^_]+)(?:_|$)',n)
  if m and m[1] in families:families[m[1]][k].add(n)
def pics(names):
 return '<br>'.join(f'{n}<br><a href="{manifest[n]["file"]}"><img src="{manifest[n]["file"]}" width="160"></a>' for n in sorted(names) if n in manifest) or '无已提取图像'
def levels(names):return '、'.join(sorted(set((re.search(r'_lv(\d+)',n)[1] if re.search(r'_lv(\d+)',n) else '非lv变体') for n in names))) or '无'
body=[];md=['# 按种类、等级、属性整理的资源图鉴','','范围沿用可开放主线及完成修复活动的原始引用缺口。存在性按原始分类清单判断，预览为原始解包贴图（UV图集），不是3D模型渲染。lv表示等级变体；是否只缩放或改变网格未经模型比较，不作确定结论。属性名表示配色变体，不等于可以安全跨模型互换。','','## 种类与等级矩阵','','|种类|至少一种原始模型|已有模型等级|已有贴图等级|缺失引用数|已有贴图原名|','|---|---|---|---|---|---|']
for f,d in sorted(families.items()):
 vals=[labels.get(f,f)+' / '+f,'有' if d['models'] else '无',levels(d['models']),levels(d['textures']),str(len(d['missing'])),'；'.join(sorted(d['models'])) or '无']
 md.append('|'+ '|'.join(vals[:-1]+['；'.join(sorted(d['textures'])) or '无'])+'|')
 body.append('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in vals)+'<td>'+pics(d['textures'])+'</td><td>'+ '<br>'.join(sorted(d['missing']))+'</td></tr>')
attr=[]
for a,color in [('water','水属性；蓝/青色方向（命名推测，具体以各族图像为准）'),('holy','光属性；黄/金色方向（命名推测，具体以图像为准）'),('fire','火属性；红/橙色方向（命名推测，具体以图像为准）'),('dark','暗属性；紫/深色方向（命名推测，具体以图像为准）'),('gold','金色外观变体；不直接等同光属性')]:
 ns={n for d in families.values() for n in d['textures'] if n.endswith('_'+a)}
 attr.append('<tr><td>'+a+'</td><td>'+color+'</td><td>'+('存在' if ns else '未发现')+'</td><td>'+pics(ns)+'</td></tr>')
intro='先按怪物种类判断可否复用，再选等级变体和属性配色。所有图片为解包贴图图集，可点击放大；不是怪物3D渲染。覆盖原缺口表全部209项直接引用，含非lv特殊变体及Boss，按名称族归类；不含动作、效果和书本等间接依赖缺口。属性颜色方向暂按名称推测，图像为实际证据。'
result='<meta charset="utf-8"><title>怪物资源分类图鉴</title><style>body{font-family:sans-serif}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:8px;vertical-align:top}img{background:#ddd}</style><h1>怪物资源分类图鉴</h1><p>'+intro+'</p><h2>种类 × 等级</h2><table><tr>'+''.join('<th>'+v+'</th>' for v in ['种类','至少一种模型','模型等级','贴图等级','缺失引用数','现存模型名','现存贴图与外观','本类全部缺失引用'])+'</tr>'+''.join(body)+'</table><h2>属性 × 配色</h2><table><tr><th>属性后缀</th><th>配色说明</th><th>是否存在</th><th>不同种类的实际贴图</th></tr>'+''.join(attr)+'</table><p>复用顺序建议：同种类同属性且有配套模型/贴图 → 同种类异属性重新配色 → 无同种类模型则补模或明确采用异类占位。模型与贴图应配套核对UV；等级不能仅凭名称视为大小不同。</p>'
(p/'怪物资源分类图鉴.html').write_text(result);(p/'怪物资源分类矩阵.md').write_text('\n'.join(md)+'\n')
print({f:dict(models=sorted(d['models']),textures=len(d['textures']),missing=len(d['missing'])) for f,d in families.items()})
