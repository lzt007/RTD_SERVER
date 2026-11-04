from pathlib import Path
import json,re,csv,html,collections
import UnityPy
P=Path('/home/workspace/RTD_SERVER/docs/resource-audit/new-backup');B=Path('/home/workspace/resources/unpacked');x=json.loads((P/'新备份资源索引.json').read_text());sources=x['sources'];assets=x['assets'];(P/'images').mkdir(exist_ok=True);gallery=[];species=collections.defaultdict(set)
for a in assets:
 if a['type']=='GameObject' and a['name'].startswith('ast_'):
  m=re.search(r'ms\d+_([^_]+)',a['name'])
  if m:species[m[1]].add(a['name'])
selected=[a for a in assets if a['type']=='Texture2D' and re.search(r'ms\d+_(sco|crab|bird|wolf)_',a['name'])];seen=set();imageerrors=[]
for a in selected:
 if a['name'] in seen:continue
 seen.add(a['name']);src=sources[a['source']]['path']
 try:
  env=UnityPy.load(str(B/src));o=next(o for o in env.objects if o.path_id==a['path_id'] and o.type.name=='Texture2D');im=o.read().image;im.thumbnail((512,512));file='images/'+a['name']+'.png';im.save(P/file);gallery.append((a['name'],src,file))
 except Exception as e:imageerrors.append([a['name'],str(e)])
rows=list(csv.DictReader((P/'旧缺口补齐对照.csv').open(encoding='utf-8-sig')))
for r in rows:
 m=re.search(r'ms\d+_([^_]+)',r['原引用']);fam=m[1] if m else '';r['已有同族候选']='；'.join(sorted(species[fam]))
with (P/'复用决策表.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
page='<meta charset="utf-8"><style>body{font:14px sans-serif}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}img{width:200px;background:#ddd}</style><h1>新备份物种素材预览</h1><p>原包解出的UV贴图，不是3D渲染。新备份多数为Unity5.3.5p8资源，不能把同名命中当作已兼容旧客户端。</p><table><tr><th>资源</th><th>来源包</th><th>贴图预览</th></tr>'
for name,src,file in gallery:page+='<tr><td>'+html.escape(name)+'</td><td>'+html.escape(src)+'</td><td><a href="'+file+'"><img src="'+file+'"></a></td></tr>'
(P/'新增物种预览.html').write_text(page+'</table>')
report=['# 群友数据资源调查','', '两个APK未解包、未读取程序集及Manifest，未用于版本匹配。归档已排除APK解压至/home/workspace/resources/unpacked。','',f'资源包915个；形成对象索引{len(assets)}条；64个Icon/AI图集包在对象解析阶段报错，已记录，不当作资源缺失。assets/assets下的敌人、地图及角色包本轮没有解析报错。', '', '## 可利用资源','', '原218项缺口中，83项命中同名同类型对象：模型59项、贴图24项；剩余135项未同名命中，不代表没有可复用替代。复用决策表.csv保留所有218项并补上同族候选。','', '本批确认存在蝎子sco四属性_02变体、螃蟹crab Lv1/Lv2四属性、鸟bird Lv1/Lv2四属性，以及330/550前缀狼变体。蝎子ms01_sco_lv1_un这个精确名称仍未命中，但已有真实蝎子模型和贴图可评估复用。','', '种类模型数量（按ast_对象原名去重）：']+[f'- {fam}：{len(names)}，例如 '+ '、'.join(sorted(names)[:4]) for fam,names in sorted(species.items())]+['','## 数据版本线索','', '- 主要资源包自身的Unity引擎版本为5.3.5p8；少数历史图集带4.6.5p3/4.3.4f1标记。Unity版本不是游戏APK版本。','- Icon/AI目录包含多代V1028至V1036及V5700、V5800……V6900、V7000资源目录，证明是跨代资源集合，不能视为单一版本快照。V7000提示7.0代资源（推测），不能由此确定7.0.1或更精确APK版本。','- quest包含4124个msgpack关卡响应，归档中部分关卡条目时间为2017-03-16。该时间只能作为归档记录线索，不能独立证明APK版本；响应可能含会话字段，未将其原文写入报告。','- 未发现足以唯一绑定APK版本的已核实数据字段；结论是“包含V7000代资源、主要由Unity5.3.5p8构建的混合历史数据”，不能认定两个附带APK之一与之匹配。','','## 兼容性与后续决策','', '当前旧客户端原始资源格式与这批Unity5资源存在代际差异。83项同名对象只是素材补齐证据，不是已验证能原包直载。贴图可以先导出作复用/重绘底稿；模型需进一步核对骨骼、材质、动作和目标Unity格式，必要时转换/重打包。本次没有覆盖主表、安装资源或改变关卡替代配置。','','文件：旧缺口补齐对照.csv、复用决策表.csv、新增物种预览.html、新备份资源索引.json。']
(P/'调查说明.md').write_text('\n'.join(report)+'\n');(P/'图像提取记录.json').write_text(json.dumps(dict(images=gallery,errors=imageerrors),ensure_ascii=False,indent=2))
print(dict(previews=len(gallery),image_errors=len(imageerrors),species=len(species),matched=x['gap_hits']))
