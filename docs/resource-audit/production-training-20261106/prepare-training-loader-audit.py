from pathlib import Path
src=Path('/home/workspace/RTD_SERVER/docs/resource-audit/loading-chain/audit.py')
s=src.read_text();s=s.replace('P=Path(__file__).parent;ROOT=P.parents[2];WS=ROOT.parent',"P=Path('/home/workspace/RTD_SERVER/docs/resource-audit/loading-chain');ROOT=P.parents[2];WS=ROOT.parent\nOUT=P.parent/'production-training-20261106';OUT.mkdir(exist_ok=True)")
s=s.replace("with (P/name).open", "with (OUT/name).open")
a=s.index('sys.path.insert(0,str(ROOT))');b=s.index('defs={};local=set()',a)
s=s[:a]+'''sys.path.insert(0,'/home/RTD_SERVER')
from rtd.masters.catalog import load_catalog
snap=json.loads(Path('/tmp/rtd-training-snapshot.json').read_text())
masters,_=load_catalog();orig={r['id']:r for r in masters[20]['data_list']}
effective={e['id']:e for r in snap['rows'] for e in r['enemies']}
qs={r['quest']['id']:r['quest'] for r in snap['rows']}
tables={r['id']:r for r in masters[21]['data_list']}
'''+s[b:]
s=s.replace('questids=(SINGLE_QUESTS|api.event_quests|layer_quests(api))-api.blocked_quests','questids=set(qs)')
s=s.replace("(P/'graph.json').write_text","(OUT/'graph.json').write_text").replace("(P/'results.json').write_text","(OUT/'results.json').write_text").replace("(P/'summary.json').write_text","(OUT/'summary.json').write_text")
s=s.replace("with (OUT/name).open", "if name in ('全部资源对象.csv','资源来源.csv','APK_Resources绑定核对.csv'):return\n with (OUT/name).open")
s=s.replace("writecsv('资源缺口与绑定问题.csv'","writecsv('旧资源索引差异参考.csv'")
Path('/tmp/rtd-training-loader-audit.py').write_text(s)
