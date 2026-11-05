from pathlib import Path
from collections import defaultdict,Counter
from functools import lru_cache
import json,csv,html,zipfile,struct,re,hashlib
import UnityPy
from PIL import Image
P=Path(__file__).parent;WS=P.parents[3];D=json.loads((P/'catalog.json').read_text());R=json.loads((P/'results.json').read_text());O=D['objects'];F=D['files'];S=D['sources'];G=json.loads((P/'graph.json').read_text());images=P/'images';images.mkdir(exist_ok=True)
def writecsv(name,header,rows):
 with (P/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f,lineterminator="\n");w.writerow(header);w.writerows(rows)
@lru_cache(maxsize=10)
def sfload(sid):
 path=S[sid]['origins'][0]['path']
 if '.apk:' in path:
  apk,n=path.split(':',1)
  with zipfile.ZipFile(WS/apk) as z:blob=z.read(n)
 else:blob=(WS/path).read_bytes()
 env=UnityPy.load(blob);return list({id(o.assets_file):o.assets_file for o in env.objects}.values())
def reader(oid):
 sid,fi=map(int,O[oid]['file'].split(':'));return sfload(sid)[fi].objects[O[oid]['path_id']]
def closure(oid):
 q=[oid];seen=set()
 while q:
  i=q.pop()
  if i in seen:continue
  seen.add(i);q+=G.get(i,{}).get('children',[])
 return seen
textures={};errors=[]
for oid in R['reachable']:
 if O[oid]['type']!='Texture2D':continue
 try:
  d=reader(oid).read()
  if d.m_TextureFormat==2:
   pixels=struct.unpack('<'+str(d.m_Width*d.m_Height)+'H',d.image_data[:d.m_Width*d.m_Height*2]);im=Image.frombytes('RGBA',(d.m_Width,d.m_Height),bytes(((px>>s)&15)*17 for px in pixels for s in (12,8,4,0))).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
  else:im=d.image
  im.thumbnail((384,384));fn=oid.replace(':','_')+'.png';im.save(images/fn);textures[oid]='images/'+fn
 except Exception as exc:errors.append(dict(object=oid,error=str(exc)))
(P/'image-manifest.json').write_text(json.dumps(dict(images=textures,errors=errors),ensure_ascii=False,indent=2))
def pics(ids):
 tex=sorted({i for oid in ids for i in closure(oid) if i in textures})
 return ''.join('<figure><a href="'+textures[i]+'"><img loading="lazy" src="'+textures[i]+'"></a><figcaption>'+html.escape(O[i]['name'])+'</figcaption></figure>' for i in tex)
req=R['requirements'];models=[r for r in req if r['scope']=='原始' and r['kind']=='模型' and r['objects']];families=defaultdict(list)
for r in models:families[r['family']].append(r)
missing=[r for r in req if r['scope']=='原始' and r['kind'] in ('模型','贴图','角色本体') and ('未找到' in r['status'] or '缺失' in r['status'])]
# Deduplicate by actual typed reference, retaining exact required package and affected quests.
grouped={}
for r in missing:
 key=r['kind'],r['name'],r['bundle'],r['path'];grouped.setdefault(key,r)
missing=list(grouped.values())
writecsv('决策缺口表.csv',['类别','原始引用名','物种族','加载包','相对路径','状态','使用关卡及怪物','现存同族模型候选','建议'],([r['kind'],r['name'],r['family'],r['bundle'],r['path'],r['status'],r['uses'],'；'.join(a['name'] for a in families[r['family']]),'已有重建包，原始外观待恢复' if '重建' in r['status'] else '评估同族模型/贴图配套复用' if families[r['family']] else '未找到同族模型；保留待补或寻找其他来源'] for r in missing))
intro='这是旧来源基线快照，历史上替代旧209项清单。新资源修复与当前生产状态请看上级README；下列缺口数字不是现生产待修总数。范围为228个可开放主线、已支持及已完成修复活动关卡（修复开关开启，不等同玩家已解锁或活动已排期）。逐关卡加载敌人表全部18普通槽位及Boss/Death槽位；原始引用与当前替代配置分开核对。图片是解包的UV贴图，不是3D渲染。'
style='<style>body{font:14px sans-serif;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;padding:8px;vertical-align:top}figure{display:inline-block;margin:4px;max-width:170px}img{max-width:160px;max-height:160px;background:#ddd}figcaption{overflow-wrap:anywhere}td{overflow-wrap:anywhere}summary{cursor:pointer}input{padding:10px;width:70%;margin:12px 0}.muted{color:#666}</style>'
head='<meta charset="utf-8">'+style+'<h1>按加载链核对的资源缺口与现有资源</h1><p>'+intro+'</p>'
head+='<p><a href="90个预载文件核对.csv">90个预载文件核对</a> · <a href="APK_Resources绑定核对.csv">APK路径绑定核对</a> · <a href="全部加载需求.csv">全部需求</a> · <a href="决策缺口表.csv">决策缺口表CSV</a> · <a href="核对报告.md">方法与统计说明</a></p>'
head+='<p>原始模型/贴图缺口 '+str(len(missing))+' 项，其中模型 '+str(sum(r['kind']=='模型' for r in missing))+' 项、贴图 '+str(sum(r['kind']=='贴图' for r in missing))+' 项。下载包与包内模型不重复加总；重建资源明确标注。</p>'
head+='<h2>已有物种与外观</h2><p>物种依据实际模型导出或APK路径绑定；角色敌人已另列于全部需求。动作文件不充当模型存在证据。</p><table><tr><th>名称族</th><th>已有模型</th><th>模型实际引用贴图</th></tr>'
allfamilies=sorted({r['family'] for r in req if r['family'] and r['kind'] in ('模型','贴图')})
for fam in allfamilies:
 rows=families[fam];head+='<tr><td>'+fam+'</td><td>'+('<br>'.join(html.escape(r['name'])+'（'+r['status']+'）' for r in rows) or '本地未找到对应模型；不等于动作也缺失')+'</td><td>'+pics([i for r in rows for i in r['objects']])+'</td></tr>'
head+='</table><h2>逐项决策缺口</h2><input id="filter" placeholder="筛选物种、资源名、关卡或怪物"><table id="gaps"><thead><tr><th>原始引用与状态</th><th>关卡／怪物</th><th>实际已有同族候选及图像</th><th>处理建议</th></tr></thead><tbody>'
for r in missing:
 candidates=families[r['family']];candidate_names='<br>'.join(html.escape(c['name']) for c in candidates)
 preview=pics([i for c in candidates for i in c['objects']])
 current=[c for c in req if c['scope']=='当前' and c['kind']==r['kind'] and set(c['enemies'])&set(r['enemies'])]
 current_text='；'.join(sorted({c['name']+' ['+c['status']+']' for c in current}))
 head+='<tr><td>'+html.escape(r['kind']+' '+r['name'])+'<br>'+html.escape(r['status'])+'<br><small>'+html.escape(r['path'])+'</small></td><td><details><summary>'+str(len(r['quest_ids']))+'关卡，'+str(len(r['enemies']))+'敌人</summary>'+html.escape(r['uses'])+'</details><details><summary>当前配置</summary>'+html.escape(current_text)+'</details></td><td>'+(candidate_names+preview if candidates else '未找到同族模型')+'</td><td>'+('已有重建包，仍缺原始外观' if '重建' in r['status'] else '优先评估同族配套复用；需确认骨骼/UV' if candidates else '需补充原始包、补绘/补模或明确采用异类替代')+'</td></tr>'
head+='</tbody></table><script>document.getElementById("filter").oninput=function(){let q=this.value.toLowerCase();document.querySelectorAll("#gaps tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))}</script>'
(P/'资源缺口总览.html').write_text(head)
# Track all raw names newly included compared with prior result; exact ast_ alias normalization.
old=list(csv.DictReader((P.parent/'缺口说明表.csv').open(encoding='utf-8-sig')));oldset={(r['类型'],r['原始引用资源名']) for r in old}
new=[r for r in missing if ('model' if r['kind']=='模型' else 'texture',r['name'].removeprefix('ast_')) not in oldset]
writecsv('相对旧表新增项.csv',['类别','引用名','加载包','状态','关卡与怪物'],([r['kind'],r['name'],r['bundle'],r['status'],r['uses']] for r in new))
summary=json.loads((P/'summary.json').read_text());current=[r for r in req if r['scope']=='当前'];book=sorted({r['bundle'] for r in current if r['kind']=='包' and '重建' in r['status']});present=Counter(r['kind'] for r in current if r['objects'])
report=['# 按原客户端加载链重审资源缺口','',intro,'','## 覆盖证据','',f'- 全新内容索引：{len(S)}份去重内容、{len(F)}个序列化文件、{len(O)}个对象（包括无名对象），解析错误{len(D["errors"])}。','- 90个预载文件全部解析；90个均匹配到内容哈希一致的APK内嵌预载副本。__info等缓存元数据不计入这90个资源文件。','- APK内所有assets条目均有覆盖记录；Unity对象文件解析，其他条目标记为非Unity对象数据。程序集代码、原生库等不是贴图缺口判定对象。','- 2250条APK Resources绑定均通过外部FileID/PathID解析到实际对象，而非仅匹配路径字符串。',f'- 对关卡可达的{len(R["roots"])}个资源根追踪{len(R["reachable"])}个对象，包括模型、骨骼、材质、贴图、动画和特效；本次静态序列化指针检查未发现悬空引用。引擎自带资源单独识别，不误判为缺失。','','## 缺口统计（避免重复计数）','',f'- 原始模型/贴图缺口{len(missing)}项：模型{sum(r["kind"]=="模型" for r in missing)}项、贴图{sum(r["kind"]=="贴图" for r in missing)}项。',f'- 相对旧209项清单新增{len(new)}项，见相对旧表新增项.csv；其中书本是先前遗漏的加载依赖，普通新增项来自整张敌人表预加载。','- 新增9项具体为5个角色地图书本及4个楼梯/移动地板模型；普通敌人原始模型/贴图仍为209项。本次独立加载链核对没有额外确认普通物种模型。',
'- 本地缺少132个原始下载包；这些包内模型/贴图已计入上述缺口，不把“缺包”和“缺模型”简单相加。','- 当前替代配置的直接模型、贴图、角色本体、已映射动作及攻击效果均找到资源对象。仍使用重建包恢复的书本：'+ '、'.join(book)+'。重建存在不等于原始美术已恢复。','- 空动作null是客户端可容忍的空动作；同名Material缓存未命中也被代码判空保护，实际渲染材质从模型依赖核对。这两类不直接计作必须补绘资源。','','## 物种复核','', '螃蟹、鸟、狼、蝎等会同时检查包导出名、APK完整Resources路径、所有实际对象名及模型递归依赖。更正：旧来源只命中蝎/狼动作，后续新资源已找到330系列狼和ms01_sco_*_02蝎子模型及贴图并发布同族兼容包。旧未命中不代表当前仍缺同族素材；原等级专属图稿与同族替代须分列。完整对象及来源CSV便于交叉核验。','','## 加载链依据与限制','', '原始DLL导出定义包含包版本、本地白名单、角色敌人类型、MotionAssign动作索引、MotionData文件名、ConvertKindToCategory、EnemyAttackEffectAssign。EnemyArrangeTable读取全部槽位；普通敌人非Boss在动作列2提前返回，角色书本方向分支另列条件。na在EnemyData构造函数转换为空贴图，不当作真实文件名。','', '包身份按实际包文件名和ast_模型的包导出确认；不能以其他包中的同名对象认定目标包可加载。原始资源与reconstructed来源分开。Resources外部指针按同APK上下文优先解析；全部2250条已唯一解析。','', '这是静态加载链与对象依赖核对，不是Android实机下载日志。尚未验证Unity实际URL/版本缓存键命中、目标HTTP可达、运行时组件行为，以及玩家队伍触发的全部共享技能/声音/场景资源。动作的BOOK_SYMBOL与朝向分支按可能条件保留；素材存在不代表所有动画或视觉显示已实机验证。结论限于当前工作区与上述敌人加载路径，不对未提供的资源包作不存在断言。','','## 文件入口','', '- 资源缺口总览.html：可筛选缺口、已有物种图鉴及贴图预览。','- 决策缺口表.csv：用于复用/补绘决策。','- 全部加载需求.csv：含原始和当前两种口径，保留加载条件。','- 90个预载文件核对.csv、APK资源覆盖.csv、APK_Resources绑定核对.csv：覆盖及路径证据。','- 全部资源对象.csv、资源来源.csv：包括未命中物种关键词和无名对象的完整清单。','- 递归依赖待核实.csv：本轮无悬空序列化指针。']
(P/'核对报告.md').write_text('\n'.join(report)+'\n')
print(json.dumps(dict(missing=len(missing),new=len(new),images=len(textures),image_errors=errors,current_rebuilt_books=book),ensure_ascii=False))
