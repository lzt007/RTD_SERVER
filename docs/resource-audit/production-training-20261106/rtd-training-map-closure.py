from pathlib import Path
import json
root=Path('/home/workspace/RTD_SERVER');out=root/'docs/resource-audit/production-training-20261106';src=root/'docs/resource-audit/loading-chain/audit.py'
s=src.read_text().split('sys.path.insert(0,str(ROOT))')[0].replace('P=Path(__file__).parent;ROOT=P.parents[2];WS=ROOT.parent',"P=Path('/home/workspace/RTD_SERVER/docs/resource-audit/loading-chain');ROOT=P.parents[2];WS=ROOT.parent").replace(" with (P/name).open", " return\n with (P/name).open")
ns={};exec(compile(s,str(src),'exec'),ns)
x=json.loads((out/'map-table-evidence.json').read_text());results=[]
for row in x['selected_maps']:
 for path in row['requirements']:
  roots=ns['resource'].get(path.lower(),[]);issues=[];nodes=set()
  for oid in roots:
   visited,found=ns['closure'](oid);nodes.update(visited);issues+=found
  results.append(dict(map_id=row['map_id'],path=path,root_types=[ns['O'][oid]['type'] for oid in roots],roots=roots,reachable=len(nodes),issues=issues,status='verified' if roots and not issues else 'review_required'))
x['dependency_results']=results;(out/'map-table-evidence.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print('map requirements',len(results),'verified',sum(r['status']=='verified' for r in results),'issues',sum(len(r['issues']) for r in results),flush=True)
